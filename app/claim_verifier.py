from __future__ import annotations

import re
from typing import Any

from app.schemas_v2 import ClaimRecord, SourceCitation


NUMERIC_SIGNAL_RE = re.compile(
    r"[-+]?\d+(?:\.\d+)?\s*(?:%|°C|℃|V|mV|h|min|s|M|mM|mmol/L|mol/L|rpm|sccm|mL|L|mg|g|nm|cm2|cm-2)?",
    re.IGNORECASE,
)


def _citation_key(citation: SourceCitation) -> list[str]:
    return [key for key in (citation.citation_id, citation.source_id) if key]


def _claim_citation_ids(claim: ClaimRecord) -> list[str]:
    raw_ids = claim.citation_ids or claim.source_ids
    return [str(source_id).strip("[]") for source_id in raw_ids if str(source_id)]


def _normalize_numeric(value: str) -> str:
    return re.sub(r"\s+", "", value).replace("℃", "°C").lower()


def _numeric_signals(text: str) -> list[str]:
    signals: list[str] = []
    for match in NUMERIC_SIGNAL_RE.finditer(text or ""):
        value = match.group(0).strip()
        if not value:
            continue
        normalized = _normalize_numeric(value)
        if normalized and normalized not in signals:
            signals.append(normalized)
    return signals


def _with_status(claim: ClaimRecord, status: str, rationale: str, evidence: list[SourceCitation]) -> ClaimRecord:
    updated = claim.model_copy(deep=True)
    updated.support_status = status
    updated.rationale = rationale
    updated.evidence = evidence
    ids = _claim_citation_ids(updated)
    updated.citation_ids = ids
    updated.source_ids = ids
    return updated


def _verify_single_claim(
    claim: ClaimRecord,
    citation_by_id: dict[str, SourceCitation],
) -> ClaimRecord:
    citation_ids = _claim_citation_ids(claim)
    if not citation_ids:
        return _with_status(claim, "unsupported", "缺少 citation_ids，无法验证。", [])

    missing_ids = [source_id for source_id in citation_ids if source_id not in citation_by_id]
    if missing_ids:
        return _with_status(
            claim,
            "unsupported",
            f"citation_id 不存在：{', '.join(missing_ids)}",
            [],
        )

    evidence = [citation_by_id[source_id] for source_id in citation_ids]
    evidence_text = " ".join(citation.evidence_text or "" for citation in evidence)
    evidence_numeric = set(_numeric_signals(evidence_text))
    missing_numeric = [
        value for value in _numeric_signals(claim.claim) if value not in evidence_numeric
    ]

    if missing_numeric and claim.support_status == "supported":
        return _with_status(
            claim,
            "partially_supported",
            f"证据中未找到对应数值/单位：{', '.join(missing_numeric)}",
            evidence,
        )

    if claim.is_agent_analysis and claim.support_status == "supported":
        return _with_status(
            claim,
            "partially_supported",
            "Agent 分析保留为分析性结论，不作为文献明确结论。",
            evidence,
        )

    return _with_status(claim, claim.support_status, claim.rationale, evidence)


def verify_claims(
    claims: list[ClaimRecord],
    citations: list[SourceCitation],
    llm_client: Any = None,
    config: dict | None = None,
) -> list[ClaimRecord]:
    citation_by_id: dict[str, SourceCitation] = {}
    for citation in citations:
        for key in _citation_key(citation):
            citation_by_id[key] = citation

    verified: list[ClaimRecord] = []
    for claim in claims:
        try:
            verified.append(_verify_single_claim(claim, citation_by_id))
        except Exception as exc:
            verified.append(
                _with_status(
                    claim,
                    "unsupported",
                    f"claim verifier 异常，已保守降级：{exc}",
                    [],
                )
            )
    return verified
