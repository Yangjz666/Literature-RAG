from app.claim_verifier import verify_claims
from app.schemas_v2 import ClaimRecord, SourceCitation


def _citation() -> SourceCitation:
    return SourceCitation(
        citation_id="S1",
        source_id="S1",
        paper_name="Zhang_2023",
        evidence_text="The Ag NPs were prepared by chemical reduction at 25 °C for 2 h.",
    )


def _claim(**overrides) -> ClaimRecord:
    values = {
        "claim": "The Ag NPs were prepared by chemical reduction.",
        "support_status": "supported",
        "citation_ids": ["S1"],
    }
    values.update(overrides)
    return ClaimRecord(**values)


def test_supported_claim_remains_supported():
    verified = verify_claims([_claim()], [_citation()])

    assert verified[0].support_status == "supported"
    assert verified[0].evidence[0].citation_id == "S1"


def test_claim_without_citation_is_unsupported():
    verified = verify_claims([_claim(citation_ids=[])], [_citation()])

    assert verified[0].support_status == "unsupported"
    assert "缺少 citation_ids" in verified[0].rationale


def test_missing_citation_id_is_unsupported():
    verified = verify_claims([_claim(citation_ids=["S404"])], [_citation()])

    assert verified[0].support_status == "unsupported"
    assert "S404" in verified[0].rationale


def test_numeric_mismatch_is_not_supported():
    verified = verify_claims(
        [_claim(claim="The Ag NPs were prepared at 80 °C for 12 h.")],
        [_citation()],
    )

    assert verified[0].support_status != "supported"
    assert verified[0].support_status == "partially_supported"


def test_agent_analysis_claim_is_preserved_but_not_literature_conclusion():
    verified = verify_claims(
        [
            _claim(
                claim="Agent analysis: this route may be scalable.",
                is_agent_analysis=True,
            )
        ],
        [_citation()],
    )

    assert verified[0].is_agent_analysis is True
    assert verified[0].support_status == "partially_supported"


def test_verifier_exception_conservatively_downgrades(monkeypatch):
    def raise_error(claim, citation_by_id):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.claim_verifier._verify_single_claim", raise_error)

    verified = verify_claims([_claim()], [_citation()])

    assert verified[0].support_status == "unsupported"
    assert "异常" in verified[0].rationale
