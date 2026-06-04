from __future__ import annotations

from typing import Any

from app.schemas_v2 import CandidateChunk, SourceCitation


def _metadata_value(candidate: CandidateChunk, key: str, default: Any = "") -> Any:
    metadata = candidate.metadata or {}
    value = metadata.get(key)
    if value is None:
        value = metadata.get(key.lower(), default)
    return default if value is None else value


def _display(value: Any) -> str:
    if value is None or value == "":
        return "Unknown"
    return str(value)


def _supporting_information_label(is_si: bool) -> str:
    return "Yes (SI)" if is_si else "No"


def build_retrieval_text(candidate: CandidateChunk) -> str:
    title = _metadata_value(candidate, "title")
    doi = candidate.doi or _metadata_value(candidate, "doi")
    paper = candidate.paper_name or _metadata_value(candidate, "paper_name")
    filename = candidate.filename or _metadata_value(candidate, "filename")
    section = candidate.section or _metadata_value(candidate, "section")
    page = candidate.page if candidate.page is not None else _metadata_value(candidate, "page")

    lines = [
        f"Title: {_display(title)}",
        f"DOI: {_display(doi)}",
        f"Paper: {_display(paper)}",
        f"Filename: {_display(filename)}",
        f"Section: {_display(section)}",
        f"Page: {_display(page)}",
        f"Supporting Information: {_supporting_information_label(candidate.is_si)}",
        f"Text: {candidate.text or ''}",
    ]
    return "\n".join(lines)


def _context_budget(config: dict) -> tuple[int, int]:
    context_budget = config.get("context_budget") or {}
    retrieval = config.get("retrieval") or {}

    max_chunks_per_paper = context_budget.get(
        "max_chunks_per_paper",
        retrieval.get("max_chunks_per_paper", 3),
    )
    max_context_tokens = context_budget.get(
        "max_context_tokens",
        retrieval.get("max_context_tokens", 12000),
    )
    return int(max_chunks_per_paper), int(max_context_tokens)


def _paper_key(candidate: CandidateChunk) -> str:
    return (
        candidate.paper_name
        or candidate.filename
        or candidate.doi
        or _metadata_value(candidate, "paper_name")
        or _metadata_value(candidate, "filename")
        or "unknown"
    )


def _estimated_tokens(text: str) -> float:
    return len(text or "") / 4


def build_v2_context(
    query: str,
    ranked_chunks: list[CandidateChunk],
    config: dict,
) -> tuple[str, list[SourceCitation]]:
    if not ranked_chunks:
        return "", []

    max_chunks_per_paper, max_context_tokens = _context_budget(config or {})
    seen_chunk_ids: set[str] = set()
    chunks_per_paper: dict[str, int] = {}
    used_tokens = 0.0
    context_blocks: list[str] = []
    citations: list[SourceCitation] = []

    for candidate in ranked_chunks:
        if candidate.chunk_id and candidate.chunk_id in seen_chunk_ids:
            continue

        paper_key = _paper_key(candidate)
        if chunks_per_paper.get(paper_key, 0) >= max_chunks_per_paper:
            continue

        candidate_tokens = _estimated_tokens(candidate.text)
        if used_tokens + candidate_tokens > max_context_tokens:
            continue

        citation_id = f"S{len(citations) + 1}"
        retrieval_text = build_retrieval_text(candidate)
        context_blocks.append(f"[{citation_id}]\n{retrieval_text}")
        citations.append(
            SourceCitation(
                citation_id=citation_id,
                source_id=citation_id,
                paper_name=candidate.paper_name,
                filename=candidate.filename,
                doi=candidate.doi,
                page=candidate.page,
                section=candidate.section,
                is_si=candidate.is_si,
                evidence_text=candidate.text,
                chunk_id=candidate.chunk_id,
                metadata=dict(candidate.metadata or {}),
            )
        )

        if candidate.chunk_id:
            seen_chunk_ids.add(candidate.chunk_id)
        chunks_per_paper[paper_key] = chunks_per_paper.get(paper_key, 0) + 1
        used_tokens += candidate_tokens

    if not context_blocks:
        return "", []

    header = f"Query: {query}\n\n" if query else ""
    return header + "\n\n".join(context_blocks), citations
