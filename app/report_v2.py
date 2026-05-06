from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.schemas_v2 import ClaimRecord, SourceCitation, SynthesisResult


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "未明确说明"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "未明确说明"
    if isinstance(value, dict):
        return ", ".join(f"{key}: {val}" for key, val in value.items()) if value else "未明确说明"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _citation_label(source: SourceCitation) -> str:
    return source.source_id if source.source_id.startswith("[") else f"[{source.source_id}]"


def _claim_sources(claim: ClaimRecord) -> str:
    labels = []
    for citation in claim.evidence:
        if citation.source_id:
            labels.append(_citation_label(citation))
    for source_id in [*claim.citation_ids, *claim.source_ids]:
        label = source_id if source_id.startswith("[") else f"[{source_id}]"
        if label not in labels:
            labels.append(label)
    return " ".join(labels) if labels else "无"


def _render_claim_table(claims: list[ClaimRecord]) -> str:
    rows = [
        "| 结论 | 支持状态 | 证据来源 | 说明 |",
        "| --- | --- | --- | --- |",
    ]
    for claim in claims:
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(claim.claim),
                    _cell(claim.support_status),
                    _claim_sources(claim),
                    _cell(claim.rationale),
                ]
            )
            + " |"
        )
    return "\n".join(rows) if claims else "_暂无关键结论。_"


def _render_structured_table(result: SynthesisResult) -> str:
    rows = list(result.structured_table)
    if not rows:
        for claim in result.claims:
            if claim.structured_fields:
                row = {"claim": claim.claim, **claim.structured_fields}
                rows.append(row)
    if not rows:
        return "_暂无结构化信息。_"

    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    lines = [
        "| " + " | ".join(keys) + " |",
        "| " + " | ".join("---" for _ in keys) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row.get(key)) for key in keys) + " |")
    return "\n".join(lines)


def _supported_summary(result: SynthesisResult) -> str:
    supported_claims = [
        claim
        for claim in result.claims
        if claim.support_status == "supported"
        and not claim.is_agent_analysis
        and not claim.is_agent_inference
    ]
    if supported_claims:
        return "\n".join(f"- {claim.claim} {_claim_sources(claim)}" for claim in supported_claims)
    if not result.claims and result.answer.strip():
        return result.answer.strip()
    return "_暂无可由原文证据支持的综合回答。_"


def _render_uncertainties(result: SynthesisResult) -> str:
    items = list(result.uncertainties)
    items.extend(
        claim.claim for claim in result.claims if claim.support_status == "unsupported" and claim.claim
    )
    if not items:
        return "_暂无不确定项。_"
    return "\n".join(f"- {item}" for item in items)


def _collect_citations(result: SynthesisResult) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    seen: set[str] = set()
    for citation in result.citations:
        key = citation.source_id or citation.evidence_text
        if key and key not in seen:
            citations.append(citation)
            seen.add(key)
    for claim in result.claims:
        for citation in claim.evidence:
            key = citation.source_id or citation.evidence_text
            if key and key not in seen:
                citations.append(citation)
                seen.add(key)
    return citations


def _render_citations(result: SynthesisResult) -> str:
    citations = _collect_citations(result)
    if not citations:
        return "_暂无原文证据摘录。_"

    lines = []
    for citation in citations:
        label = _citation_label(citation) if citation.source_id else "[S?]"
        paper = citation.paper_name or citation.filename or "未知文献"
        location_parts = []
        if citation.page is not None:
            location_parts.append(f"页码: {citation.page}")
        if citation.section:
            location_parts.append(f"章节: {citation.section}")
        if citation.is_si:
            location_parts.append("SI")
        location = " | ".join(location_parts)
        suffix = f" | {location}" if location else ""
        lines.append(f"**{label} {paper}{suffix}**")
        lines.append(f"> {citation.evidence_text or '未提供原文摘录。'}")
        lines.append("")
    return "\n".join(lines).rstrip()


def generate_markdown_v2(result: SynthesisResult) -> str:
    if not isinstance(result, SynthesisResult):
        result = SynthesisResult.model_validate(result)

    lines = [
        f"# 查询结果：{result.query}",
        "",
        "## 一、综合回答",
        "",
        _supported_summary(result),
        "",
        "## 二、关键结论与证据支持状态",
        "",
        _render_claim_table(result.claims),
        "",
        "## 三、结构化信息表",
        "",
        _render_structured_table(result),
        "",
        "## 四、文献对比与分析",
        "",
        result.literature_analysis or "_暂无文献对比与分析。_",
        "",
        "## 五、Agent 分析",
        "",
        result.agent_analysis or "_暂无 Agent 分析。_",
        "",
        "## 六、不确定项",
        "",
        _render_uncertainties(result),
        "",
        "## 七、原文证据摘录",
        "",
        _render_citations(result),
        "",
    ]
    return "\n".join(lines)


def _sanitize_filename(query: str, max_len: int = 40) -> str:
    clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", query)
    clean = clean.strip().replace(" ", "_")
    return clean[:max_len] if clean else "query"


def save_markdown_v2(markdown: str, query: str, output_dir: str | os.PathLike[str]) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_v2_synthesis_{_sanitize_filename(query)}.md"
    path = Path(output_dir) / filename
    path.write_text(markdown, encoding="utf-8")
    return str(path)
