"""Helpers for building per-query retrieval debug traces."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import re


NOT_AVAILABLE = "not_available"
TEXT_PREVIEW_LIMIT = 400

TRACE_STAGE_FIELDS = (
    "bm25_results",
    "vector_results",
    "rrf_results",
    "reranker_results",
)

VALID_FAILED_STAGES = {
    "query_rewrite_failed",
    "bm25_failed",
    "vector_search_failed",
    "rrf_failed",
    "reranker_failed",
    "context_builder_failed",
    "llm_failed",
    "citation_parse_failed",
    "unknown_failed",
}


def create_debug_trace(user_query: str, query_mode: str | None = None) -> dict:
    """Create an in-memory trace shell for one RAG query attempt."""
    query = "" if user_query is None else str(user_query)
    return {
        "trace_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_query": query,
        "original_query": query,
        "rewritten_query": NOT_AVAILABLE,
        "query_mode": query_mode,
        "bm25_results": NOT_AVAILABLE,
        "vector_results": NOT_AVAILABLE,
        "rrf_results": NOT_AVAILABLE,
        "reranker_results": NOT_AVAILABLE,
        "final_context_chunks": [],
        "final_answer": None,
        "citations_used": [],
        "elapsed_ms": None,
        "warning": [],
        "error": None,
        "failed_stage": None,
    }


def normalize_trace_chunk(raw_chunk: Any, source_stage: str) -> dict:
    """Normalize a retrieved chunk or candidate into trace display fields."""
    metadata = _metadata(raw_chunk)
    return {
        "document_id": _first_value(raw_chunk, metadata, ("document_id", "doc_id", "doi")),
        "filename": _first_value(raw_chunk, metadata, ("filename", "paper_name", "source")),
        "page": _coerce_int(_first_value(raw_chunk, metadata, ("page", "page_number"))),
        "section": _first_value(raw_chunk, metadata, ("section", "heading")),
        "chunk_id": _string_or_none(_first_value(raw_chunk, metadata, ("chunk_id", "id"))),
        "parent_chunk_id": _string_or_none(
            _first_value(raw_chunk, metadata, ("parent_chunk_id", "parent_id"))
        ),
        "score": _coerce_float(
            _first_value(raw_chunk, metadata, ("score", "rrf_score", "rerank_score"))
        ),
        "source_stage": source_stage,
        "text_preview": _preview(
            _first_value(
                raw_chunk,
                metadata,
                ("text", "retrieval_text", "evidence_text", "content", "document"),
            )
        ),
    }


def normalize_trace_chunks(raw_chunks: list[Any] | None, source_stage: str) -> list[dict]:
    if not raw_chunks:
        return []
    if not isinstance(raw_chunks, (list, tuple)):
        raw_chunks = [raw_chunks]

    normalized: list[dict] = []
    for raw_chunk in raw_chunks:
        try:
            normalized.append(normalize_trace_chunk(raw_chunk, source_stage))
        except Exception:
            continue
    return normalized


def mark_stage_not_available(trace: dict, stage: str, reason: str | None = None) -> None:
    if not isinstance(trace, dict):
        return
    trace[stage] = NOT_AVAILABLE
    if reason:
        _warnings(trace).append(str(reason))


def record_error(trace: dict, failed_stage: str, error: Exception | str) -> None:
    if not isinstance(trace, dict):
        return
    trace["failed_stage"] = (
        failed_stage if failed_stage in VALID_FAILED_STAGES else "unknown_failed"
    )
    trace["error"] = _sanitize_error_message(error)


def to_json_safe(value: Any) -> Any:
    """Return a recursively JSON-serializable copy of value."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return to_json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        try:
            return to_json_safe(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "dict"):
        try:
            return to_json_safe(value.dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        public = {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
        if public:
            return to_json_safe(public)
    return str(value)


def normalize_trace_citation(raw_citation: Any, final_context_chunks: list[dict]) -> dict:
    metadata = _metadata(raw_citation)
    chunk_id = _string_or_none(_first_value(raw_citation, metadata, ("chunk_id", "source_chunk_id")))
    matched_context = _find_context_by_chunk_id(final_context_chunks, chunk_id)

    citation = {
        "citation_id": _string_or_none(
            _first_value(raw_citation, metadata, ("citation_id", "source_id", "id"))
        ),
        "document_id": _first_value(raw_citation, metadata, ("document_id", "doc_id", "doi")),
        "filename": _first_value(raw_citation, metadata, ("filename", "paper_name", "source")),
        "page": _coerce_int(_first_value(raw_citation, metadata, ("page", "page_number"))),
        "section": _first_value(raw_citation, metadata, ("section", "heading")),
        "chunk_id": chunk_id,
        "evidence_text_preview": _preview(
            _first_value(raw_citation, metadata, ("evidence_text", "text", "content"))
        ),
        "matched_final_context": matched_context is not None,
        "match_status": "matched" if matched_context is not None else "unmatched",
    }

    if matched_context:
        for key in ("document_id", "filename", "page", "section"):
            if citation[key] is None:
                citation[key] = matched_context.get(key)
    if chunk_id is None and not final_context_chunks:
        citation["match_status"] = NOT_AVAILABLE
    return citation


def record_citations(trace: dict, citations: list[Any] | None) -> None:
    if not isinstance(trace, dict):
        return
    if not citations:
        trace["citations_used"] = []
        return

    final_context_chunks = trace.get("final_context_chunks") or []
    trace["citations_used"] = [
        normalize_trace_citation(citation, final_context_chunks)
        for citation in citations
    ]


def _metadata(value: Any) -> dict:
    metadata = _get_value(value, "metadata")
    return metadata if isinstance(metadata, dict) else {}


def _first_value(value: Any, metadata: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        result = _get_value(value, key)
        if result is not None:
            return result
        if key in metadata and metadata[key] is not None:
            return metadata[key]
    return None


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _coerce_int(value: Any) -> int | None:
    try:
        return None if value is None or value == "" else int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return None


def _preview(value: Any, limit: int = TEXT_PREVIEW_LIMIT) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _warnings(trace: dict) -> list[str]:
    warnings = trace.setdefault("warning", [])
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
        trace["warning"] = warnings
    return warnings


def _sanitize_error_message(error: Exception | str) -> str:
    message = str(error)
    message = re.sub(r"sk-[A-Za-z0-9_\-]+", "[REDACTED_API_KEY]", message)
    message = re.sub(r"(?:(?:/home|/mnt/[a-z]|/Users)/)[^\s]+", "[REDACTED_PATH]", message)
    return message


def _find_context_by_chunk_id(
    final_context_chunks: list[dict], chunk_id: str | None
) -> dict | None:
    if not chunk_id:
        return None
    for chunk in final_context_chunks:
        if isinstance(chunk, dict) and str(chunk.get("chunk_id")) == chunk_id:
            return chunk
    return None
