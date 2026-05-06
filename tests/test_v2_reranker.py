import sys

from app.reranker import rerank_candidates
from app.schemas_v2 import CandidateChunk


def _candidate(chunk_id: str, paper_name: str, rrf_score: float) -> CandidateChunk:
    return CandidateChunk(
        chunk_id=chunk_id,
        parent_chunk_id=chunk_id,
        paper_name=paper_name,
        text=f"text {chunk_id}",
        retrieval_text=f"retrieval {chunk_id}",
        rrf_score=rrf_score,
    )


def test_reranker_disabled_returns_rrf_order():
    candidates = [
        _candidate("c1", "A", 0.1),
        _candidate("c2", "B", 0.3),
        _candidate("c3", "C", 0.2),
    ]

    ranked = rerank_candidates("query", candidates, {"reranker": {"enabled": False}})

    assert [candidate.chunk_id for candidate in ranked] == ["c2", "c3", "c1"]


def test_final_top_n_is_enforced():
    candidates = [
        _candidate("c1", "A", 0.3),
        _candidate("c2", "B", 0.2),
        _candidate("c3", "C", 0.1),
    ]

    ranked = rerank_candidates(
        "query",
        candidates,
        {"reranker": {"enabled": False, "final_top_n": 2}},
    )

    assert [candidate.chunk_id for candidate in ranked] == ["c1", "c2"]


def test_max_chunks_per_paper_is_enforced():
    candidates = [
        _candidate("c1", "A", 0.4),
        _candidate("c2", "A", 0.3),
        _candidate("c3", "B", 0.2),
    ]

    ranked = rerank_candidates(
        "query",
        candidates,
        {"reranker": {"enabled": False, "max_chunks_per_paper": 1}},
    )

    assert [candidate.chunk_id for candidate in ranked] == ["c1", "c3"]


def test_dependency_missing_or_exception_falls_back_to_rrf_without_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    candidates = [
        _candidate("c1", "A", 0.1),
        _candidate("c2", "B", 0.2),
    ]

    ranked = rerank_candidates("query", candidates, {"reranker": {"enabled": True}})

    assert [candidate.chunk_id for candidate in ranked] == ["c2", "c1"]
