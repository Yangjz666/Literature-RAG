from __future__ import annotations

from pathlib import Path
from typing import Any

from app.chunker import chunk_paper
from app.index_status import (
    STATUS_CHUNKED,
    STATUS_EMBEDDING,
    STATUS_INDEXED,
    STATUS_NOT_INDEXED,
    STATUS_PARSED,
    build_operation_summary,
    cleanup_document_status,
    get_document_status,
    load_index_status,
    mark_stage,
    record_failure,
    save_operation_summary,
    update_document_status,
)
from app.indexer import load_manifest, remove_manifest_entry, rebuild_full_index
from app.ingest import is_supporting_information, load_folder, parse_single_file
from app.parse_report import (
    diff_parse_reports,
    delete_parse_report,
    generate_document_id,
    get_file_fingerprint,
    list_parse_reports,
    load_parse_report,
    load_parse_report_detail,
    save_parse_report,
)


DEFAULT_PARSE_REPORT_DIR = "./data/parse_reports"
DEFAULT_INDEX_STATUS_PATH = "./data/index_status.json"
DEFAULT_INDEX_MANIFEST_PATH = "./data/index_manifest.json"


def _operation_id(operation_type: str, document_id: str | None = None) -> str:
    from datetime import datetime

    suffix = document_id or "all"
    return f"{operation_type}_{suffix}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


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


def get_document_detail(
    document_id: str,
    folder: str | Path,
    config: dict[str, Any] | None = None,
    index: Any | None = None,
    chunk_limit: int = 20,
) -> dict[str, Any]:
    config = config or {}
    rows = list_document_library(folder, config)
    item = next((row for row in rows if row.get("document_id") == document_id), None)
    report_dir = config.get("parse_report_dir", DEFAULT_PARSE_REPORT_DIR)
    status_path = config.get("index_status_path", DEFAULT_INDEX_STATUS_PATH)
    status_data = load_index_status(status_path)
    status_record = status_data.get("documents", {}).get(document_id)
    latest_operation = None
    if status_record and status_record.get("last_operation_id"):
        latest_operation = status_data.get("operations", {}).get(status_record["last_operation_id"])

    filename = item.get("filename") if item else None
    chunk_previews: list[dict[str, Any]] = []
    if index is not None and hasattr(index, "get_chunk_previews"):
        chunk_previews = index.get_chunk_previews(document_id, filename=filename, limit=chunk_limit)

    return {
        "document_id": document_id,
        "item": item,
        "parse_report": load_parse_report_detail(document_id, report_dir),
        "index_status": status_record,
        "latest_operation": latest_operation,
        "chunk_previews": chunk_previews,
        "errors": {
            "failure_stage": (status_record or {}).get("failure_stage"),
            "failure_reason": (status_record or {}).get("failure_reason"),
        },
    }


def _find_document_item(document_id: str, folder: str | Path, config: dict[str, Any]) -> dict[str, Any]:
    rows = list_document_library(folder, config)
    item = next((row for row in rows if row.get("document_id") == document_id), None)
    if item is None:
        raise ValueError(f"未找到文献记录: {document_id}")
    return item


def reparse_document(
    document_id: str,
    folder: str | Path,
    config: dict[str, Any] | None = None,
    progress_cb: Any | None = None,
) -> dict[str, Any]:
    config = config or {}
    item = _find_document_item(document_id, folder, config)
    report_dir = config.get("parse_report_dir", DEFAULT_PARSE_REPORT_DIR)
    status_path = config.get("index_status_path", DEFAULT_INDEX_STATUS_PATH)
    operation_id = _operation_id("reparse", document_id)
    old_report = load_parse_report(document_id, report_dir)
    old_status = get_document_status(document_id, status_path)

    try:
        if progress_cb:
            progress_cb("解析当前文献", 0.2)
        mark_stage(
            document_id,
            "parsing",
            filename=item.get("filename") or "",
            path=status_path,
            operation_id=operation_id,
            operation_type="reparse",
        )
        parsed = parse_single_file(
            item.get("filepath") or str(Path(folder) / item["filename"]),
            root_dir=str(folder) if folder else None,
            timeout_sec=config.get("performance", {}).get("pdf_parse_timeout_sec", 60),
            tesseract_cmd=config.get("ocr", {}).get("tesseract_cmd", ""),
            parse_report_dir=report_dir,
            write_report=False,
        )
        if parsed.get("error"):
            raise RuntimeError(parsed["error"])
        paper = parsed["paper"]
        paper["document_id"] = document_id
        chunks = chunk_paper(
            paper,
            child_max=config.get("chunking", {}).get("child_chunk_max_size", 300),
            parent_max=config.get("chunking", {}).get("parent_chunk_size", 800),
        )
        report = dict(parsed["report"])
        report["document_id"] = document_id
        report["chunks_created"] = len(chunks["children"])
        report["filename"] = item.get("filename") or report["filename"]
        save_parse_report(report, report_dir)
        mark_stage(
            document_id,
            STATUS_CHUNKED,
            filename=item.get("filename") or "",
            chunk_count=len(chunks["children"]),
            path=status_path,
            operation_id=operation_id,
            operation_type="reparse",
        )
        if progress_cb:
            progress_cb("重新解析完成", 1.0)
        summary = build_operation_summary(
            operation_id,
            "reparse",
            status="success",
            document_id=document_id,
            filename=item.get("filename"),
            current_stage=STATUS_CHUNKED,
            current_document_chunk_count=len(chunks["children"]),
            old_state=old_report,
            new_state=report,
            diff=diff_parse_reports(old_report, report),
        )
    except Exception as e:
        record_failure(
            document_id,
            "parsing",
            str(e),
            path=status_path,
            filename=item.get("filename") or "",
            operation_id=operation_id,
            operation_type="reparse",
        )
        summary = build_operation_summary(
            operation_id,
            "reparse",
            status="failed",
            document_id=document_id,
            filename=item.get("filename"),
            current_stage="parsing",
            old_state=old_report or old_status,
            error_messages=[str(e)],
        )
    save_operation_summary(summary, status_path)
    return summary


def rebuild_document_index(
    document_id: str,
    folder: str | Path,
    config: dict[str, Any],
    index: Any,
    progress_cb: Any | None = None,
) -> dict[str, Any]:
    item = _find_document_item(document_id, folder, config)
    status_path = config.get("index_status_path", DEFAULT_INDEX_STATUS_PATH)
    operation_id = _operation_id("rebuild_index", document_id)
    old_status = get_document_status(document_id, status_path)
    try:
        mark_stage(
            document_id,
            STATUS_EMBEDDING,
            filename=item.get("filename") or "",
            path=status_path,
            operation_id=operation_id,
            operation_type="rebuild_index",
        )
        parsed = parse_single_file(
            item.get("filepath") or str(Path(folder) / item["filename"]),
            root_dir=str(folder) if folder else None,
            timeout_sec=config.get("performance", {}).get("pdf_parse_timeout_sec", 60),
            tesseract_cmd=config.get("ocr", {}).get("tesseract_cmd", ""),
            parse_report_dir=config.get("parse_report_dir", DEFAULT_PARSE_REPORT_DIR),
            write_report=False,
        )
        if parsed.get("error"):
            raise RuntimeError(parsed["error"])
        paper = parsed["paper"]
        paper["document_id"] = document_id
        result = index.rebuild_document_index(paper, str(folder), config, progress_cb=progress_cb)
        new_status = mark_stage(
            document_id,
            STATUS_INDEXED,
            filename=item.get("filename") or "",
            chunk_count=int(result.get("chunk_count") or 0),
            path=status_path,
            operation_id=operation_id,
            operation_type="rebuild_index",
        )
        summary = build_operation_summary(
            operation_id,
            "rebuild_index",
            status="success",
            document_id=document_id,
            filename=item.get("filename"),
            current_stage=STATUS_INDEXED,
            current_document_chunk_count=int(result.get("chunk_count") or 0),
            old_state=old_status,
            new_state=new_status,
        )
    except Exception as e:
        if old_status and old_status.get("status") == STATUS_INDEXED:
            update_document_status(
                document_id,
                {
                    **old_status,
                    "failure_stage": "embedding",
                    "failure_reason": str(e),
                    "last_operation_id": operation_id,
                    "last_operation_type": "rebuild_index",
                },
                path=status_path,
            )
        else:
            record_failure(
                document_id,
                "embedding",
                str(e),
                path=status_path,
                filename=item.get("filename") or "",
                operation_id=operation_id,
                operation_type="rebuild_index",
            )
        summary = build_operation_summary(
            operation_id,
            "rebuild_index",
            status="failed",
            document_id=document_id,
            filename=item.get("filename"),
            current_stage="embedding",
            old_state=old_status,
            error_messages=[str(e)],
        )
    save_operation_summary(summary, status_path)
    return summary


def rebuild_all_indexes(
    folder: str | Path,
    config: dict[str, Any],
    index: Any,
    progress_cb: Any | None = None,
) -> dict[str, Any]:
    operation_id = _operation_id("full_rebuild")
    status_path = config.get("index_status_path", DEFAULT_INDEX_STATUS_PATH)
    papers = load_folder(
        str(folder),
        timeout_sec=config.get("performance", {}).get("pdf_parse_timeout_sec", 60),
        tesseract_cmd=config.get("ocr", {}).get("tesseract_cmd", ""),
    )
    result = rebuild_full_index(index, papers, str(folder), config, progress_cb=progress_cb)
    summary = build_operation_summary(
        operation_id,
        "full_rebuild",
        status=result["status"],
        completed_document_count=result["completed_document_count"],
        failed_document_count=result["failed_document_count"],
        error_messages=result["error_messages"],
    )
    save_operation_summary(summary, status_path)
    return summary


def delete_document_records(
    document_id: str,
    folder: str | Path,
    config: dict[str, Any] | None = None,
    index: Any | None = None,
) -> dict[str, Any]:
    config = config or {}
    item = _find_document_item(document_id, folder, config)
    operation_id = _operation_id("delete", document_id)
    status_path = config.get("index_status_path", DEFAULT_INDEX_STATUS_PATH)
    results: dict[str, dict[str, Any]] = {}

    for key, func in (
        (
            "manifest",
            lambda: remove_manifest_entry(
                config.get("index_manifest_path", DEFAULT_INDEX_MANIFEST_PATH),
                document_id,
                item.get("filename"),
            ),
        ),
        ("parse_report", lambda: delete_parse_report(document_id, config.get("parse_report_dir", DEFAULT_PARSE_REPORT_DIR))),
    ):
        try:
            results[key] = func()
        except Exception as e:
            results[key] = {"target": key, "status": "failed", "reason": str(e)}

    if index is not None and hasattr(index, "remove_document_records"):
        index_results = index.remove_document_records(document_id, item.get("filename"))
        results.update(index_results)
    else:
        results["vector_index"] = {"target": "vector_index", "status": "skipped", "reason": "未提供索引对象"}
        results["keyword_index"] = {"target": "keyword_index", "status": "skipped", "reason": "未提供索引对象"}
        results["parent_store"] = {"target": "parent_store", "status": "skipped", "reason": "未提供索引对象"}

    try:
        results["index_status"] = cleanup_document_status(document_id, status_path)
    except Exception as e:
        results["index_status"] = {"target": "index_status", "status": "failed", "reason": str(e)}

    failed_count = sum(1 for result in results.values() if result.get("status") == "failed")
    summary = build_operation_summary(
        operation_id,
        "delete",
        status="success" if failed_count == 0 else "partial",
        document_id=document_id,
        filename=item.get("filename"),
        results=results,
        failed_document_count=1 if failed_count else 0,
        error_messages=[f"{key}: {value.get('reason')}" for key, value in results.items() if value.get("status") == "failed"],
    )
    save_operation_summary(summary, status_path)
    summary["pdf_deleted"] = False
    return summary
