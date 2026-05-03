import difflib
import re
import unicodedata


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"-\s*\n\s*", "", text)       # 断词连字符
    text = re.sub(r"\s+", " ", text)
    text = text.replace("℃", "°C")
    return text.strip()


def _soft_normalize(text: str) -> str:
    """用于模糊匹配的更宽松规范化，吸收 LLM 常见轻微改写。"""
    text = normalize_text(text).lower()
    text = re.sub(r"\b(the|a|an)\b", " ", text)
    text = re.sub(r"(?<=\d)\s+(?=[a-z%])", "", text)
    text = re.sub(r"(?<=[a-z])\s+(?=\d)", "", text)
    text = re.sub(r"[^a-z0-9.%°+-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def make_sentence_windows(text: str, window_size: int = 2) -> list[str]:
    """将文本按句子切分，返回 1 到 window_size 句的滑动窗口。"""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s for s in sentences if s.strip()]
    windows = []
    for i in range(len(sentences)):
        for size in range(1, window_size + 1):
            window = " ".join(sentences[i: i + size])
            if window:
                windows.append(window)
    return windows if windows else [text]


def verify_evidence(
    evidence: str,
    source_text: str,
    threshold: float = 0.85,
) -> tuple[str, str]:
    """
    返回 (confidence_level, reason)。
    confidence_level: "高" | "中" | "低"
    """
    evidence_n = normalize_text(evidence)
    source_n = normalize_text(source_text)

    if not evidence_n:
        return "低", "证据为空"
    if evidence_n in source_n:
        return "高", "精确匹配"

    evidence_soft = _soft_normalize(evidence_n)
    windows = make_sentence_windows(source_n, window_size=2)
    best = max(
        (
            max(
                difflib.SequenceMatcher(None, evidence_n, w).ratio(),
                difflib.SequenceMatcher(None, evidence_soft, _soft_normalize(w)).ratio(),
            )
            for w in windows
        ),
        default=0.0,
    )
    if best >= threshold:
        return "中", f"模糊匹配 {best:.2f}"
    return "低", "证据未能在原文中验证"


def verify_batch(
    records: list[dict],
    source_chunks: list[dict],
    threshold: float = 0.85,
) -> list[dict]:
    """
    批量校验 records 中的 evidence_sentence。
    每条记录追加 confidence 和 confidence_note 字段。
    校验失败的记录标记 ⚠️，不从列表中删除（由 generator 决定是否进入主表格）。
    """
    # 构建 filename -> 全文 的映射，用于回查
    source_map: dict[str, str] = {}
    for chunk in source_chunks:
        meta = chunk.get("metadata", chunk)
        fname = meta.get("filename", "")
        text = chunk.get("text", "")
        source_map[fname] = source_map.get(fname, "") + " " + text

    result = []
    for rec in records:
        evidence = rec.get("evidence_sentence", "")
        filename = rec.get("filename", "")

        # 优先用对应文献的文本，找不到则合并所有文本
        source_text = source_map.get(filename, " ".join(source_map.values()))

        level, reason = verify_evidence(evidence, source_text, threshold)
        annotated = dict(rec)
        annotated["confidence"] = level
        if level == "低":
            annotated["confidence_note"] = f"⚠️ {reason}"
        else:
            annotated["confidence_note"] = reason
        result.append(annotated)

    return result
