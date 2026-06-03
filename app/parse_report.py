from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


PARSE_STATUS_SUCCESS = "success"
PARSE_STATUS_PARTIAL = "partial"
PARSE_STATUS_FAILED = "failed"
VALID_PARSE_STATUSES = {
    PARSE_STATUS_SUCCESS,
    PARSE_STATUS_PARTIAL,
    PARSE_STATUS_FAILED,
}

DEFAULT_PARSE_REPORT_DIR = "./data/parse_reports"
REQUIRED_PARSE_REPORT_FIELDS = {
    "document_id",
    "filename",
    "parse_status",
    "created_at",
    "updated_at",
}


def now_iso() -> str:
    return datetime.now().isoformat()


def get_file_fingerprint(filepath: str | Path) -> str:
    try:
        stat = Path(filepath).stat()
    except OSError:
        return ""
    return f"{stat.st_mtime}_{stat.st_size}"


def generate_document_id(filepath: str | Path, root_dir: str | Path | None = None) -> str:
    path = Path(filepath)
    try:
        if root_dir is not None:
            identity = path.resolve().relative_to(Path(root_dir).resolve()).as_posix()
        else:
            identity = path.resolve().as_posix()
    except (OSError, ValueError):
        identity = path.as_posix()
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]
    return f"doc_{digest}"


def default_parse_report(
    document_id: str,
    filename: str,
    filepath: str = "",
    parse_status: str = PARSE_STATUS_FAILED,
) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "document_id": document_id,
        "filename": filename,
        "filepath": filepath,
        "file_fingerprint": get_file_fingerprint(filepath) if filepath else "",
        "paper_title": "",
        "doi": None,
        "year": None,
        "journal": None,
        "is_si": False,
        "main_document_id": None,
        "metadata_source": {},
        "parse_status": parse_status,
        "pages_total": 0,
        "pages_parsed": 0,
        "text_length": 0,
        "chunks_created": 0,
        "tables_found": 0,
        "figure_captions_found": 0,
        "ocr_used": False,
        "error_message": None,
        "warnings": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def build_parse_report(**fields: Any) -> dict[str, Any]:
    document_id = str(fields.get("document_id") or "")
    filename = str(fields.get("filename") or "")
    filepath = str(fields.get("filepath") or "")
    report = default_parse_report(
        document_id=document_id,
        filename=filename,
        filepath=filepath,
        parse_status=str(fields.get("parse_status") or PARSE_STATUS_FAILED),
    )
    created_at = fields.get("created_at") or report["created_at"]
    report.update(fields)
    report["created_at"] = created_at
    report["updated_at"] = fields.get("updated_at") or now_iso()
    validate_parse_report(report)
    return report


def validate_parse_report(report: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_PARSE_REPORT_FIELDS if not report.get(field)]
    if missing:
        raise ValueError(f"parse_report 缺少必填字段: {', '.join(sorted(missing))}")

    status = report.get("parse_status")
    if status not in VALID_PARSE_STATUSES:
        raise ValueError(f"parse_status 不合法: {status!r}")

    pages_total = int(report.get("pages_total") or 0)
    pages_parsed = int(report.get("pages_parsed") or 0)
    if pages_parsed > pages_total:
        raise ValueError("pages_parsed 不能大于 pages_total")

    if status == PARSE_STATUS_FAILED and not report.get("error_message") and not report.get("warnings"):
        raise ValueError("failed parse_report 必须包含 error_message 或 warnings")


def _report_path(report_dir: str | Path, document_id: str) -> Path:
    return Path(report_dir) / f"{document_id}.json"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def save_parse_report(report: dict[str, Any], report_dir: str | Path = DEFAULT_PARSE_REPORT_DIR) -> Path:
    validate_parse_report(report)
    path = _report_path(report_dir, str(report["document_id"]))
    _atomic_write_json(path, report)
    return path


def load_parse_report(document_id: str, report_dir: str | Path = DEFAULT_PARSE_REPORT_DIR) -> dict[str, Any] | None:
    path = _report_path(report_dir, document_id)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    validate_parse_report(report)
    return report


def load_parse_report_detail(
    document_id: str,
    report_dir: str | Path = DEFAULT_PARSE_REPORT_DIR,
) -> dict[str, Any]:
    report = load_parse_report(document_id, report_dir)
    if report is None:
        return {
            "document_id": document_id,
            "exists": False,
            "summary": {},
            "raw": None,
            "error_message": "未找到 parse_report",
        }
    return {
        "document_id": document_id,
        "exists": True,
        "summary": {
            "filename": report.get("filename"),
            "paper_title": report.get("paper_title"),
            "doi": report.get("doi"),
            "parse_status": report.get("parse_status"),
            "pages_total": report.get("pages_total"),
            "pages_parsed": report.get("pages_parsed"),
            "text_length": report.get("text_length"),
            "chunks_created": report.get("chunks_created"),
            "tables_found": report.get("tables_found"),
            "figure_captions_found": report.get("figure_captions_found"),
            "ocr_used": report.get("ocr_used"),
            "error_message": report.get("error_message"),
            "warnings": report.get("warnings", []),
            "updated_at": report.get("updated_at"),
        },
        "raw": report,
        "error_message": report.get("error_message"),
    }


def list_parse_reports(report_dir: str | Path = DEFAULT_PARSE_REPORT_DIR) -> dict[str, dict[str, Any]]:
    path = Path(report_dir)
    if not path.exists():
        return {}

    reports: dict[str, dict[str, Any]] = {}
    for report_path in sorted(path.glob("*.json")):
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            validate_parse_report(report)
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        reports[str(report["document_id"])] = report
    return reports


def delete_parse_report(document_id: str, report_dir: str | Path = DEFAULT_PARSE_REPORT_DIR) -> dict[str, Any]:
    path = _report_path(report_dir, document_id)
    if not path.exists():
        return {"target": "parse_report", "status": "skipped", "reason": "parse_report 不存在"}
    try:
        path.unlink()
    except OSError as e:
        return {"target": "parse_report", "status": "failed", "reason": str(e)}
    return {"target": "parse_report", "status": "success", "reason": f"已删除 {path.name}"}


def diff_parse_reports(old: dict[str, Any] | None, new: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    old = old or {}
    new = new or {}
    diff: dict[str, dict[str, Any]] = {}
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            diff[key] = {"old": old.get(key), "new": new.get(key)}
    return diff
