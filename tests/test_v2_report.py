from pathlib import Path

from app.report_v2 import generate_markdown_v2, save_markdown_v2
from app.schemas_v2 import ClaimRecord, SourceCitation, SynthesisResult


def _sample_result() -> SynthesisResult:
    s1 = SourceCitation(
        source_id="S1",
        paper_name="Zhang_2023",
        page=3,
        section="Experimental",
        evidence_text="The Ag NPs were prepared by chemical reduction.",
    )
    return SynthesisResult(
        query="Ag 催化剂如何合成？",
        claims=[
            ClaimRecord(
                claim="Ag NPs 通过化学还原法制备。",
                support_status="supported",
                source_ids=["S1"],
                evidence=[s1],
                structured_fields={"catalyst": "Ag NPs", "method": "chemical reduction"},
            ),
            ClaimRecord(
                claim="反应需要 200 °C 高温煅烧。",
                support_status="unsupported",
                rationale="给定证据中没有高温煅烧描述。",
            ),
        ],
        citations=[s1],
        literature_analysis="Zhang_2023 提供了明确合成路线。",
        agent_analysis="仅基于给定证据生成。",
    )


def test_generate_markdown_v2_contains_required_sections():
    markdown = generate_markdown_v2(_sample_result())

    required_sections = [
        "# 查询结果：Ag 催化剂如何合成？",
        "## 一、综合回答",
        "## 二、关键结论与证据支持状态",
        "## 三、结构化信息表",
        "## 四、文献对比与分析",
        "## 五、Agent 分析",
        "## 六、不确定项",
        "## 七、原文证据摘录",
    ]
    for section in required_sections:
        assert section in markdown


def test_generate_markdown_v2_includes_s1_evidence_excerpt():
    markdown = generate_markdown_v2(_sample_result())

    assert "[S1]" in markdown
    assert "The Ag NPs were prepared by chemical reduction." in markdown


def test_unsupported_claim_not_in_answer_body():
    markdown = generate_markdown_v2(_sample_result())

    answer_body = markdown.split("## 二、关键结论与证据支持状态", maxsplit=1)[0]
    assert "Ag NPs 通过化学还原法制备。" in answer_body
    assert "反应需要 200 °C 高温煅烧。" not in answer_body


def test_save_markdown_v2_writes_v2_synthesis_markdown(tmp_path):
    markdown = generate_markdown_v2(_sample_result())

    path = Path(save_markdown_v2(markdown, "Ag 催化剂如何合成？", tmp_path))

    assert path.exists()
    assert path.suffix == ".md"
    assert "v2_synthesis" in path.name
    assert path.read_text(encoding="utf-8") == markdown
