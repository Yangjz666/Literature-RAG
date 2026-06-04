from app.query_router import QueryMode, detect_query_mode


def test_explicit_structured_extraction_mode_wins():
    assert detect_query_mode("总结这些文献", explicit_mode="structured_extraction") == QueryMode.STRUCTURED_EXTRACTION


def test_explicit_synthesis_mode_wins():
    assert detect_query_mode("提取表格", explicit_mode="synthesis") == QueryMode.SYNTHESIS


def test_explicit_deep_reading_mode_wins():
    assert detect_query_mode("提取表格", explicit_mode="deep_reading") == QueryMode.DEEP_READING


def test_chinese_synthesis_keywords_route_to_synthesis():
    for query in ["总结这些论文", "对比 Ag 和 Cu", "综合说明机制", "有什么启发"]:
        assert detect_query_mode(query) == QueryMode.SYNTHESIS


def test_chinese_structured_keywords_route_to_structured_extraction():
    for query in ["提取合成方法", "测试条件是什么", "FE 和电解液", "生成表格"]:
        assert detect_query_mode(query) == QueryMode.STRUCTURED_EXTRACTION


def test_chinese_deep_reading_keywords_route_to_deep_reading():
    for query in ["精读这篇论文", "小白解释这篇", "解释这篇文章", "单篇逐段分析"]:
        assert detect_query_mode(query) == QueryMode.DEEP_READING


def test_english_keywords_route_to_expected_modes():
    assert detect_query_mode("extract a table of synthesis condition") == QueryMode.STRUCTURED_EXTRACTION
    assert detect_query_mode("summarize and compare the mechanism insight") == QueryMode.SYNTHESIS
    assert detect_query_mode("deep reading explain this paper for a beginner") == QueryMode.DEEP_READING


def test_empty_or_unknown_query_uses_config_default_or_conservative_default():
    assert detect_query_mode("") == QueryMode.STRUCTURED_EXTRACTION
    assert detect_query_mode("???", config={"v2": {"default_mode": "synthesis"}}) == QueryMode.SYNTHESIS
