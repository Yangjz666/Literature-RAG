import json
from pathlib import Path

from app.pipeline_v2 import run_synthesis_pipeline


class FakeIndex:
    def __init__(self, empty=False):
        self.empty = empty
        self.vector_called = False
        self.bm25_called = False
        self.parents = {
            "p1": {
                "chunk_id": "p1",
                "text": "Ag NPs were prepared by chemical reduction.",
                "paper_name": "Zhang_2023",
                "filename": "zhang.pdf",
                "page": 3,
                "section": "Experimental",
                "is_si": False,
                "metadata": {"title": "Ag synthesis"},
            }
        }
        self.children = {
            "c1": {
                "chunk_id": "c1",
                "text": "Ag NPs were prepared by chemical reduction.",
                "metadata": {"parent_chunk_id": "p1"},
            }
        }

    def vector_search(self, query, top_k):
        self.vector_called = True
        return [] if self.empty else [{"chunk_id": "c1"}]

    def bm25_search(self, query, top_k):
        self.bm25_called = True
        return [] if self.empty else [{"chunk_id": "c1"}]

    def get_chunk_by_id(self, chunk_id):
        return self.children.get(chunk_id)

    def get_parent(self, parent_id):
        return self.parents.get(parent_id)


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def chat(self, prompt, json_mode=False):
        self.calls += 1
        if "关键词" in prompt:
            return json.dumps(["Ag NPs"])
        return self.response


def test_fake_index_and_fake_llm_run_complete_pipeline(tmp_path):
    llm = FakeLLM(
        json.dumps(
            {
                "answer": "Ag NPs were prepared by chemical reduction. [S1]",
                "claims": [
                    {
                        "claim": "Ag NPs were prepared by chemical reduction.",
                        "support_status": "supported",
                        "citation_ids": ["S1"],
                    }
                ],
                "agent_analysis": "Agent 分析：仅基于给定证据。",
            }
        )
    )
    index = FakeIndex()

    result = run_synthesis_pipeline("How were Ag NPs synthesized?", index, llm, {"output_dir": str(tmp_path)})

    assert result.claims[0].citation_ids == ["S1"]
    assert result.citations[0].source_id == "S1"
    assert index.vector_called is True
    assert index.bm25_called is True
    assert llm.calls >= 1


def test_pipeline_saves_markdown_to_temp_dir(tmp_path):
    llm = FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []}))

    result = run_synthesis_pipeline("query", FakeIndex(), llm, {"output_dir": str(tmp_path)})

    markdown_path = Path(result.metadata["markdown_path"])
    assert markdown_path.exists()
    assert markdown_path.parent == tmp_path
    assert "Answer. [S1]" in markdown_path.read_text(encoding="utf-8")


def test_empty_candidates_or_context_returns_conservative_result(tmp_path):
    llm = FakeLLM(json.dumps({"answer": "Should not be needed", "claims": []}))

    result = run_synthesis_pipeline("query", FakeIndex(empty=True), llm, {"output_dir": str(tmp_path)})

    assert "证据不足" in result.answer
    assert result.claims == []
    assert result.metadata["fallback"] is True
    assert Path(result.metadata["markdown_path"]).exists()


def test_pipeline_uses_fakes_without_real_api_or_real_index(tmp_path):
    index = FakeIndex()
    llm = FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []}))

    result = run_synthesis_pipeline(
        "query",
        index,
        llm,
        {
            "output_dir": str(tmp_path),
            "external_metadata": {"enabled": False},
            "reranker": {"enabled": False},
        },
    )

    assert result.metadata["candidate_count"] == 1
    assert index.vector_called is True
    assert index.bm25_called is True
    assert llm.calls >= 1
