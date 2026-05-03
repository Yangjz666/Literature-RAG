import hashlib
import logging
import os
import re
import signal
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

SI_KEYWORDS = ("si", "supporting", "supplementary", "esi")
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+", re.IGNORECASE)


def is_supporting_information(filename: str) -> bool:
    stem = Path(filename).stem.lower()
    return any(kw in stem for kw in SI_KEYWORDS)


def extract_doi_from_text(text: str) -> str | None:
    m = DOI_PATTERN.search(text or "")
    return m.group(0).rstrip(".,;)") if m else None


def ocr_page(page, tesseract_cmd: str = "") -> str:
    try:
        import pytesseract
        from PIL import Image

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        pix = page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return pytesseract.image_to_string(img)
    except Exception as e:
        logger.warning(f"OCR 失败: {e}")
        return ""


def extract_metadata(doc) -> dict:
    meta = doc.metadata or {}
    title = meta.get("title", "").strip()
    author = meta.get("author", "").strip()
    # 尝试从前两页文本提取 DOI
    doi = None
    for i in range(min(2, len(doc))):
        doi = extract_doi_from_text(doc[i].get_text())
        if doi:
            break
    return {"title": title, "author": author, "doi": doi}


def extract_text(pdf_path: str, timeout_sec: int = 60, tesseract_cmd: str = "") -> dict:
    """解析单个 PDF，返回 {meta, pages, error}。"""
    result = {"meta": {}, "pages": [], "error": None}
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        result["error"] = f"无法打开文件: {e}"
        return result

    if getattr(doc, "is_encrypted", False) is True:
        result["error"] = "加密 PDF，请手动解密后重试"
        return result

    result["meta"] = extract_metadata(doc)
    pages = []
    for page in doc:
        text = page.get_text()
        used_ocr = False
        if not text.strip():
            text = ocr_page(page, tesseract_cmd)
            used_ocr = True
        pages.append({"page": page.number + 1, "text": text, "used_ocr": used_ocr})
    result["pages"] = pages
    return result


def _content_hash(pdf_path: str) -> str:
    try:
        with open(pdf_path, "rb") as f:
            head = f.read(500)
        return hashlib.md5(head).hexdigest()
    except Exception:
        return ""


def deduplicate_papers(papers: list[dict]) -> list[dict]:
    """按 DOI 或内容哈希去重，保留文件名字典序靠前的版本。"""
    seen_doi: dict[str, dict] = {}
    seen_hash: dict[str, dict] = {}
    result = []

    for p in sorted(papers, key=lambda x: x.get("filename", "")):
        doi = p.get("doi")
        ch = p.get("content_hash", "")

        if doi:
            if doi in seen_doi:
                logger.info(f"去重跳过 {p['filename']}（与 {seen_doi[doi]['filename']} DOI 相同）")
                continue
            seen_doi[doi] = p
        elif ch:
            if ch in seen_hash:
                logger.info(f"去重跳过 {p['filename']}（内容哈希重复）")
                continue
            seen_hash[ch] = p

        result.append(p)
    return result


def load_folder(folder: str, timeout_sec: int = 60, tesseract_cmd: str = "") -> list[dict]:
    """读取文件夹中所有 PDF，返回文献列表（含文本和元数据）。"""
    folder_path = Path(folder)
    pdf_files = sorted(folder_path.rglob("*.pdf"))

    raw = []
    for pdf_path in pdf_files:
        filename = pdf_path.name
        is_si = is_supporting_information(filename)
        logger.info(f"解析: {filename} (SI={is_si})")

        parsed = extract_text(str(pdf_path), timeout_sec, tesseract_cmd)
        if parsed["error"]:
            logger.warning(f"跳过 {filename}: {parsed['error']}")
            continue

        doi = parsed["meta"].get("doi")
        ch = _content_hash(str(pdf_path))

        # 推断 paper_name：优先标题，其次 author_year，最后文件名
        title = parsed["meta"].get("title", "")
        author = parsed["meta"].get("author", "")
        if title:
            paper_name = title[:80]
        elif author:
            paper_name = author.split(",")[0].split(";")[0].strip()
        else:
            paper_name = pdf_path.stem

        raw.append({
            "filename": filename,
            "filepath": str(pdf_path),
            "paper_name": paper_name,
            "doi": doi,
            "content_hash": ch,
            "is_si": is_si,
            "pages": parsed["pages"],
            "meta": parsed["meta"],
        })

    return deduplicate_papers(raw)
