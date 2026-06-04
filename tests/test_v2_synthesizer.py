import json

from app.schemas_v2 import SourceCitation
from app.synthesizer import synthesize_with_citations


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.prompts = []

    def chat(self, prompt, json_mode=False):
        self.prompts.append((prompt, json_mode))
        return self.response


def _citation() -> SourceCitation:
    return SourceCitation(
        citation_id="S1",
        source_id="S1",
        paper_name="Zhang_2023",
        evidence_text="Ag NPs were prepared by chemical reduction.",
        chunk_id="p1",
    )


def test_fake_llm_valid_json_generates_synthesis_result():
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
                "structured_table": [],
                "literature_analysis": "One paper reports the synthesis.",
                "agent_analysis": "Agent 分析：仅基于给定证据。",
                "uncertainties": [],
            }
        )
    )

    result = synthesize_with_citations("query", "[S1]\nText: evidence", [_citation()], llm, {})

    assert result.answer.startswith("Ag NPs")
    assert result.claims[0].claim == "Ag NPs were prepared by chemical reduction."
    assert result.metadata["fallback"] is False
    assert llm.prompts[0][1] is True
    assert "只能使用 CONTEXT" in llm.prompts[0][0]


def test_fake_llm_invalid_json_does_not_crash():
    result = synthesize_with_citations("query", "[S1]\nText: evidence", [_citation()], FakeLLM("not json"), {})

    assert "证据不足" in result.answer
    assert result.claims == []
    assert result.metadata["fallback"] is True
    assert result.uncertainties


def test_claim_citation_ids_are_preserved():
    llm = FakeLLM(
        json.dumps(
            {
                "answer": "Supported answer. [S1]",
                "claims": [
                    {
                        "claim": "Supported claim.",
                        "support_status": "supported",
                        "citation_ids": ["S1"],
                    }
                ],
            }
        )
    )

    result = synthesize_with_citations("query", "[S1]\nText: evidence", [_citation()], llm, {})

    assert result.claims[0].citation_ids == ["S1"]
    assert result.claims[0].source_ids == ["S1"]


def test_citations_enter_result():
    citation = _citation()

    result = synthesize_with_citations(
        "query",
        "[S1]\nText: evidence",
        [citation],
        FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []})),
        {},
    )

    assert result.citations == [citation]
