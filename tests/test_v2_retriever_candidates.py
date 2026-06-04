from inspect import signature

from app.retriever import hybrid_retrieve, hybrid_retrieve_candidates
from app.schemas_v2 import CandidateChunk


class FakeIndex:
    def __init__(self):
        self.children = {
            "c1": {
                "chunk_id": "c1",
                "text": "child one",
                "metadata": {"parent_chunk_id": "p1"},
            },
            "c2": {
                "chunk_id": "c2",
                "text": "child two",
                "metadata": {"parent_chunk_id": "p1"},
            },
            "c3": {
                "chunk_id": "c3",
                "text": "child three",
                "metadata": {"parent_chunk_id": "p2"},
            },
        }
        self.parents = {
            "p1": {
                "chunk_id": "p1",
                "text": "parent one text",
                "paper_name": "PaperA",
                "filename": "paper_a.pdf",
                "doi": "10.1000/a",
                "title": "Title A",
                "year": 2024,
                "page": 1,
                "section": "Methods",
                "is_si": False,
            },
            "p2": {
                "chunk_id": "p2",
                "text": "parent two text",
                "paper_name": "PaperB",
                "filename": "paper_b_si.pdf",
                "doi": "10.1000/b",
                "title": "Title B",
                "year": 2023,
                "page": 2,
                "section": "SI",
                "is_si": True,
            },
        }

    def vector_search(self, query, top_k):
        return [{"chunk_id": "c2"}, {"chunk_id": "c3"}][:top_k]

    def bm25_search(self, query, top_k):
        return [{"chunk_id": "c1"}, {"chunk_id": "c2"}, {"chunk_id": "c3"}][:top_k]

    def get_chunk_by_id(self, chunk_id):
        return self.children.get(chunk_id)

    def get_parent(self, parent_id):
        return self.parents.get(parent_id)


def test_hybrid_retrieve_candidates_returns_candidate_chunks():
    candidates = hybrid_retrieve_candidates("query", FakeIndex(), None, {})

    assert candidates
    assert all(isinstance(candidate, CandidateChunk) for candidate in candidates)
    assert candidates[0].chunk_id == "p1"
    assert candidates[0].paper_name == "PaperA"
    assert candidates[0].retrieval_text
    assert candidates[0].bm25_rank is not None
    assert candidates[0].vector_rank is not None
    assert candidates[0].rrf_score is not None


def test_candidate_top_k_is_enforced():
    candidates = hybrid_retrieve_candidates(
        "query",
        FakeIndex(),
        None,
        {"retrieval": {"candidate_top_k": 1}},
    )

    assert len(candidates) == 1


def test_child_hit_expands_to_parent_chunk():
    candidates = hybrid_retrieve_candidates("query", FakeIndex(), None, {})

    candidate_ids = {candidate.chunk_id for candidate in candidates}
    assert "p1" in candidate_ids
    assert "c1" not in candidate_ids
    assert any(candidate.text == "parent one text" for candidate in candidates)


def test_same_parent_is_deduped_and_hit_child_ids_are_merged():
    candidates = hybrid_retrieve_candidates("query", FakeIndex(), None, {})

    p1 = next(candidate for candidate in candidates if candidate.chunk_id == "p1")
    assert sorted(p1.hit_child_ids) == ["c1", "c2"]
    assert len([candidate for candidate in candidates if candidate.chunk_id == "p1"]) == 1


def test_hybrid_retrieve_signature_and_default_return_remain_unchanged():
    params = list(signature(hybrid_retrieve).parameters)

    assert params == ["query", "index", "llm_client", "config"]

    result = hybrid_retrieve(
        "query",
        FakeIndex(),
        None,
        {"retrieval": {"final_top_k": 1}},
    )
    assert isinstance(result, list)
    assert result
    assert isinstance(result[0], dict)
    assert "rrf_score" in result[0]
