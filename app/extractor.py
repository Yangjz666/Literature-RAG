from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from app.llm_client import LLMClient

logger = logging.getLogger(__name__)
llm_client = None


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SourceRecord(BaseModel):
    paper_name: str
    filename: str | None = None
    doi: str | None = None
    page: str | None = None
    section: str | None = None
    is_si: bool = False
    evidence_sentence: str
    is_agent_inference: bool = False


class SynthesisRecord(SourceRecord):
    catalyst: str
    method_type: str | None = None
    precursors: list[str] = []
    solvent: str | None = None
    temperature: str | None = None
    time: str | None = None
    post_treatment: str | None = None


class ElectrochemicalTestRecord(SourceRecord):
    catalyst: str
    cell_type: str | None = None
    electrolyte: str | None = None
    co2_flow_rate: str | None = None
    potential_or_current: str | None = None
    product: str | None = None
    faradaic_efficiency: str | None = None


class MechanismRecord(SourceRecord):
    additive: str | None = None
    catalyst_system: str | None = None
    main_effect: str | None = None
    mechanism_explanation: str | None = None


# ── Prompt 模板 ───────────────────────────────────────────────────────────────

_BASE_RULES = """你是严格的 CO2RR 文献信息抽取助手。

规则：
1. evidence_sentence 必须是原文中的完整原句或连续原文片段，不能改写或总结。
2. 原文没有明确说明的字段填 null，不允许根据常识补全。
3. 多篇文献的条件不能合并成一条记录，每篇文献单独输出一条。
4. 来自 Supporting Information 的内容必须保留 is_si=true。
5. 如果你做出推测，is_agent_inference=true，且该记录不得作为文献明确结论。
6. 只输出 JSON 数组，不输出解释性文本。"""

SYNTHESIS_PROMPT = _BASE_RULES + """

抽取字段：paper_name, filename, doi, page, section, is_si,
catalyst, method_type, precursors(数组), solvent, temperature, time,
post_treatment, evidence_sentence, is_agent_inference

用户问题：{query}

候选原文片段：
{context}"""

TEST_CONDITION_PROMPT = _BASE_RULES + """

抽取字段：paper_name, filename, doi, page, section, is_si,
catalyst, cell_type, electrolyte, co2_flow_rate, potential_or_current,
product, faradaic_efficiency, evidence_sentence, is_agent_inference

用户问题：{query}

候选原文片段：
{context}"""

MECHANISM_PROMPT = _BASE_RULES + """

抽取字段：paper_name, filename, doi, page, section, is_si,
additive, catalyst_system, main_effect, mechanism_explanation,
evidence_sentence, is_agent_inference

用户问题：{query}

候选原文片段：
{context}"""


def _format_context(chunks: list[dict]) -> str:
    parts = []
    for c in chunks:
        meta = c.get("metadata", c)
        header = (
            f"[文献: {meta.get('paper_name', meta.get('filename', '?'))} | "
            f"页码: {meta.get('page', '?')} | "
            f"章节: {meta.get('section', '?')} | "
            f"SI: {meta.get('is_si', False)}]"
        )
        parts.append(f"{header}\n{c.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def build_extraction_prompt(query: str, context: str, query_type: str = "synthesis") -> str:
    templates = {
        "synthesis": SYNTHESIS_PROMPT,
        "test": TEST_CONDITION_PROMPT,
        "mechanism": MECHANISM_PROMPT,
    }
    tmpl = templates.get(query_type, SYNTHESIS_PROMPT)
    return tmpl.format(query=query, context=context)


def _parse_records(raw: str, schema_cls) -> list[dict]:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # 有时 LLM 返回 {"records": [...]}
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break
        if not isinstance(data, list):
            data = [data]
        result = []
        for item in data:
            try:
                record = schema_cls(**item)
                result.append(record.model_dump())
            except ValidationError as e:
                logger.warning(f"记录校验失败，跳过: {e}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"LLM 返回非 JSON 内容: {e}\n原始内容: {raw[:200]}")
        return []


def extract_synthesis_info(
    query: str,
    chunks: list[dict],
    llm_client: "LLMClient" | None = None,
) -> list[dict]:
    client = llm_client or globals().get("llm_client")
    if client is None:
        raise RuntimeError("llm_client is required for extraction.")
    context = _format_context(chunks)
    prompt = build_extraction_prompt(query, context, "synthesis")
    raw = client.chat(prompt, json_mode=True)
    return _parse_records(raw, SynthesisRecord)


def extract_test_conditions(
    query: str,
    chunks: list[dict],
    llm_client: "LLMClient" | None = None,
) -> list[dict]:
    client = llm_client or globals().get("llm_client")
    if client is None:
        raise RuntimeError("llm_client is required for extraction.")
    context = _format_context(chunks)
    prompt = build_extraction_prompt(query, context, "test")
    raw = client.chat(prompt, json_mode=True)
    return _parse_records(raw, ElectrochemicalTestRecord)


def extract_mechanism_info(
    query: str,
    chunks: list[dict],
    llm_client: "LLMClient" | None = None,
) -> list[dict]:
    client = llm_client or globals().get("llm_client")
    if client is None:
        raise RuntimeError("llm_client is required for extraction.")
    context = _format_context(chunks)
    prompt = build_extraction_prompt(query, context, "mechanism")
    raw = client.chat(prompt, json_mode=True)
    return _parse_records(raw, MechanismRecord)


def detect_query_type(query: str) -> str:
    """简单规则判断查询类型，用于选择抽取 schema。"""
    q = query.lower()
    if any(w in q for w in ("合成", "制备", "synthesis", "preparation", "fabrication", "precursor")):
        return "synthesis"
    if any(w in q for w in ("测试", "电解", "fe", "faradaic", "cell", "electrolyte", "potential", "current")):
        return "test"
    if any(w in q for w in ("机理", "作用", "mechanism", "additive", "imidazol", "suppression", "enrichment")):
        return "mechanism"
    return "synthesis"
