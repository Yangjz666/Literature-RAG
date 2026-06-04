from __future__ import annotations

from enum import StrEnum


class QueryMode(StrEnum):
    STRUCTURED_EXTRACTION = "structured_extraction"
    SYNTHESIS = "synthesis"
    DEEP_READING = "deep_reading"


STRUCTURED_KEYWORDS = [
    "合成方法",
    "测试条件",
    "fe",
    "电解液",
    "表格",
    "提取",
    "extract",
    "table",
    "synthesis condition",
    "electrolyte",
]

SYNTHESIS_KEYWORDS = [
    "总结",
    "对比",
    "共同说明",
    "是否一致",
    "启发",
    "综合",
    "summarize",
    "compare",
    "synthesis",
    "insight",
    "mechanism",
]

DEEP_READING_KEYWORDS = [
    "精读",
    "解释这篇",
    "小白",
    "逐段",
    "单篇",
    "deep reading",
    "explain this paper",
    "beginner",
    "single paper",
]


def _normalize_mode(value: str | QueryMode | None) -> QueryMode | None:
    if value is None:
        return None
    if isinstance(value, QueryMode):
        return value
    normalized = str(value).strip().lower()
    for mode in QueryMode:
        if normalized == mode.value:
            return mode
    return None


def _default_mode(config: dict | None) -> QueryMode:
    config = config or {}
    v2_config = config.get("v2") or {}
    return _normalize_mode(v2_config.get("default_mode")) or QueryMode.STRUCTURED_EXTRACTION


def _contains_any(query: str, keywords: list[str]) -> bool:
    return any(keyword in query for keyword in keywords)


def detect_query_mode(
    query: str,
    explicit_mode: str | QueryMode | None = None,
    config: dict | None = None,
) -> QueryMode:
    explicit = _normalize_mode(explicit_mode)
    if explicit is not None:
        return explicit

    normalized_query = (query or "").strip().lower()
    if not normalized_query:
        return _default_mode(config)

    if _contains_any(normalized_query, DEEP_READING_KEYWORDS):
        return QueryMode.DEEP_READING
    if _contains_any(normalized_query, STRUCTURED_KEYWORDS):
        return QueryMode.STRUCTURED_EXTRACTION
    if _contains_any(normalized_query, SYNTHESIS_KEYWORDS):
        return QueryMode.SYNTHESIS
    return _default_mode(config)
