from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.schemas_v2 import ClaimRecord, SourceCitation, SynthesisResult


SYNTHESIS_PROMPT = """你是 CO2RR-LocalScholar V2 的文献综合模块。

必须遵守：
1. 只能使用 CONTEXT 中给出的信息。
2. 每个事实性 claim 必须带 citation_ids，例如 ["S1"]。
3. 不得引用 CONTEXT 外的论文、网页、常识或来源。
4. 原文未说明时，写“证据不足”或“未明确说明”。
5. Agent 分析必须单独放在 agent_analysis 字段，并标注这是基于证据边界的分析。
6. 只输出 JSON，不要输出 Markdown 或额外解释。

JSON schema:
{
  "answer": "string",
  "claims": [
    {
      "claim": "string",
      "support_status": "supported | partially_supported | unsupported",
      "citation_ids": ["S1"],
      "rationale": "string",
      "structured_fields": {},
      "is_agent_inference": false
    }
  ],
  "structured_table": [],
  "literature_analysis": "string",
  "agent_analysis": "string",
  "uncertainties": []
}

QUERY:
__QUERY__

CONTEXT:
__CONTEXT_TEXT__
"""


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


def _conservative_result(
    query: str,
    citations: list[SourceCitation],
    reason: str,
) -> SynthesisResult:
    return SynthesisResult(
        query=query,
        answer="证据不足，无法基于当前上下文生成可靠综合回答。",
        claims=[],
        citations=citations,
        literature_analysis="证据不足。",
        agent_analysis="Agent 分析：未生成外推结论，仅报告证据不足。",
        uncertainties=[reason],
        metadata={"fallback": True, "fallback_reason": reason},
    )


def _citation_map(citations: list[SourceCitation]) -> dict[str, SourceCitation]:
    mapped: dict[str, SourceCitation] = {}
    for citation in citations:
        for key in (citation.citation_id, citation.source_id):
            if key:
                mapped[key] = citation
    return mapped


def _normalize_claims(raw_claims: Any, citations: list[SourceCitation]) -> list[ClaimRecord]:
    if not isinstance(raw_claims, list):
        return []

    citation_by_id = _citation_map(citations)
    claims: list[ClaimRecord] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            continue
        raw_ids = raw_claim.get("citation_ids", raw_claim.get("source_ids", []))
        if isinstance(raw_ids, str):
            raw_ids = [raw_ids]
        if not isinstance(raw_ids, list):
            raw_ids = []
        citation_ids = [str(source_id).strip("[]") for source_id in raw_ids if str(source_id)]
        evidence = [citation_by_id[source_id] for source_id in citation_ids if source_id in citation_by_id]
        claim = ClaimRecord.model_validate(
            {
                **raw_claim,
                "citation_ids": citation_ids,
                "source_ids": citation_ids,
                "evidence": evidence,
            }
        )
        claims.append(claim)
    return claims


def synthesize_with_citations(
    query: str,
    context_text: str,
    citations: list[SourceCitation],
    llm_client: Any,
    config: dict,
) -> SynthesisResult:
    if not context_text.strip() or not citations:
        return _conservative_result(query, citations, "证据不足：没有可用于综合的上下文或引用。")

    prompt = SYNTHESIS_PROMPT.replace("__QUERY__", query).replace("__CONTEXT_TEXT__", context_text)
    raw = _call_llm(prompt, llm_client)
    if not raw or not raw.strip():
        return _conservative_result(query, citations, "LLM 返回空字符串。")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return _conservative_result(query, citations, f"LLM 返回非法 JSON：{exc.msg}")

    if not isinstance(parsed, dict):
        return _conservative_result(query, citations, "LLM JSON 顶层不是对象。")

    try:
        claims = _normalize_claims(parsed.get("claims", []), citations)
        result = SynthesisResult.model_validate(
            {
                "query": query,
                "answer": parsed.get("answer", ""),
                "claims": claims,
                "citations": citations,
                "structured_table": parsed.get("structured_table", []),
                "literature_analysis": parsed.get("literature_analysis", ""),
                "agent_analysis": parsed.get("agent_analysis", ""),
                "uncertainties": parsed.get("uncertainties", []),
                "metadata": {
                    **(parsed.get("metadata") if isinstance(parsed.get("metadata"), dict) else {}),
                    "fallback": False,
                },
            }
        )
    except (ValidationError, TypeError, ValueError) as exc:
        return _conservative_result(query, citations, f"LLM JSON 字段校验失败：{exc}")

    if not result.answer:
        return _conservative_result(query, citations, "LLM JSON 缺少 answer 字段。")
    return result
