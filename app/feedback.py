from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.schemas_v2 import FeedbackRecord, SourceCitation, SynthesisResult


SELF_FEEDBACK_PROMPT = """你是 CO2RR-LocalScholar V2 的自检模块。

只检查给定 draft 与 citations，不得引入外部来源，不得发起新检索。
请输出 JSON，字段必须包含：
{
  "unsupported_claims": [],
  "missing_aspects": [],
  "citation_mismatch": [],
  "mixed_paper_conditions": [],
  "need_followup_retrieval": false,
  "followup_queries": [],
  "revision_instructions": []
}

需要检查：
1. unsupported_claims
2. missing_aspects
3. citation_mismatch
4. mixed_paper_conditions
5. need_followup_retrieval
6. revision_instructions

QUERY:
__QUERY__

DRAFT ANSWER:
__ANSWER__

CLAIMS:
__CLAIMS__

CITATIONS:
__CITATIONS__
"""


def _empty_feedback(note: str | None = None) -> FeedbackRecord:
    notes = [note] if note else []
    return FeedbackRecord(notes=notes, max_iterations=1)


def _feedback_config(config: dict | None) -> dict:
    return (config or {}).get("self_feedback") or {}


def _call_llm(prompt: str, llm_client: Any) -> str:
    if llm_client is None:
        return ""
    chat = getattr(llm_client, "chat", None)
    if chat is None:
        return ""
    try:
        return chat(prompt, json_mode=True)
    except TypeError:
        return chat(prompt)


def _claims_payload(result: SynthesisResult) -> str:
    return json.dumps(
        [
            {
                "claim": claim.claim,
                "support_status": claim.support_status,
                "citation_ids": claim.citation_ids,
                "source_ids": claim.source_ids,
                "rationale": claim.rationale,
                "is_agent_analysis": claim.is_agent_analysis,
                "is_agent_inference": claim.is_agent_inference,
            }
            for claim in result.claims
        ],
        ensure_ascii=False,
    )


def _citations_payload(citations: list[SourceCitation]) -> str:
    return json.dumps(
        [
            {
                "citation_id": citation.citation_id,
                "source_id": citation.source_id,
                "paper_name": citation.paper_name,
                "filename": citation.filename,
                "page": citation.page,
                "section": citation.section,
                "is_si": citation.is_si,
                "evidence_text": citation.evidence_text,
            }
            for citation in citations
        ],
        ensure_ascii=False,
    )


def _build_prompt(query: str, result: SynthesisResult, citations: list[SourceCitation]) -> str:
    return (
        SELF_FEEDBACK_PROMPT
        .replace("__QUERY__", query)
        .replace("__ANSWER__", result.answer)
        .replace("__CLAIMS__", _claims_payload(result))
        .replace("__CITATIONS__", _citations_payload(citations))
    )


def run_self_feedback(
    query: str,
    result: SynthesisResult,
    citations: list[SourceCitation],
    llm_client: Any = None,
    config: dict | None = None,
) -> FeedbackRecord:
    feedback_cfg = _feedback_config(config)
    if not feedback_cfg.get("enabled", False):
        return _empty_feedback("self_feedback disabled")

    max_iterations = int(feedback_cfg.get("max_iterations", 1))
    if max_iterations > 1:
        max_iterations = 1

    prompt = _build_prompt(query, result, citations)
    try:
        raw = _call_llm(prompt, llm_client)
    except Exception as exc:
        return _empty_feedback(f"self_feedback llm error: {exc}")

    if not raw or not raw.strip():
        return _empty_feedback("self_feedback empty llm response")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _empty_feedback(f"self_feedback invalid json: {exc.msg}")

    if not isinstance(parsed, dict):
        return _empty_feedback("self_feedback json top-level is not an object")

    try:
        feedback = FeedbackRecord.model_validate({**parsed, "max_iterations": max_iterations})
    except (ValidationError, TypeError, ValueError) as exc:
        return _empty_feedback(f"self_feedback validation error: {exc}")

    feedback.max_iterations = max_iterations
    return feedback
