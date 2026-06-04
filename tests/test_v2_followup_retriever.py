from app.followup_retriever import run_followup_retrieval
from app.schemas_v2 import CandidateChunk, FeedbackRecord


class FakeIndex:
    pass


def _candidate(chunk_id: str, rrf_score: float = 1.0) -> CandidateChunk:
    return CandidateChunk(chunk_id=chunk_id, text=f"text {chunk_id}", paper_name="Paper", rrf_score=rrf_score)


def test_allow_followup_retrieval_false_returns_empty(monkeypatch):
    def fail_retrieve(*args, **kwargs):
        raise AssertionError("retriever should not be called")

    monkeypatch.setattr("app.followup_retriever.hybrid_retrieve_candidates", fail_retrieve)
    feedback = FeedbackRecord(need_followup_retrieval=True, followup_queries=["q1"])

    assert run_followup_retrieval(feedback, FakeIndex(), None, {"self_feedback": {"allow_followup_retrieval": False}}) == []


def test_no_followup_queries_returns_empty(monkeypatch):
    def fail_retrieve(*args, **kwargs):
        raise AssertionError("retriever should not be called")

    monkeypatch.setattr("app.followup_retriever.hybrid_retrieve_candidates", fail_retrieve)
    feedback = FeedbackRecord(need_followup_retrieval=True, followup_queries=[])

    assert run_followup_retrieval(feedback, FakeIndex(), None, {"self_feedback": {"allow_followup_retrieval": True}}) == []


def test_max_followup_queries_is_enforced(monkeypatch):
    calls = []

    def fake_retrieve(query, index, llm_client, config):
        calls.append(query)
        return [_candidate(query)]

    monkeypatch.setattr("app.followup_retriever.hybrid_retrieve_candidates", fake_retrieve)
    monkeypatch.setattr("app.followup_retriever.rerank_candidates", lambda query, candidates, config: candidates)
    feedback = FeedbackRecord(followup_queries=["q1", "q2", "q3"])

    chunks = run_followup_retrieval(
        feedback,
        FakeIndex(),
        None,
        {"self_feedback": {"allow_followup_retrieval": True, "max_followup_queries": 2}},
    )

    assert calls == ["q1", "q2"]
    assert [chunk.chunk_id for chunk in chunks] == ["q1", "q2"]


def test_multiple_query_results_are_deduped(monkeypatch):
    def fake_retrieve(query, index, llm_client, config):
        return [_candidate("shared"), _candidate(query)]

    monkeypatch.setattr("app.followup_retriever.hybrid_retrieve_candidates", fake_retrieve)
    monkeypatch.setattr("app.followup_retriever.rerank_candidates", lambda query, candidates, config: candidates)
    feedback = FeedbackRecord(followup_queries=["q1", "q2"])

    chunks = run_followup_retrieval(feedback, FakeIndex(), None, {"self_feedback": {"allow_followup_retrieval": True}})

    assert [chunk.chunk_id for chunk in chunks] == ["shared", "q1", "q2"]


def test_existing_chunk_ids_are_excluded(monkeypatch):
    monkeypatch.setattr(
        "app.followup_retriever.hybrid_retrieve_candidates",
        lambda query, index, llm_client, config: [_candidate("existing"), _candidate("new")],
    )
    monkeypatch.setattr("app.followup_retriever.rerank_candidates", lambda query, candidates, config: candidates)
    feedback = FeedbackRecord(followup_queries=["q1"])

    chunks = run_followup_retrieval(
        feedback,
        FakeIndex(),
        None,
        {"self_feedback": {"allow_followup_retrieval": True}},
        existing_chunk_ids={"existing"},
    )

    assert [chunk.chunk_id for chunk in chunks] == ["new"]
