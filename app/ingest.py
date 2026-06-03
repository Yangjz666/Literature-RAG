import hashlib
import logging
import os
import re
import signal
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF

from app.parse_report import (
    PARSE_STATUS_FAILED,
    PARSE_STATUS_PARTIAL,
    PARSE_STATUS_SUCCESS,
    build_parse_report,
    generate_document_id,
    save_parse_report,
)

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


def _paper_name_from_metadata(pdf_path: Path, metadata: dict) -> str:
    title = metadata.get("title", "")
    author = metadata.get("author", "")
    if title:
        return title[:80]
    if author:
        return author.split(",")[0].split(";")[0].strip()
    return pdf_path.stem


def _parse_status_for_pages(parsed: dict) -> str:
    if parsed.get("error"):
        return PARSE_STATUS_FAILED
    pages = parsed.get("pages") or []
    if not pages:
        return PARSE_STATUS_FAILED
    parsed_pages = [page for page in pages if str(page.get("text") or "").strip()]
    if len(parsed_pages) == len(pages):
        return PARSE_STATUS_SUCCESS
    return PARSE_STATUS_PARTIAL


def _build_report_from_parse(
    pdf_path: Path,
    document_id: str,
    parsed: dict,
    warnings: list[str],
) -> dict:
    pages = parsed.get("pages") or []
    parsed_pages = [page for page in pages if str(page.get("text") or "").strip()]
    metadata = parsed.get("meta") or {}
    status = _parse_status_for_pages(parsed)
    error_message = parsed.get("error")
    if status == PARSE_STATUS_FAILED and not error_message:
        error_message = "未解析到可用文本"
    return build_parse_report(
        document_id=document_id,
        filename=pdf_path.name,
        filepath=str(pdf_path),
        paper_title=metadata.get("title") or "",
        doi=metadata.get("doi"),
        is_si=is_supporting_information(pdf_path.name),
        metadata_source={"pdf_metadata": True, "doi_regex": bool(metadata.get("doi"))},
        parse_status=status,
        pages_total=len(pages),
        pages_parsed=len(parsed_pages),
        text_length=sum(len(str(page.get("text") or "")) for page in pages),
        ocr_used=any(bool(page.get("used_ocr")) for page in pages),
        error_message=error_message,
        warnings=warnings,
    )


def parse_single_pdf(
    pdf_path: str | Path,
    root_dir: str | Path | None = None,
    timeout_sec: int = 60,
    tesseract_cmd: str = "",
    report_dir: str | Path | None = None,
    write_report: bool = False,
) -> dict:
    """Parse exactly one PDF and optionally persist its parse_report."""
    path = Path(pdf_path)
    document_id = generate_document_id(path, root_dir)
    warnings: list[str] = []
    parsed = extract_text(str(path), timeout_sec=timeout_sec, tesseract_cmd=tesseract_cmd)
    if parsed.get("error"):
        warnings.append(str(parsed["error"]))

    report = _build_report_from_parse(path, document_id, parsed, warnings)
    metadata = parsed.get("meta") or {}
    result = {
        "document_id": document_id,
        "filename": path.name,
        "filepath": str(path),
        "pages": parsed.get("pages") or [],
        "metadata": metadata,
        "warnings": warnings,
        "error": parsed.get("error"),
        "report": report,
        "paper": None,
    }
    if report["parse_status"] != PARSE_STATUS_FAILED:
        result["paper"] = {
            "document_id": document_id,
            "filename": path.name,
            "filepath": str(path),
            "paper_name": _paper_name_from_metadata(path, metadata),
            "doi": metadata.get("doi"),
            "content_hash": _content_hash(str(path)),
            "is_si": is_supporting_information(path.name),
            "pages": result["pages"],
            "meta": metadata,
        }
    if write_report:
        save_parse_report(report, report_dir or "./data/parse_reports")
    return result


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

        raw.append({
            "filename": filename,
            "filepath": str(pdf_path),
            "paper_name": _paper_name_from_metadata(pdf_path, parsed["meta"]),
            "doi": doi,
            "content_hash": ch,
            "is_si": is_si,
            "pages": parsed["pages"],
            "meta": parsed["meta"],
        })

    return deduplicate_papers(raw)
