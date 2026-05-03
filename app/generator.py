import os
import re
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llm_client import LLMClient

# ── 表格列定义 ────────────────────────────────────────────────────────────────

_SYNTHESIS_COLS = [
    ("paper_name", "文献名称"),
    ("catalyst", "催化剂"),
    ("method_type", "合成方法"),
    ("precursors", "原料"),
    ("solvent", "溶剂"),
    ("temperature", "温度"),
    ("time", "时间"),
    ("post_treatment", "后处理"),
    ("evidence_sentence", "原文证据"),
    ("page", "页码/章节"),
    ("confidence", "可信度"),
]

_TEST_COLS = [
    ("paper_name", "文献名称"),
    ("catalyst", "催化剂"),
    ("cell_type", "电解池"),
    ("electrolyte", "电解液"),
    ("co2_flow_rate", "CO2 流速"),
    ("potential_or_current", "电位/电流密度"),
    ("product", "主要产物"),
    ("faradaic_efficiency", "FE"),
    ("evidence_sentence", "原文证据"),
    ("page", "页码/章节"),
    ("confidence", "可信度"),
]

_MECHANISM_COLS = [
    ("paper_name", "文献名称"),
    ("additive", "添加剂"),
    ("catalyst_system", "催化剂体系"),
    ("main_effect", "主要作用"),
    ("mechanism_explanation", "机理解释"),
    ("evidence_sentence", "原文证据"),
    ("page", "页码/章节"),
    ("confidence", "可信度"),
]

_COLS_MAP = {
    "synthesis": _SYNTHESIS_COLS,
    "test": _TEST_COLS,
    "mechanism": _MECHANISM_COLS,
}


def _cell(value) -> str:
    if value is None:
        return "未明确说明"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else "未明确说明"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _is_main_table_eligible(rec: dict) -> bool:
    return (
        rec.get("confidence") in ("高", "中")
        and not rec.get("is_agent_inference", False)
        and bool(rec.get("evidence_sentence", "").strip())
        and bool(rec.get("paper_name", "").strip())
    )


def generate_markdown_table(records: list[dict], query_type: str = "synthesis") -> str:
    cols = _COLS_MAP.get(query_type, _SYNTHESIS_COLS)
    header = "| " + " | ".join(cn for _, cn in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for rec in records:
        si_note = " (SI)" if rec.get("is_si") else ""
        row_cells = []
        for field, _ in cols:
            val = rec.get(field)
            if field == "paper_name":
                val = f"{_cell(val)}{si_note}"
            else:
                val = _cell(val)
            row_cells.append(val)
        rows.append("| " + " | ".join(row_cells) + " |")
    return "\n".join([header, sep] + rows)


def generate_markdown_output(
    records: list[dict],
    query: str = "",
    query_type: str = "synthesis",
) -> str:
    if not records:
        return f"# 查询结果：{query}\n\n在当前文献库中未找到相关内容，请尝试换用其他关键词，或检查文献是否已正确导入。\n"

    main_records = [r for r in records if _is_main_table_eligible(r)]
    inferred = [r for r in records if r.get("is_agent_inference")]
    uncertain = [r for r in records if not _is_main_table_eligible(r) and not r.get("is_agent_inference")]

    lines = [f"# 查询结果：{query}\n"]

    # 主表格
    lines.append("## 文献明确说明\n")
    if main_records:
        lines.append(generate_markdown_table(main_records, query_type))
    else:
        lines.append("_未找到可信度足够的文献明确结论。_")
    lines.append("")

    # 原文证据摘录
    if main_records:
        lines.append("## 原文证据摘录\n")
        for rec in main_records:
            paper = rec.get("paper_name", "?")
            page = rec.get("page", "?")
            section = rec.get("section", "")
            evidence = rec.get("evidence_sentence", "")
            si_note = "（来源：Supporting Information）" if rec.get("is_si") else ""
            lines.append(f"**{paper}** | 第 {page} 页 {section} {si_note}")
            lines.append(f"> {evidence}\n")

    # Agent 分析
    if inferred:
        lines.append("## Agent 分析\n")
        lines.append("_以下内容为 Agent 推测，不代表文献明确结论，请人工核查。_\n")
        lines.append(generate_markdown_table(inferred, query_type))
        lines.append("")

    # 不确定项
    if uncertain:
        lines.append("## 不确定项\n")
        lines.append("_以下记录证据校验失败或可信度不足，不应直接作为结论引用。_\n")
        for rec in uncertain:
            paper = rec.get("paper_name", "?")
            note = rec.get("confidence_note", "")
            evidence = rec.get("evidence_sentence", "")
            lines.append(f"- **{paper}**: {note}")
            if evidence:
                lines.append(f"  > {evidence}")
        lines.append("")

    return "\n".join(lines)


def _sanitize_filename(query: str, max_len: int = 40) -> str:
    clean = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", query)
    clean = clean.strip().replace(" ", "_")
    return clean[:max_len] if clean else "query"


def save_output(content: str, query: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{_sanitize_filename(query)}.md"
    path = os.path.join(output_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


STREAM_PROMPT = """你是 CO2RR 文献阅读助手。
根据以下结构化抽取结果，用中文生成一份清晰的 Markdown 格式分析报告。
报告应包含：总体结论、各文献要点、可借鉴实验路线（仅基于原文，不创造新方案）。
不要重复输出表格，只做文字分析。

用户问题：{query}

抽取结果摘要：
{summary}"""


def build_stream_prompt(query: str, records: list[dict]) -> str:
    summary_lines = []
    for rec in records:
        if not _is_main_table_eligible(rec):
            continue
        paper = rec.get("paper_name", "?")
        evidence = rec.get("evidence_sentence", "")
        summary_lines.append(f"- {paper}: {evidence[:200]}")
    summary = "\n".join(summary_lines) if summary_lines else "（无高可信度记录）"
    return STREAM_PROMPT.format(query=query, summary=summary)
