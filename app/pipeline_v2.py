from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from app.claim_verifier import verify_claims
from app.context_builder import build_v2_context
from app.debug_trace import (
    create_debug_trace,
    record_citations,
    record_elapsed_ms,
    record_error,
    record_final_answer,
    record_final_context,
    record_stage_results,
    to_json_safe,
)
from app.feedback import run_self_feedback
from app.followup_retriever import run_followup_retrieval
from app.metadata_enricher import enrich_metadata
from app.query_router import detect_query_mode
from app.report_v2 import generate_markdown_v2, save_markdown_v2
from app.reranker import rerank_candidates
from app.retriever import hybrid_retrieve_candidates
from app.schemas_v2 import SynthesisResult
from app.synthesizer import synthesize_with_citations


def _output_dir(config: dict) -> str:
    value = (config or {}).get("output_dir")
    if value:
        return str(value)
    v2_value = ((config or {}).get("v2") or {}).get("output_dir")
    if v2_value:
        return str(v2_value)
    return str(Path("data") / "output")


def run_synthesis_pipeline(
    query: str,
    index: Any,
    llm_client: Any,
    config: dict | None = None,
    debug_trace: dict | None = None,
) -> SynthesisResult:
    config = config or {}
    query_mode = detect_query_mode(query, config=config)
    trace = debug_trace or create_debug_trace(query, query_mode=query_mode.value)
    started_at = perf_counter()

    try:
        candidates = hybrid_retrieve_candidates(query, index, llm_client, config, debug_trace=trace)
        try:
            ranked = rerank_candidates(query, candidates, config)
            record_stage_results(trace, "reranker_results", ranked, "reranker")
        except Exception as exc:
            record_error(trace, "reranker_failed", exc)
            raise

        try:
            context_text, citations = build_v2_context(query, ranked, config)
            record_final_context(trace, _chunks_used_for_citations(ranked, citations))
        except Exception as exc:
            record_error(trace, "context_builder_failed", exc)
            raise

        try:
            result = synthesize_with_citations(query, context_text, citations, llm_client, config)
            record_final_answer(trace, result.answer)
            record_citations(trace, result.citations)
        except Exception as exc:
            record_error(trace, "llm_failed", exc)
            raise

        result.claims = verify_claims(result.claims, result.citations, llm_client=None, config=config)
        external_metadata_records = []
        if (config.get("external_metadata") or {}).get("enabled", False):
            for citation in result.citations:
                identifier = citation.doi or citation.paper_name
                if not identifier:
                    continue
                metadata = enrich_metadata(identifier, config)
                if metadata is not None:
                    external_metadata_records.append(metadata)
            result.metadata["external_metadata_count"] = len(external_metadata_records)
            result.metadata["external_metadata"] = [
                metadata.model_dump() if hasattr(metadata, "model_dump") else metadata.dict()
                for metadata in external_metadata_records
            ]
        feedback = run_self_feedback(query, result, result.citations, llm_client=llm_client, config=config)
        result.feedback_trace.append(feedback)
        followup_chunks = []
        if feedback.need_followup_retrieval and (config.get("self_feedback") or {}).get("allow_followup_retrieval", False):
            try:
                existing_chunk_ids = {candidate.chunk_id for candidate in ranked}
                followup_chunks = run_followup_retrieval(
                    feedback,
                    index,
                    llm_client,
                    config,
                    existing_chunk_ids=existing_chunk_ids,
                )
                feedback.followup_chunk_ids = [chunk.chunk_id for chunk in followup_chunks]
                if followup_chunks:
                    ranked = [*ranked, *followup_chunks]
                    context_text, citations = build_v2_context(query, ranked, config)
                    result.metadata["followup_context_citation_count"] = len(citations)
            except Exception as exc:
                feedback.followup_error = str(exc)
                feedback.notes.append(f"follow-up retrieval failed: {exc}")

        markdown = generate_markdown_v2(result)
        markdown_path = save_markdown_v2(markdown, query, _output_dir(config))
        record_elapsed_ms(trace, started_at)
        result.metadata = {
            **result.metadata,
            "markdown_path": markdown_path,
            "candidate_count": len(candidates),
            "context_citation_count": len(citations),
            "claims_verified": True,
            "query_mode": query_mode.value,
            "feedback_iterations": len(result.feedback_trace),
            "followup_chunk_count": len(followup_chunks),
            "debug_trace": to_json_safe(trace),
        }
        return result
    except Exception as exc:
        if trace.get("failed_stage") is None:
            record_error(trace, "unknown_failed", exc)
        record_elapsed_ms(trace, started_at)
        setattr(exc, "debug_trace", to_json_safe(trace))
        raise


def _chunks_used_for_citations(ranked: list[Any], citations: list[Any]) -> list[Any]:
    citation_chunk_ids = {
        str(citation.chunk_id)
        for citation in citations
        if getattr(citation, "chunk_id", None)
    }
    if not citation_chunk_ids:
        return []
    return [
        candidate
        for candidate in ranked
        if getattr(candidate, "chunk_id", None) and str(candidate.chunk_id) in citation_chunk_ids
    ]
