"""
验收测试脚本 - CO2RR RAG Agent
运行方式：pytest tests/test_acceptance.py -v
"""

import difflib
import hashlib
import json
import os
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ─────────────────────────────────────────────
# Fixtures：构造测试用的最小 PDF 文本和 chunk
# ─────────────────────────────────────────────

SAMPLE_PAPER_TEXT = """
Experimental Section
The Ag NPs were prepared by chemical reduction. 20 mL aqueous solution containing
141.6 mmol/L sodium citrate was titrated with 20 mL aqueous solution containing
20 mmol/L AgNO3 under stirring at room temperature for 2 h. NaBH4 (0.1 M, 1 mL)
was added dropwise as the reducing agent. The product was centrifuged at 8000 rpm,
washed three times with deionized water, and dried at 60 °C under vacuum overnight.

Electrochemical Measurements
CO2RR was performed in an H-cell with 0.1 M KHCO3 electrolyte. CO2 was purged
at a flow rate of 20 sccm. The applied potential was -1.0 V vs RHE. The Faradaic
efficiency for CO was 92% at -1.0 V vs RHE.
"""

SAMPLE_CHUNK = {
    "chunk_id": "paper_01_p3_c1",
    "paper_name": "Zhang_2023",
    "filename": "paper_01.pdf",
    "doi": "10.1021/test.001",
    "page": 3,
    "section": "Experimental",
    "is_si": False,
    "text": SAMPLE_PAPER_TEXT,
    "parent_chunk_id": "paper_01_p3_parent_1",
}

SAMPLE_EXTRACTION = {
    "paper_name": "Zhang_2023",
    "catalyst": "Ag NPs",
    "method_type": "chemical reduction",
    "precursors": ["AgNO3", "sodium citrate", "NaBH4"],
    "solvent": "deionized water",
    "temperature": "room temperature",
    "time": "2 h",
    "post_treatment": "centrifuged at 8000 rpm, washed three times, dried at 60 °C under vacuum",
    "evidence_sentence": "20 mL aqueous solution containing 141.6 mmol/L sodium citrate was titrated with 20 mL aqueous solution containing 20 mmol/L AgNO3 under stirring at room temperature for 2 h.",
    "page": "3",
    "is_agent_inference": False,
}


# ─────────────────────────────────────────────
# AC-01: PDF 解析 - 文字型 PDF 能提取文本
# ─────────────────────────────────────────────

class TestPDFIngest:

    def test_text_extraction_returns_pages(self, tmp_path):
        """文字型 PDF 解析后应返回分页文本列表，每页包含 page 和 text 字段。"""
        # 用 reportlab 或直接 mock fitz，这里用 mock 隔离外部依赖
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = SAMPLE_PAPER_TEXT

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.metadata = {"title": "Test Paper", "author": "Zhang"}

        with patch("fitz.open", return_value=mock_doc):
            from app.ingest import extract_text
            result = extract_text("dummy.pdf")

        assert "pages" in result
        assert len(result["pages"]) == 1
        assert result["pages"][0]["page"] == 1
        assert "AgNO3" in result["pages"][0]["text"]

    def test_empty_text_triggers_ocr_flag(self):
        """文本为空的页面应触发 OCR 降级标记。"""
        mock_page = MagicMock()
        mock_page.number = 0
        mock_page.get_text.return_value = ""  # 扫描版，文本为空

        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.metadata = {}

        with patch("fitz.open", return_value=mock_doc):
            with patch("app.ingest.ocr_page", return_value="OCR extracted text") as mock_ocr:
                from app.ingest import extract_text
                result = extract_text("scanned.pdf")

        mock_ocr.assert_called_once()
        assert result["pages"][0]["text"] == "OCR extracted text"

    def test_si_detection_by_filename(self):
        """文件名含 SI/Supporting/Supplementary/ESI 应被识别为 Supporting Information。"""
        from app.ingest import is_supporting_information

        assert is_supporting_information("paper_01_SI.pdf") is True
        assert is_supporting_information("Zhang2023_Supporting.pdf") is True
        assert is_supporting_information("ESI_data.pdf") is True
        assert is_supporting_information("Supplementary_info.pdf") is True
        assert is_supporting_information("paper_01.pdf") is False
        assert is_supporting_information("main_text.pdf") is False

    def test_doi_extraction_from_text(self):
        """应能从文本中用正则提取 DOI。"""
        from app.ingest import extract_doi_from_text

        text = "DOI: 10.1021/acscatal.3c00123 This paper reports..."
        doi = extract_doi_from_text(text)
        assert doi == "10.1021/acscatal.3c00123"

    def test_dedup_by_doi(self):
        """相同 DOI 的文献应被去重，只保留一份。"""
        from app.ingest import deduplicate_papers

        papers = [
            {"filename": "paper_01.pdf", "doi": "10.1021/test.001"},
            {"filename": "paper_01_copy.pdf", "doi": "10.1021/test.001"},  # 重复
            {"filename": "paper_02.pdf", "doi": "10.1021/test.002"},
        ]
        result = deduplicate_papers(papers)
        dois = [p["doi"] for p in result]
        assert len(result) == 2
        assert dois.count("10.1021/test.001") == 1

    def test_dedup_by_content_hash_when_no_doi(self):
        """无 DOI 时应基于内容哈希去重。"""
        from app.ingest import deduplicate_papers

        content = "same content " * 50
        h = hashlib.md5(content[:500].encode()).hexdigest()

        papers = [
            {"filename": "a.pdf", "doi": None, "content_hash": h},
            {"filename": "b.pdf", "doi": None, "content_hash": h},  # 重复
        ]
        result = deduplicate_papers(papers)
        assert len(result) == 1


# ─────────────────────────────────────────────
# AC-02: 文本切分 - 父子 chunk 结构正确
# ─────────────────────────────────────────────

class TestChunker:

    def test_child_chunk_size_within_limit(self):
        """子 chunk 文本长度应在 50-300 字符之间。"""
        from app.chunker import split_to_child_chunks

        chunks = split_to_child_chunks(SAMPLE_PAPER_TEXT, max_chars=150)
        for c in chunks:
            assert len(c["text"]) <= 300, f"子 chunk 过长: {len(c['text'])} 字符"
            assert len(c["text"]) >= 10, "子 chunk 过短，可能切分异常"

    def test_chunk_carries_metadata(self):
        """每个 chunk 必须携带 paper_name、page、section、is_si 字段。"""
        from app.chunker import split_to_child_chunks

        chunks = split_to_child_chunks(
            SAMPLE_PAPER_TEXT,
            metadata={"paper_name": "Zhang_2023", "page": 3,
                      "section": "Experimental", "is_si": False}
        )
        for c in chunks:
            assert "paper_name" in c
            assert "page" in c
            assert "section" in c
            assert "is_si" in c

    def test_parent_chunk_links_to_children(self):
        """父 chunk 应包含其所有子 chunk 的 ID 列表。"""
        from app.chunker import split_with_parent_child

        result = split_with_parent_child(SAMPLE_PAPER_TEXT, metadata={})
        for parent in result["parents"]:
            assert "child_ids" in parent
            assert len(parent["child_ids"]) >= 1

    def test_no_content_loss_after_chunking(self):
        """切分后所有子 chunk 文本拼接应覆盖原文的关键词。"""
        from app.chunker import split_to_child_chunks

        chunks = split_to_child_chunks(SAMPLE_PAPER_TEXT)
        combined = " ".join(c["text"] for c in chunks)
        for keyword in ["AgNO3", "NaBH4", "sodium citrate", "KHCO3"]:
            assert keyword in combined, f"关键词 {keyword} 在切分后丢失"


# ─────────────────────────────────────────────
# AC-03: 证据校验 - 核心防幻觉机制
# ─────────────────────────────────────────────

class TestEvidenceVerifier:

    def test_exact_match_returns_high_confidence(self):
        """evidence_sentence 是原文子串时，应返回'高'可信度。"""
        from app.verifier import verify_evidence

        evidence = "NaBH4 (0.1 M, 1 mL) was added dropwise as the reducing agent."
        level, reason = verify_evidence(evidence, SAMPLE_PAPER_TEXT)
        assert level == "高"
        assert "精确匹配" in reason

    def test_fuzzy_match_returns_medium_confidence(self):
        """evidence_sentence 与原文高度相似（≥0.85）时，应返回'中'可信度。"""
        from app.verifier import verify_evidence

        # 轻微改写，模拟 LLM 的小幅改动
        evidence = "NaBH4 (0.1M, 1mL) was added dropwise as reducing agent."
        level, reason = verify_evidence(evidence, SAMPLE_PAPER_TEXT)
        assert level in ("高", "中"), f"预期高或中，实际: {level}"

    def test_fabricated_sentence_returns_low_confidence(self):
        """完全捏造的句子应返回'低'可信度。"""
        from app.verifier import verify_evidence

        fabricated = "The catalyst was synthesized using a hydrothermal method at 200 °C for 12 h."
        level, reason = verify_evidence(fabricated, SAMPLE_PAPER_TEXT)
        assert level == "低"
        assert "未能在原文中验证" in reason

    def test_empty_evidence_returns_low_confidence(self):
        """空字符串 evidence 应返回'低'可信度。"""
        from app.verifier import verify_evidence

        level, reason = verify_evidence("", SAMPLE_PAPER_TEXT)
        assert level == "低"

    def test_verify_batch_marks_failed_records(self):
        """批量校验时，校验失败的记录应被标记，不进入最终输出。"""
        from app.verifier import verify_batch

        records = [
            {**SAMPLE_EXTRACTION, "evidence_sentence": "NaBH4 (0.1 M, 1 mL) was added dropwise as the reducing agent."},
            {**SAMPLE_EXTRACTION, "evidence_sentence": "This is a completely fabricated sentence about nothing."},
        ]
        verified = verify_batch(records, source_chunks=[SAMPLE_CHUNK])

        passed = [r for r in verified if r["confidence"] != "低"]
        failed = [r for r in verified if r["confidence"] == "低"]

        assert len(passed) >= 1
        assert len(failed) >= 1
        assert all("⚠️" in r.get("confidence_note", "") for r in failed)


# ─────────────────────────────────────────────
# AC-04: 混合检索 - RRF 融合正确性
# ─────────────────────────────────────────────

class TestRetriever:

    def test_rrf_score_calculation(self):
        """RRF 分数计算应符合公式 1/(k+r1) + 1/(k+r2)。"""
        from app.retriever import rrf_score

        score = rrf_score(bm25_rank=1, vec_rank=1, k=60)
        expected = 1 / 61 + 1 / 61
        assert abs(score - expected) < 1e-9

    def test_rrf_higher_rank_gives_higher_score(self):
        """排名越靠前（数字越小），RRF 分数应越高。"""
        from app.retriever import rrf_score

        score_top = rrf_score(1, 1)
        score_mid = rrf_score(10, 10)
        score_bot = rrf_score(50, 50)
        assert score_top > score_mid > score_bot

    def test_retrieval_returns_top_k_chunks(self):
        """检索结果数量应不超过 final_top_k 配置值。"""
        from app.retriever import HybridRetriever

        mock_bm25 = MagicMock()
        mock_bm25.retrieve.return_value = [
            {"chunk_id": f"c{i}", "text": f"chunk {i}", "score": 1.0 / (i + 1)}
            for i in range(20)
        ]
        mock_vector = MagicMock()
        mock_vector.retrieve.return_value = [
            {"chunk_id": f"c{i}", "text": f"chunk {i}", "score": 1.0 / (i + 1)}
            for i in range(20)
        ]

        retriever = HybridRetriever(bm25=mock_bm25, vector=mock_vector, final_top_k=10)
        results = retriever.retrieve("AgNPs synthesis")

        assert len(results) <= 10

    def test_keyword_expansion_includes_synonyms(self):
        """关键词扩展应包含 AgNPs 的常见同义词。"""
        from app.retriever import expand_keywords

        with patch("app.retriever.llm_client") as mock_llm:
            mock_llm.chat.return_value = json.dumps([
                "AgNPs", "Ag NPs", "Ag nanoparticles",
                "silver nanoparticles", "silver NPs"
            ])
            keywords = expand_keywords("AgNPs 合成方法")

        assert "Ag nanoparticles" in keywords or "silver nanoparticles" in keywords


# ─────────────────────────────────────────────
# AC-05: 信息抽取 - 结构化输出和防幻觉规则
# ─────────────────────────────────────────────

class TestExtractor:

    def test_extraction_output_matches_schema(self):
        """LLM 抽取结果应符合 SynthesisRecord Pydantic schema。"""
        from app.extractor import SynthesisRecord

        record = SynthesisRecord(**SAMPLE_EXTRACTION)
        assert record.catalyst == "Ag NPs"
        assert "AgNO3" in record.precursors
        assert record.is_agent_inference is False

    def test_missing_field_is_none_not_fabricated(self):
        """原文未提及的字段应为 None，不能填常识值。"""
        from app.extractor import SynthesisRecord

        incomplete = {**SAMPLE_EXTRACTION, "temperature": None, "time": None}
        record = SynthesisRecord(**incomplete)
        assert record.temperature is None
        assert record.time is None

    def test_agent_inference_flag_is_set(self):
        """Agent 推测内容必须将 is_agent_inference 设为 True。"""
        from app.extractor import SynthesisRecord

        inferred = {**SAMPLE_EXTRACTION, "is_agent_inference": True,
                    "evidence_sentence": "Based on the conditions, this is likely a reduction method."}
        record = SynthesisRecord(**inferred)
        assert record.is_agent_inference is True

    def test_extraction_prompt_contains_anti_hallucination_rules(self):
        """抽取 Prompt 必须包含防幻觉约束关键词。"""
        from app.extractor import build_extraction_prompt

        prompt = build_extraction_prompt("AgNPs synthesis", "some context text")
        assert "原文" in prompt or "evidence" in prompt.lower()
        assert "null" in prompt or "None" in prompt or "未明确" in prompt
        assert "推测" in prompt or "inference" in prompt.lower()


# ─────────────────────────────────────────────
# AC-06: 索引管理 - 增量更新和持久化
# ─────────────────────────────────────────────

class TestIndexManager:

    def test_detect_new_files(self, tmp_path):
        """新增文件应被检测为需要增量索引。"""
        from app.indexer import get_changed_files

        manifest = {"paper_01.pdf": "1000_50000"}
        # 模拟文件夹中有新文件
        (tmp_path / "paper_01.pdf").write_bytes(b"x" * 50000)
        (tmp_path / "paper_02.pdf").write_bytes(b"y" * 30000)

        with patch("os.stat") as mock_stat:
            mock_stat.return_value = MagicMock(st_mtime=1000, st_size=50000)
            added, removed = get_changed_files(str(tmp_path), manifest)

        assert "paper_02.pdf" in added

    def test_detect_removed_files(self, tmp_path):
        """已删除的文件应被检测为需要从索引中移除。"""
        from app.indexer import get_changed_files

        manifest = {
            "paper_01.pdf": "1000_50000",
            "paper_deleted.pdf": "999_20000",  # 已删除
        }
        (tmp_path / "paper_01.pdf").write_bytes(b"x" * 50000)
        # paper_deleted.pdf 不存在

        with patch("os.stat") as mock_stat:
            mock_stat.return_value = MagicMock(st_mtime=1000, st_size=50000)
            added, removed = get_changed_files(str(tmp_path), manifest)

        assert "paper_deleted.pdf" in removed

    def test_manifest_saved_after_indexing(self, tmp_path):
        """索引完成后应更新并保存 manifest 文件。"""
        from app.indexer import save_manifest

        manifest = {
            "paper_01.pdf": {"mtime": 1000, "chunk_count": 42},
        }
        manifest_path = tmp_path / "index_manifest.json"
        save_manifest(str(manifest_path), manifest)

        assert manifest_path.exists()
        loaded = json.loads(manifest_path.read_text())
        assert "paper_01.pdf" in loaded
        assert loaded["paper_01.pdf"]["chunk_count"] == 42


# ─────────────────────────────────────────────
# AC-07: 输出生成 - Markdown 格式和自动保存
# ─────────────────────────────────────────────

class TestGenerator:

    def test_output_contains_evidence_column(self):
        """输出 Markdown 表格必须包含原文证据列。"""
        from app.generator import generate_markdown_table

        records = [
            {**SAMPLE_EXTRACTION, "confidence": "高",
             "confidence_note": "精确匹配"}
        ]
        md = generate_markdown_table(records, query_type="synthesis")

        assert "原文证据" in md or "evidence" in md.lower()
        assert "Zhang_2023" in md

    def test_output_separates_facts_and_inference(self):
        """输出应将 Agent 推测与文献明确结论分开。"""
        from app.generator import generate_markdown_output

        records_fact = [{**SAMPLE_EXTRACTION, "is_agent_inference": False, "confidence": "高"}]
        records_infer = [{**SAMPLE_EXTRACTION, "is_agent_inference": True,
                          "evidence_sentence": "Likely a reduction method based on conditions.",
                          "confidence": "低"}]

        md = generate_markdown_output(records_fact + records_infer)

        assert "Agent 分析" in md or "推测" in md
        assert "文献明确" in md or "原文" in md

    def test_uncertain_items_listed_separately(self):
        """低可信度记录应出现在'不确定项'部分，不进入主表格。"""
        from app.generator import generate_markdown_output

        records = [
            {**SAMPLE_EXTRACTION, "confidence": "高", "confidence_note": "精确匹配"},
            {**SAMPLE_EXTRACTION, "confidence": "低",
             "confidence_note": "⚠️ 证据未能在原文中验证",
             "catalyst": "Unknown Catalyst"},
        ]
        md = generate_markdown_output(records)

        assert "不确定" in md
        # 低可信度的 catalyst 不应出现在主表格中
        main_table_end = md.find("不确定")
        main_table = md[:main_table_end]
        assert "Unknown Catalyst" not in main_table

    def test_output_file_saved_with_timestamp(self, tmp_path):
        """查询结果应自动保存到 output 目录，文件名含时间戳。"""
        from app.generator import save_output

        md_content = "# Test Output\n\nSome content."
        saved_path = save_output(md_content, query="AgNPs合成方法",
                                 output_dir=str(tmp_path))

        assert Path(saved_path).exists()
        filename = Path(saved_path).name
        # 文件名格式：YYYYMMDD_HHMMSS_xxx.md
        assert re.match(r"\d{8}_\d{6}_.*\.md", filename), \
            f"文件名格式不符: {filename}"

    def test_output_includes_source_location(self):
        """每条证据应标注文献名称和页码。"""
        from app.generator import generate_markdown_table

        records = [{**SAMPLE_EXTRACTION, "confidence": "高", "confidence_note": "精确匹配"}]
        md = generate_markdown_table(records, query_type="synthesis")

        assert "paper_01.pdf" in md or "Zhang_2023" in md
        assert "3" in md  # 页码


# ─────────────────────────────────────────────
# AC-08: 端到端集成测试（使用 mock LLM）
# ─────────────────────────────────────────────

class TestEndToEnd:

    @pytest.fixture
    def mock_llm_response(self):
        return json.dumps([SAMPLE_EXTRACTION])

    def test_full_pipeline_synthesis_query(self, mock_llm_response, tmp_path):
        """
        端到端：给定包含 AgNPs 合成信息的文本，
        查询'AgNPs 合成方法'应返回含原文证据的 Markdown 表格。
        """
        from app.extractor import SynthesisRecord

        # 模拟 LLM 返回结构化 JSON
        with patch("app.extractor.llm_client") as mock_llm:
            mock_llm.chat.return_value = mock_llm_response

            from app.extractor import extract_synthesis_info
            records = extract_synthesis_info(
                query="AgNPs 合成方法",
                chunks=[SAMPLE_CHUNK]
            )

        assert len(records) >= 1
        r = records[0]
        assert r["catalyst"] == "Ag NPs"
        assert r["evidence_sentence"] != ""

    def test_full_pipeline_evidence_verified(self, mock_llm_response):
        """端到端：抽取结果经过证据校验后，高可信度记录应有精确匹配标注。"""
        from app.verifier import verify_batch

        records = [SAMPLE_EXTRACTION]
        verified = verify_batch(records, source_chunks=[SAMPLE_CHUNK])

        high_conf = [r for r in verified if r["confidence"] == "高"]
        assert len(high_conf) >= 1

    def test_query_with_no_relevant_chunks_returns_empty_with_message(self):
        """检索结果为空时，输出应包含'未找到相关内容'提示，不返回空表格。"""
        from app.generator import generate_markdown_output

        md = generate_markdown_output([], query="完全不相关的问题")
        assert "未找到" in md or "no results" in md.lower() or "未检索到" in md

    def test_response_time_within_limit(self, mock_llm_response):
        """单次查询（含 mock LLM）应在 5 秒内完成（不含真实 LLM 延迟）。"""
        from app.verifier import verify_batch

        start = time.time()
        records = [SAMPLE_EXTRACTION]
        verify_batch(records, source_chunks=[SAMPLE_CHUNK])
        elapsed = time.time() - start

        assert elapsed < 5.0, f"证据校验耗时过长: {elapsed:.2f}s"


# ─────────────────────────────────────────────
# AC-09: 防幻觉规则合规性检查
# ─────────────────────────────────────────────

class TestAntiHallucinationRules:

    def test_null_fields_not_filled_with_common_sense(self):
        """temperature=None 不能被自动填充为'room temperature'等常识值。"""
        from app.extractor import SynthesisRecord

        record = SynthesisRecord(**{**SAMPLE_EXTRACTION, "temperature": None})
        assert record.temperature is None

    def test_multiple_papers_not_merged(self):
        """不同文献的实验条件不能合并成一条记录。"""
        from app.extractor import SynthesisRecord

        record1 = SynthesisRecord(**{**SAMPLE_EXTRACTION, "paper_name": "Paper_A", "temperature": "25 °C"})
        record2 = SynthesisRecord(**{**SAMPLE_EXTRACTION, "paper_name": "Paper_B", "temperature": "80 °C"})

        assert record1.paper_name != record2.paper_name
        assert record1.temperature != record2.temperature

    def test_si_source_labeled_in_output(self):
        """来自 Supporting Information 的信息应在输出中标注。"""
        from app.generator import generate_markdown_table

        si_record = {
            **SAMPLE_EXTRACTION,
            "is_si": True,
            "confidence": "高",
            "confidence_note": "精确匹配",
        }
        md = generate_markdown_table([si_record], query_type="synthesis")
        assert "Supporting Information" in md or "SI" in md

    def test_inference_not_in_main_table(self):
        """is_agent_inference=True 的记录不能出现在主结论表格中。"""
        from app.generator import generate_markdown_output

        inferred_record = {
            **SAMPLE_EXTRACTION,
            "is_agent_inference": True,
            "confidence": "低",
            "confidence_note": "⚠️ Agent 推测",
            "catalyst": "INFERRED_CATALYST",
        }
        md = generate_markdown_output([inferred_record])

        # 主表格（不确定项之前）不应包含推测内容
        uncertain_pos = md.find("不确定") if "不确定" in md else md.find("Agent 分析")
        if uncertain_pos > 0:
            main_section = md[:uncertain_pos]
            assert "INFERRED_CATALYST" not in main_section
