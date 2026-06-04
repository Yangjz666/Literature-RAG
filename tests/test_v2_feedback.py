import json

from app.feedback import run_self_feedback
from app.schemas_v2 import ClaimRecord, SourceCitation, SynthesisResult


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def chat(self, prompt, json_mode=False):
        self.calls += 1
        return self.response


def _citation() -> SourceCitation:
    return SourceCitation(
        citation_id="S1",
        source_id="S1",
        paper_name="Zhang_2023",
        evidence_text="Ag NPs were prepared by chemical reduction.",
    )


def _result() -> SynthesisResult:
    return SynthesisResult(
        query="How were Ag NPs synthesized?",
        answer="Ag NPs were prepared by chemical reduction. [S1]",
        claims=[
            ClaimRecord(
                claim="Ag NPs were prepared by chemical reduction.",
                support_status="supported",
                citation_ids=["S1"],
            )
        ],
        citations=[_citation()],
    )


def test_self_feedback_disabled_returns_empty_feedback():
    llm = FakeLLM("{}")

    feedback = run_self_feedback("query", _result(), [_citation()], llm, {"self_feedback": {"enabled": False}})

    assert feedback.unsupported_claims == []
    assert feedback.need_followup_retrieval is False
    assert "disabled" in feedback.notes[0]
    assert llm.calls == 0


def test_fake_llm_valid_json_parses_feedback_record():
    llm = FakeLLM(
        json.dumps(
            {
                "unsupported_claims": ["Unsupported FE claim"],
                "missing_aspects": ["electrolyte"],
                "citation_mismatch": ["S1 does not support FE"],
                "mixed_paper_conditions": [],
                "need_followup_retrieval": False,
                "followup_queries": [],
                "revision_instructions": ["Remove unsupported FE claim"],
            }
        )
    )

    feedback = run_self_feedback("query", _result(), [_citation()], llm, {"self_feedback": {"enabled": True}})

    assert feedback.unsupported_claims == ["Unsupported FE claim"]
    assert feedback.missing_aspects == ["electrolyte"]
    assert feedback.citation_mismatch == ["S1 does not support FE"]
    assert feedback.revision_instructions == ["Remove unsupported FE claim"]


def test_fake_llm_invalid_json_does_not_crash():
    feedback = run_self_feedback("query", _result(), [_citation()], FakeLLM("not json"), {"self_feedback": {"enabled": True}})

    assert feedback.unsupported_claims == []
    assert feedback.notes
    assert "invalid json" in feedback.notes[0]


def test_feedback_records_unsupported_claims_citation_mismatch_and_missing_aspects():
    llm = FakeLLM(
        json.dumps(
            {
                "unsupported_claims": ["unsupported"],
                "missing_aspects": ["missing"],
                "citation_mismatch": ["mismatch"],
                "mixed_paper_conditions": [],
                "need_followup_retrieval": False,
                "followup_queries": [],
                "revision_instructions": [],
            }
        )
    )

    feedback = run_self_feedback("query", _result(), [_citation()], llm, {"self_feedback": {"enabled": True}})

    assert feedback.unsupported_claims == ["unsupported"]
    assert feedback.citation_mismatch == ["mismatch"]
    assert feedback.missing_aspects == ["missing"]


def test_followup_retrieval_request_is_recorded_but_not_executed():
    llm = FakeLLM(
        json.dumps(
            {
                "unsupported_claims": [],
                "missing_aspects": [],
                "citation_mismatch": [],
                "mixed_paper_conditions": [],
                "need_followup_retrieval": True,
                "followup_queries": ["Ag NPs electrolyte"],
                "revision_instructions": [],
            }
        )
    )

    feedback = run_self_feedback("query", _result(), [_citation()], llm, {"self_feedback": {"enabled": True}})

    assert feedback.need_followup_retrieval is True
    assert feedback.followup_queries == ["Ag NPs electrolyte"]
    assert llm.calls == 1


def test_max_iterations_is_stable_at_one():
    llm = FakeLLM(json.dumps({"need_followup_retrieval": True, "followup_queries": ["q"]}))

    feedback = run_self_feedback("query", _result(), [_citation()], llm, {"self_feedback": {"enabled": True, "max_iterations": 5}})

    assert feedback.max_iterations == 1
