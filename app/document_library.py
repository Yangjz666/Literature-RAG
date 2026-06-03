from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from app.index_status import (
    STATUS_FAILED,
    STATUS_PARSED,
    STATUS_PARSING,
    STATUS_NOT_INDEXED,
    build_operation_summary,
    load_index_status,
    record_failure,
    record_reparse_stage,
    save_operation_summary,
)
from app.indexer import load_manifest
from app.ingest import is_supporting_information, parse_single_pdf
from app.parse_report import (
    diff_parse_reports,
    generate_document_id,
    get_file_fingerprint,
    list_parse_reports,
    load_parse_report,
    save_parse_report,
)


DEFAULT_PARSE_REPORT_DIR = "./data/parse_reports"
DEFAULT_INDEX_STATUS_PATH = "./data/index_status.json"
DEFAULT_INDEX_MANIFEST_PATH = "./data/index_manifest.json"


def _safe_manifest(path: str | Path) -> dict[str, Any]:
    try:
        manifest = load_manifest(str(path))
    except (OSError, ValueError):
        return {"last_updated": "", "files": {}}
    if "files" not in manifest:
        manifest = {"last_updated": manifest.get("last_updated", ""), "files": manifest}
    return manifest


def _manifest_entry(filename: str, raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        entry = dict(raw)
    else:
        entry = {"fingerprint": raw}
    entry.setdefault("filename", filename)
    entry.setdefault("chunk_count", 0)
    entry.setdefault("status", None)
    entry.setdefault("error", None)
    return entry


def _status_by_filename(status_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for record in status_data.get("documents", {}).values():
        filename = record.get("filename")
        if filename:
            result[str(filename)] = record
    return result


def _reports_by_filename(reports: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for report in reports.values():
        filename = report.get("filename")
        if filename:
            result[str(filename)] = report
    return result


def _base_item_from_file(pdf_path: Path, folder_path: Path) -> dict[str, Any]:
    document_id = generate_document_id(pdf_path, folder_path)
    filename = pdf_path.name
    return {
        "document_id": document_id,
        "filename": filename,
        "filepath": str(pdf_path),
        "file_fingerprint": get_file_fingerprint(pdf_path),
        "title": pdf_path.stem,
        "doi": None,
        "year": None,
        "journal": None,
        "is_si": is_supporting_information(filename),
        "main_document_id": None,
        "parse_status": "unknown",
        "index_status": STATUS_NOT_INDEXED,
        "chunk_count": 0,
        "error_summary": None,
        "last_updated": None,
    }


def _base_item_from_manifest(filename: str, entry: dict[str, Any]) -> dict[str, Any]:
    filepath = str(entry.get("filepath") or "")
    document_id = str(entry.get("document_id") or generate_document_id(filepath or filename))
    return {
        "document_id": document_id,
        "filename": filename,
        "filepath": filepath,
        "file_fingerprint": str(entry.get("fingerprint") or ""),
        "title": Path(filename).stem,
        "doi": entry.get("doi"),
        "year": entry.get("year"),
        "journal": entry.get("journal"),
        "is_si": bool(entry.get("is_si", is_supporting_information(filename))),
        "main_document_id": entry.get("main_document_id"),
        "parse_status": "unknown",
        "index_status": entry.get("status") or STATUS_NOT_INDEXED,
        "chunk_count": int(entry.get("chunk_count") or 0),
        "error_summary": entry.get("error"),
        "last_updated": entry.get("updated_at"),
    }


def _merge_report(item: dict[str, Any], report: dict[str, Any] | None) -> None:
    if not report:
        return
    item["document_id"] = str(report.get("document_id") or item["document_id"])
    item["filename"] = str(report.get("filename") or item["filename"])
    item["filepath"] = str(report.get("filepath") or item["filepath"])
    item["file_fingerprint"] = str(report.get("file_fingerprint") or item["file_fingerprint"])
    item["title"] = report.get("paper_title") or item["title"]
    item["doi"] = report.get("doi") or item["doi"]
    item["year"] = report.get("year") or item["year"]
    item["journal"] = report.get("journal") or item["journal"]
    item["is_si"] = bool(report.get("is_si", item["is_si"]))
    item["main_document_id"] = report.get("main_document_id") or item["main_document_id"]
    item["parse_status"] = report.get("parse_status") or item["parse_status"]
    item["chunk_count"] = int(report.get("chunks_created") or item["chunk_count"] or 0)
    item["error_summary"] = report.get("error_message") or item["error_summary"]
    item["last_updated"] = report.get("updated_at") or item["last_updated"]


def _merge_status(item: dict[str, Any], status: dict[str, Any] | None) -> None:
    if not status:
        return
    item["index_status"] = status.get("status") or item["index_status"]
    item["chunk_count"] = int(status.get("chunk_count") or item["chunk_count"] or 0)
    item["error_summary"] = status.get("failure_reason") or item["error_summary"]
    item["last_updated"] = status.get("updated_at") or item["last_updated"]


def list_document_library(folder: str | Path, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    config = config or {}
    folder_text = str(folder).strip()
    folder_path = Path(folder_text).expanduser() if folder_text else None
    manifest_path = config.get("index_manifest_path", DEFAULT_INDEX_MANIFEST_PATH)
    report_dir = config.get("parse_report_dir", DEFAULT_PARSE_REPORT_DIR)
    status_path = config.get("index_status_path", DEFAULT_INDEX_STATUS_PATH)

    manifest = _safe_manifest(manifest_path)
    manifest_entries = {
        filename: _manifest_entry(filename, raw)
        for filename, raw in (manifest.get("files") or {}).items()
    }
    reports = list_parse_reports(report_dir)
    status_data = load_index_status(status_path)
    reports_by_filename = _reports_by_filename(reports)
    status_by_filename = _status_by_filename(status_data)

    items: dict[str, dict[str, Any]] = {}
    if folder_path is not None and folder_path.exists() and folder_path.is_dir():
        for pdf_path in sorted(folder_path.rglob("*.pdf")):
            item = _base_item_from_file(pdf_path, folder_path)
            filename = item["filename"]
            entry = manifest_entries.get(filename)
            if entry:
                item["document_id"] = str(entry.get("document_id") or item["document_id"])
                item["chunk_count"] = int(entry.get("chunk_count") or item["chunk_count"] or 0)
                item["index_status"] = entry.get("status") or item["index_status"]
                item["error_summary"] = entry.get("error") or item["error_summary"]
                item["last_updated"] = entry.get("updated_at") or item["last_updated"]
            _merge_report(item, reports.get(item["document_id"]) or reports_by_filename.get(filename))
            _merge_status(item, status_data["documents"].get(item["document_id"]) or status_by_filename.get(filename))
            items[item["document_id"]] = item

    for filename, entry in manifest_entries.items():
        document_id = str(entry.get("document_id") or generate_document_id(entry.get("filepath") or filename))
        known_filenames = {item.get("filename") for item in items.values()}
        if document_id in items or filename in known_filenames:
            continue
        item = _base_item_from_manifest(filename, entry)
        _merge_report(item, reports.get(item["document_id"]) or reports_by_filename.get(filename))
        _merge_status(item, status_data["documents"].get(item["document_id"]) or status_by_filename.get(filename))
        items[item["document_id"]] = item

    for document_id, report in reports.items():
        known_filenames = {item.get("filename") for item in items.values()}
        if document_id in items or report.get("filename") in known_filenames:
            continue
        item = _base_item_from_manifest(str(report.get("filename") or document_id), {})
        _merge_report(item, report)
        _merge_status(item, status_data["documents"].get(document_id))
        items[document_id] = item

    return sorted(items.values(), key=lambda item: item.get("filename", ""))


def _resolve_document(
    document_id: str | None = None,
    document: dict[str, Any] | None = None,
    folder: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if document:
        return dict(document)
    if not document_id:
        raise ValueError("reparse_document 需要 document_id 或 document")
    rows = list_document_library(folder or "", config)
    for row in rows:
        if row.get("document_id") == document_id:
            return dict(row)
    raise ValueError(f"未找到文献: {document_id}")


def reparse_document(
    document_id: str | None = None,
    document: dict[str, Any] | None = None,
    folder: str | Path | None = None,
    config: dict[str, Any] | None = None,
    parse_func: Any | None = None,
) -> dict[str, Any]:
    config = config or {}
    doc = _resolve_document(document_id=document_id, document=document, folder=folder, config=config)
    resolved_document_id = str(doc.get("document_id") or document_id or "")
    filename = str(doc.get("filename") or "")
    filepath = str(doc.get("filepath") or "")
    if not resolved_document_id or not filepath:
        raise ValueError("单篇重新解析需要 document_id 和 filepath")

    report_dir = config.get("parse_report_dir", DEFAULT_PARSE_REPORT_DIR)
    status_path = config.get("index_status_path", DEFAULT_INDEX_STATUS_PATH)
    timeout_sec = config.get("performance", {}).get("pdf_parse_timeout_sec", 60)
    tesseract_cmd = config.get("ocr", {}).get("tesseract_cmd", "")
    operation_id = f"reparse_{uuid4().hex[:12]}"
    old_report = load_parse_report(resolved_document_id, report_dir)

    record_reparse_stage(
        resolved_document_id,
        STATUS_PARSING,
        path=status_path,
        filename=filename,
        operation_id=operation_id,
    )
    parser = parse_func or parse_single_pdf
    try:
        parsed = parser(
            filepath,
            root_dir=folder,
            timeout_sec=timeout_sec,
            tesseract_cmd=tesseract_cmd,
            report_dir=report_dir,
            write_report=False,
        )
        new_report = parsed["report"]
        new_report["document_id"] = resolved_document_id
        new_report["filename"] = filename or new_report.get("filename")
    except Exception as exc:
        new_report = None
        failure_reason = str(exc)
        record_failure(
            resolved_document_id,
            "parsing",
            failure_reason,
            path=status_path,
            operation_id=operation_id,
            operation_type="reparse",
        )
        summary = build_operation_summary(
            operation_id,
            "reparse",
            status="failed",
            document_id=resolved_document_id,
            filename=filename,
            current_stage=STATUS_FAILED,
            failure_stage="parsing",
            failure_reason=failure_reason,
            old_state=old_report,
            new_state=None,
            diff=diff_parse_reports(old_report, None),
            error_messages=[failure_reason],
        )
        return save_operation_summary(summary, status_path)

    if new_report.get("parse_status") == "failed":
        failure_reason = str(new_report.get("error_message") or "; ".join(new_report.get("warnings") or []))
        record_failure(
            resolved_document_id,
            "parsing",
            failure_reason,
            path=status_path,
            operation_id=operation_id,
            operation_type="reparse",
        )
        summary = build_operation_summary(
            operation_id,
            "reparse",
            status="failed",
            document_id=resolved_document_id,
            filename=filename,
            current_stage=STATUS_FAILED,
            failure_stage="parsing",
            failure_reason=failure_reason,
            old_state=old_report,
            new_state=new_report,
            diff=diff_parse_reports(old_report, new_report),
            error_messages=[failure_reason],
        )
        return save_operation_summary(summary, status_path)

    save_parse_report(new_report, report_dir)
    record_reparse_stage(
        resolved_document_id,
        STATUS_PARSED,
        path=status_path,
        filename=filename,
        operation_id=operation_id,
    )
    summary = build_operation_summary(
        operation_id,
        "reparse",
        status="success",
        document_id=resolved_document_id,
        filename=filename,
        current_stage=STATUS_PARSED,
        old_state=old_report,
        new_state=new_report,
        diff=diff_parse_reports(old_report, new_report),
    )
    return save_operation_summary(summary, status_path)
