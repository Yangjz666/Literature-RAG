from __future__ import annotations

from typing import Any

from app.reranker import rerank_candidates
from app.retriever import hybrid_retrieve_candidates
from app.schemas_v2 import CandidateChunk, FeedbackRecord


def _feedback_config(config: dict | None) -> dict:
    return (config or {}).get("self_feedback") or {}


def run_followup_retrieval(
    feedback: FeedbackRecord,
    index: Any,
    llm_client: Any,
    config: dict | None,
    existing_chunk_ids: set[str] | list[str] | None = None,
) -> list[CandidateChunk]:
    feedback_cfg = _feedback_config(config)
    if not feedback_cfg.get("allow_followup_retrieval", False):
        return []

    followup_queries = list(feedback.followup_queries or [])
    if not followup_queries:
        return []

    max_followup_queries = int(feedback_cfg.get("max_followup_queries", 3))
    excluded = {str(chunk_id) for chunk_id in (existing_chunk_ids or []) if str(chunk_id)}
    seen = set(excluded)
    merged: list[CandidateChunk] = []

    for query in followup_queries[:max_followup_queries]:
        candidates = hybrid_retrieve_candidates(query, index, llm_client, config or {})
        ranked = rerank_candidates(query, candidates, config or {})
        for candidate in ranked:
            if candidate.chunk_id in seen:
                continue
            seen.add(candidate.chunk_id)
            merged.append(candidate)

    return merged
