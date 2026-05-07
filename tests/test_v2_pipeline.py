import json
from pathlib import Path

import app.pipeline_v2 as pipeline_v2
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
    assert result.feedback_trace


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
    assert result.feedback_trace[0].notes == ["self_feedback disabled"]


def test_pipeline_calls_verify_claims(monkeypatch, tmp_path):
    called = {"value": False}

    def fake_verify_claims(claims, citations, llm_client=None, config=None):
        called["value"] = True
        return claims

    monkeypatch.setattr(pipeline_v2, "verify_claims", fake_verify_claims)
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
            }
        )
    )

    run_synthesis_pipeline("query", FakeIndex(), llm, {"output_dir": str(tmp_path)})

    assert called["value"] is True


def test_unsupported_claim_does_not_enter_markdown_main_answer(tmp_path):
    llm = FakeLLM(
        json.dumps(
            {
                "answer": "The catalyst reached 99% FE. [S1]",
                "claims": [
                    {
                        "claim": "The catalyst reached 99% FE.",
                        "support_status": "supported",
                        "citation_ids": ["S1"],
                    }
                ],
            }
        )
    )

    result = run_synthesis_pipeline("query", FakeIndex(), llm, {"output_dir": str(tmp_path)})
    markdown = Path(result.metadata["markdown_path"]).read_text(encoding="utf-8")
    answer_body = markdown.split("## 二、关键结论与证据支持状态", maxsplit=1)[0]

    assert result.claims[0].support_status != "supported"
    assert "99% FE" not in answer_body


def test_pipeline_records_feedback_trace_when_enabled(tmp_path):
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
            }
        )
    )

    def feedback_chat(prompt, json_mode=False):
        llm.calls += 1
        if "关键词" in prompt:
            return json.dumps(["Ag NPs"])
        if "自检模块" in prompt:
            return json.dumps({"missing_aspects": ["electrolyte"], "revision_instructions": ["Note missing electrolyte"]})
        return llm.response

    llm.chat = feedback_chat

    result = run_synthesis_pipeline("query", FakeIndex(), llm, {"output_dir": str(tmp_path), "self_feedback": {"enabled": True}})

    assert result.feedback_trace[0].missing_aspects == ["electrolyte"]
    markdown = Path(result.metadata["markdown_path"]).read_text(encoding="utf-8")
    assert "electrolyte" in markdown


def test_pipeline_feedback_failure_does_not_crash(tmp_path):
    llm = FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []}))

    def feedback_chat(prompt, json_mode=False):
        llm.calls += 1
        if "关键词" in prompt:
            return json.dumps(["Ag NPs"])
        if "自检模块" in prompt:
            return "not json"
        return llm.response

    llm.chat = feedback_chat

    result = run_synthesis_pipeline("query", FakeIndex(), llm, {"output_dir": str(tmp_path), "self_feedback": {"enabled": True}})

    assert result.feedback_trace[0].notes
    assert Path(result.metadata["markdown_path"]).exists()


def test_pipeline_calls_followup_retriever_when_feedback_requests_it(monkeypatch, tmp_path):
    called = {"value": False}

    def fake_followup_retrieval(feedback, index, llm_client, config, existing_chunk_ids=None):
        called["value"] = True
        return []

    monkeypatch.setattr(pipeline_v2, "run_followup_retrieval", fake_followup_retrieval)
    llm = FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []}))

    def feedback_chat(prompt, json_mode=False):
        llm.calls += 1
        if "关键词" in prompt:
            return json.dumps(["Ag NPs"])
        if "自检模块" in prompt:
            return json.dumps({"need_followup_retrieval": True, "followup_queries": ["electrolyte"]})
        return llm.response

    llm.chat = feedback_chat

    result = run_synthesis_pipeline(
        "query",
        FakeIndex(),
        llm,
        {"output_dir": str(tmp_path), "self_feedback": {"enabled": True, "allow_followup_retrieval": True}},
    )

    assert called["value"] is True
    assert result.metadata["followup_chunk_count"] == 0


def test_pipeline_followup_results_enter_trace(monkeypatch, tmp_path):
    def fake_followup_retrieval(feedback, index, llm_client, config, existing_chunk_ids=None):
        from app.schemas_v2 import CandidateChunk

        return [CandidateChunk(chunk_id="p2", text="Follow-up electrolyte evidence.", paper_name="FollowPaper")]

    monkeypatch.setattr(pipeline_v2, "run_followup_retrieval", fake_followup_retrieval)
    llm = FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []}))

    def feedback_chat(prompt, json_mode=False):
        llm.calls += 1
        if "关键词" in prompt:
            return json.dumps(["Ag NPs"])
        if "自检模块" in prompt:
            return json.dumps({"need_followup_retrieval": True, "followup_queries": ["electrolyte"]})
        return llm.response

    llm.chat = feedback_chat

    result = run_synthesis_pipeline(
        "query",
        FakeIndex(),
        llm,
        {"output_dir": str(tmp_path), "self_feedback": {"enabled": True, "allow_followup_retrieval": True}},
    )

    assert result.feedback_trace[0].followup_chunk_ids == ["p2"]
    assert result.metadata["followup_chunk_count"] == 1
    assert result.metadata["followup_context_citation_count"] >= 1


def test_pipeline_followup_failure_does_not_crash(monkeypatch, tmp_path):
    def failing_followup(*args, **kwargs):
        raise RuntimeError("followup failed")

    monkeypatch.setattr(pipeline_v2, "run_followup_retrieval", failing_followup)
    llm = FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []}))

    def feedback_chat(prompt, json_mode=False):
        llm.calls += 1
        if "关键词" in prompt:
            return json.dumps(["Ag NPs"])
        if "自检模块" in prompt:
            return json.dumps({"need_followup_retrieval": True, "followup_queries": ["electrolyte"]})
        return llm.response

    llm.chat = feedback_chat

    result = run_synthesis_pipeline(
        "query",
        FakeIndex(),
        llm,
        {"output_dir": str(tmp_path), "self_feedback": {"enabled": True, "allow_followup_retrieval": True}},
    )

    assert result.feedback_trace[0].followup_error == "followup failed"
    assert Path(result.metadata["markdown_path"]).exists()
