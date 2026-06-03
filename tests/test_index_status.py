from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.index_status import (
    STATUS_FAILED,
    STATUS_INDEXED,
    build_operation_summary,
    load_index_status,
    record_failure,
    save_index_status,
    update_document_status,
)


def test_load_index_status_returns_empty_shape_for_missing_file(tmp_path):
    status = load_index_status(tmp_path / "missing.json")

    assert status == {"last_updated": "", "documents": {}, "operations": {}}


def test_update_document_status_saves_record(tmp_path):
    path = tmp_path / "index_status.json"

    record = update_document_status(
        "doc_test",
        {"filename": "paper.pdf", "status": STATUS_INDEXED, "chunk_count": 7},
        path=path,
    )
    loaded = load_index_status(path)

    assert record["status"] == STATUS_INDEXED
    assert loaded["documents"]["doc_test"]["chunk_count"] == 7


def test_record_failure_sets_stage_and_reason(tmp_path):
    path = tmp_path / "index_status.json"

    record = record_failure("doc_test", "embedding", "quota exceeded", path=path)

    assert record["status"] == STATUS_FAILED
    assert record["failure_stage"] == "embedding"
    assert record["failure_reason"] == "quota exceeded"


def test_invalid_status_is_rejected(tmp_path):
    path = tmp_path / "index_status.json"
    data = {
        "last_updated": "",
        "documents": {
            "doc_test": {"document_id": "doc_test", "status": "done"},
        },
        "operations": {},
    }

    with pytest.raises(ValueError, match="index_status"):
        save_index_status(data, path)


def test_build_operation_summary_validates_operation_type():
    summary = build_operation_summary("op_1", "reparse", status="success", filename="paper.pdf")

    assert summary["operation_id"] == "op_1"
    assert summary["operation_type"] == "reparse"
    assert summary["filename"] == "paper.pdf"

    with pytest.raises(ValueError, match="operation_type"):
        build_operation_summary("op_2", "unknown")
