from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


STATUS_NOT_INDEXED = "not_indexed"
STATUS_PARSING = "parsing"
STATUS_PARSED = "parsed"
STATUS_CHUNKED = "chunked"
STATUS_EMBEDDING = "embedding"
STATUS_INDEXED = "indexed"
STATUS_FAILED = "failed"
VALID_INDEX_STATUSES = {
    STATUS_NOT_INDEXED,
    STATUS_PARSING,
    STATUS_PARSED,
    STATUS_CHUNKED,
    STATUS_EMBEDDING,
    STATUS_INDEXED,
    STATUS_FAILED,
}

DEFAULT_INDEX_STATUS_PATH = "./data/index_status.json"
VALID_OPERATION_TYPES = {"reparse", "rebuild_index", "full_rebuild", "delete"}
OPERATION_STATUS_RUNNING = "running"
OPERATION_STATUS_SUCCESS = "success"
OPERATION_STATUS_PARTIAL = "partial"
OPERATION_STATUS_FAILED = "failed"


def now_iso() -> str:
    return datetime.now().isoformat()


def empty_index_status() -> dict[str, Any]:
    return {"last_updated": "", "documents": {}, "operations": {}}


def default_document_status(
    document_id: str,
    filename: str = "",
    status: str = STATUS_NOT_INDEXED,
) -> dict[str, Any]:
    timestamp = now_iso()
    return {
        "document_id": document_id,
        "filename": filename,
        "status": status,
        "parse_completed": False,
        "chunks_generated": False,
        "embedding_completed": False,
        "vector_index_written": False,
        "keyword_index_written": False,
        "parent_store_written": False,
        "chunk_count": 0,
        "failure_stage": None,
        "failure_reason": None,
        "last_operation_id": None,
        "last_operation_type": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def validate_document_status(status_record: dict[str, Any]) -> None:
    if not status_record.get("document_id"):
        raise ValueError("index_status 缺少 document_id")
    status = status_record.get("status")
    if status not in VALID_INDEX_STATUSES:
        raise ValueError(f"index_status 不合法: {status!r}")


def validate_index_status(data: dict[str, Any]) -> None:
    documents = data.get("documents", {})
    if not isinstance(documents, dict):
        raise ValueError("index_status documents 必须是对象")
    for record in documents.values():
        validate_document_status(record)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def load_index_status(path: str | Path = DEFAULT_INDEX_STATUS_PATH) -> dict[str, Any]:
    status_path = Path(path)
    if not status_path.exists():
        return empty_index_status()
    with open(status_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("last_updated", "")
    data.setdefault("documents", {})
    data.setdefault("operations", {})
    validate_index_status(data)
    return data


def save_index_status(data: dict[str, Any], path: str | Path = DEFAULT_INDEX_STATUS_PATH) -> Path:
    validate_index_status(data)
    data["last_updated"] = now_iso()
    status_path = Path(path)
    _atomic_write_json(status_path, data)
    return status_path


def save_operation_summary(
    summary: dict[str, Any],
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
) -> dict[str, Any]:
    data = load_index_status(path)
    operation_id = str(summary.get("operation_id") or "")
    if not operation_id:
        raise ValueError("operation summary 缺少 operation_id")
    summary["updated_at"] = now_iso()
    data.setdefault("operations", {})[operation_id] = summary
    save_index_status(data, path)
    return summary


def update_document_status(
    document_id: str,
    updates: dict[str, Any],
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
) -> dict[str, Any]:
    data = load_index_status(path)
    current = data["documents"].get(document_id) or default_document_status(
        document_id=document_id,
        filename=str(updates.get("filename") or ""),
    )
    current.update(updates)
    current["document_id"] = document_id
    current["updated_at"] = now_iso()
    validate_document_status(current)
    data["documents"][document_id] = current
    save_index_status(data, path)
    return current


def get_document_status(
    document_id: str,
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
) -> dict[str, Any] | None:
    data = load_index_status(path)
    return data.get("documents", {}).get(document_id)


def mark_stage(
    document_id: str,
    stage: str,
    filename: str = "",
    chunk_count: int | None = None,
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
    operation_id: str | None = None,
    operation_type: str | None = None,
) -> dict[str, Any]:
    stage_updates = {
        STATUS_PARSING: {"status": STATUS_PARSING},
        STATUS_PARSED: {"status": STATUS_PARSED, "parse_completed": True},
        STATUS_CHUNKED: {"status": STATUS_CHUNKED, "parse_completed": True, "chunks_generated": True},
        STATUS_EMBEDDING: {
            "status": STATUS_EMBEDDING,
            "parse_completed": True,
            "chunks_generated": True,
        },
        STATUS_INDEXED: {
            "status": STATUS_INDEXED,
            "parse_completed": True,
            "chunks_generated": True,
            "embedding_completed": True,
            "vector_index_written": True,
            "keyword_index_written": True,
            "parent_store_written": True,
            "failure_stage": None,
            "failure_reason": None,
        },
    }
    if stage not in stage_updates:
        raise ValueError(f"index stage 不合法: {stage!r}")
    updates = dict(stage_updates[stage])
    if filename:
        updates["filename"] = filename
    if chunk_count is not None:
        updates["chunk_count"] = int(chunk_count)
    if operation_id:
        updates["last_operation_id"] = operation_id
    if operation_type:
        updates["last_operation_type"] = operation_type
    return update_document_status(document_id, updates, path=path)


def record_failure(
    document_id: str,
    stage: str,
    reason: str,
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
    filename: str = "",
    operation_id: str | None = None,
    operation_type: str | None = None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {"status": STATUS_FAILED, "failure_stage": stage, "failure_reason": reason}
    if filename:
        updates["filename"] = filename
    if operation_id:
        updates["last_operation_id"] = operation_id
    if operation_type:
        updates["last_operation_type"] = operation_type
    return update_document_status(document_id, updates, path=path)


def record_reparse_stage(
    document_id: str,
    stage_status: str,
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
    filename: str = "",
    operation_id: str | None = None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "filename": filename,
        "status": stage_status,
        "last_operation_type": "reparse",
        "failure_stage": None,
        "failure_reason": None,
    }
    if operation_id:
        updates["last_operation_id"] = operation_id
    if stage_status == STATUS_PARSING:
        updates["parse_completed"] = False
    elif stage_status == STATUS_PARSED:
        updates["parse_completed"] = True
    return update_document_status(document_id, updates, path=path)


def record_rebuild_stage(
    document_id: str,
    stage_status: str,
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
    filename: str = "",
    operation_id: str | None = None,
    chunk_count: int | None = None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "filename": filename,
        "status": stage_status,
        "last_operation_type": "rebuild_index",
        "failure_stage": None,
        "failure_reason": None,
    }
    if operation_id:
        updates["last_operation_id"] = operation_id
    if chunk_count is not None:
        updates["chunk_count"] = chunk_count
    if stage_status == STATUS_CHUNKED:
        updates["chunks_generated"] = True
    elif stage_status == STATUS_EMBEDDING:
        updates["chunks_generated"] = True
    elif stage_status == STATUS_INDEXED:
        updates.update(
            {
                "chunks_generated": True,
                "embedding_completed": True,
                "vector_index_written": True,
                "keyword_index_written": True,
                "parent_store_written": True,
            }
        )
    return update_document_status(document_id, updates, path=path)


def build_operation_summary(
    operation_id: str,
    operation_type: str,
    status: str = "running",
    **fields: Any,
) -> dict[str, Any]:
    if operation_type not in VALID_OPERATION_TYPES:
        raise ValueError(f"operation_type 不合法: {operation_type!r}")
    timestamp = now_iso()
    summary = {
        "operation_id": operation_id,
        "operation_type": operation_type,
        "document_id": None,
        "filename": None,
        "status": status,
        "current_stage": None,
        "completed_document_count": 0,
        "failed_document_count": 0,
        "current_document_chunk_count": 0,
        "results": {},
        "old_state": None,
        "new_state": None,
        "diff": None,
        "error_messages": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    summary.update(fields)
    return summary


def build_rebuild_summary(
    operation_id: str,
    operation_type: str,
    results: dict[str, dict[str, Any]],
    status: str = "success",
    **fields: Any,
) -> dict[str, Any]:
    success_count = sum(1 for result in results.values() if result.get("status") == "success")
    failed_count = sum(1 for result in results.values() if result.get("status") == "failed")
    skipped_count = sum(1 for result in results.values() if result.get("status") == "skipped")
    return build_operation_summary(
        operation_id,
        operation_type,
        status=status,
        results=results,
        total_document_count=len(results),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        completed_document_count=success_count,
        failed_document_count=failed_count,
        **fields,
    )


def cleanup_document_status(
    document_id: str,
    path: str | Path = DEFAULT_INDEX_STATUS_PATH,
) -> dict[str, Any]:
    data = load_index_status(path)
    if document_id not in data.get("documents", {}):
        return {"target": "index_status", "status": "skipped", "reason": "index_status 中无该文献"}
    del data["documents"][document_id]
    save_index_status(data, path)
    return {"target": "index_status", "status": "success", "reason": "已删除该文献状态记录"}
