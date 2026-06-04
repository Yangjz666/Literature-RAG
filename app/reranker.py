from __future__ import annotations

from app.schemas_v2 import CandidateChunk


def _reranker_config(config: dict) -> dict:
    return (config or {}).get("reranker", {})


def _paper_key(candidate: CandidateChunk) -> str:
    return candidate.paper_name or candidate.filename or candidate.doi or "unknown"


def _rrf_order(candidates: list[CandidateChunk]) -> list[CandidateChunk]:
    return sorted(candidates, key=lambda candidate: candidate.rrf_score or 0.0, reverse=True)


def _limit_candidates(
    candidates: list[CandidateChunk],
    final_top_n: int,
    max_chunks_per_paper: int,
) -> list[CandidateChunk]:
    limited: list[CandidateChunk] = []
    per_paper: dict[str, int] = {}
    for candidate in candidates:
        key = _paper_key(candidate)
        if per_paper.get(key, 0) >= max_chunks_per_paper:
            continue
        limited.append(candidate)
        per_paper[key] = per_paper.get(key, 0) + 1
        if len(limited) >= final_top_n:
            break
    return limited


def _fallback(candidates: list[CandidateChunk], final_top_n: int, max_chunks_per_paper: int) -> list[CandidateChunk]:
    return _limit_candidates(_rrf_order(candidates), final_top_n, max_chunks_per_paper)


def _score_with_cross_encoder(query: str, candidates: list[CandidateChunk], config: dict) -> list[CandidateChunk]:
    from sentence_transformers import CrossEncoder

    reranker_cfg = _reranker_config(config)
    model_name = reranker_cfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    model = CrossEncoder(model_name)
    pairs = [
        [query, candidate.retrieval_text or candidate.text]
        for candidate in candidates
    ]
    scores = model.predict(pairs)
    scored: list[CandidateChunk] = []
    for candidate, score in zip(candidates, scores):
        updated = candidate.model_copy()
        updated.rerank_score = float(score)
        scored.append(updated)
    return sorted(scored, key=lambda candidate: candidate.rerank_score or 0.0, reverse=True)


def rerank_candidates(
    query: str,
    candidates: list[CandidateChunk],
    config: dict,
) -> list[CandidateChunk]:
    reranker_cfg = _reranker_config(config)
    final_top_n = int(reranker_cfg.get("final_top_n", 10))
    max_chunks_per_paper = int(reranker_cfg.get("max_chunks_per_paper", 3))

    if not candidates:
        return []

    if not reranker_cfg.get("enabled", False):
        return _fallback(candidates, final_top_n, max_chunks_per_paper)

    try:
        ranked = _score_with_cross_encoder(query, candidates, config)
    except Exception:
        return _fallback(candidates, final_top_n, max_chunks_per_paper)

    return _limit_candidates(ranked, final_top_n, max_chunks_per_paper)
