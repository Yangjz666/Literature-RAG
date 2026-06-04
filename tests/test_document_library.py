import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.document_library import (
    delete_document_records,
    get_document_detail,
    list_document_library,
    rebuild_document_index,
    reparse_document,
)
from app.index_status import STATUS_FAILED, STATUS_INDEXED, load_index_status, save_index_status, update_document_status
from app.parse_report import PARSE_STATUS_FAILED, PARSE_STATUS_SUCCESS, build_parse_report, load_parse_report, save_parse_report


class FakeIndex:
    def __init__(self):
        self.removed = []
        self.rebuilt = []

    def get_chunk_previews(self, document_id, filename=None, limit=20):
        return [
            {
                "chunk_id": "chunk_1",
                "page": 2,
                "section": "Results",
                "is_si": False,
                "text_preview": "CO2RR activity evidence",
            }
        ]

    def remove_document_records(self, document_id, filename=None):
        self.removed.append((document_id, filename))
        return {
            "vector_index": {"target": "vector_index", "status": "success", "reason": "删除 2 条 ChromaDB chunk"},
            "keyword_index": {"target": "keyword_index", "status": "success", "reason": "BM25 已重建"},
            "parent_store": {"target": "parent_store", "status": "success", "reason": "删除 1 条 parent chunk"},
        }

    def rebuild_document_index(self, paper, folder, config, progress_cb=None):
        self.rebuilt.append((paper["document_id"], paper["filename"]))
        return {"document_id": paper["document_id"], "filename": paper["filename"], "chunk_count": 1}


def test_document_library_empty_folder_and_no_state(tmp_path):
    folder = tmp_path / "pdfs"
    folder.mkdir()

    rows = list_document_library(
        folder,
        {
            "index_manifest_path": str(tmp_path / "missing_manifest.json"),
            "parse_report_dir": str(tmp_path / "missing_reports"),
            "index_status_path": str(tmp_path / "missing_status.json"),
        },
    )

    assert rows == []


def test_document_library_discovers_local_pdf_and_si(tmp_path):
    folder = tmp_path / "pdfs"
    folder.mkdir()
    (folder / "main.pdf").write_bytes(b"%PDF-1.4")
    (folder / "main_SI.pdf").write_bytes(b"%PDF-1.4")

    rows = list_document_library(
        folder,
        {
            "index_manifest_path": str(tmp_path / "manifest.json"),
            "parse_report_dir": str(tmp_path / "reports"),
            "index_status_path": str(tmp_path / "index_status.json"),
        },
    )

    by_filename = {row["filename"]: row for row in rows}
    assert by_filename["main.pdf"]["is_si"] is False
    assert by_filename["main.pdf"]["parse_status"] == "unknown"
    assert by_filename["main.pdf"]["index_status"] == "not_indexed"
    assert by_filename["main_SI.pdf"]["is_si"] is True


def test_document_library_supports_old_manifest_format(tmp_path):
    manifest_path = tmp_path / "index_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "last_updated": "2026-06-02T00:00:00",
                "files": {
                    "paper.pdf": {
                        "fingerprint": "mtime_size",
                        "chunk_count": 12,
                        "status": "indexed",
                        "error": None,
                    },
                    "legacy.pdf": "legacy_fingerprint",
                },
            }
        ),
        encoding="utf-8",
    )

    rows = list_document_library(
        "",
        {
            "index_manifest_path": str(manifest_path),
            "parse_report_dir": str(tmp_path / "reports"),
            "index_status_path": str(tmp_path / "index_status.json"),
        },
    )

    by_filename = {row["filename"]: row for row in rows}
    assert by_filename["paper.pdf"]["chunk_count"] == 12
    assert by_filename["paper.pdf"]["index_status"] == "indexed"
    assert by_filename["legacy.pdf"]["file_fingerprint"] == "legacy_fingerprint"


def test_document_library_does_not_duplicate_local_file_from_old_manifest(tmp_path):
    folder = tmp_path / "pdfs"
    folder.mkdir()
    (folder / "paper.pdf").write_bytes(b"%PDF-1.4")
    manifest_path = tmp_path / "index_manifest.json"
    manifest_path.write_text(
        json.dumps({"last_updated": "", "files": {"paper.pdf": {"chunk_count": 4, "status": "indexed"}}}),
        encoding="utf-8",
    )

    rows = list_document_library(
        folder,
        {
            "index_manifest_path": str(manifest_path),
            "parse_report_dir": str(tmp_path / "reports"),
            "index_status_path": str(tmp_path / "index_status.json"),
        },
    )

    assert len(rows) == 1
    assert rows[0]["filename"] == "paper.pdf"
    assert rows[0]["chunk_count"] == 4


def test_document_library_merges_parse_report_and_index_status(tmp_path):
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    manifest_path = tmp_path / "index_manifest.json"
    report = build_parse_report(
        document_id="doc_test",
        filename="paper.pdf",
        paper_title="Parsed Title",
        doi="10.1021/example",
        parse_status=PARSE_STATUS_SUCCESS,
        pages_total=1,
        pages_parsed=1,
        chunks_created=3,
    )
    save_parse_report(report, report_dir)
    save_index_status(
        {
            "last_updated": "",
            "documents": {
                "doc_test": {
                    "document_id": "doc_test",
                    "filename": "paper.pdf",
                    "status": STATUS_FAILED,
                    "parse_completed": True,
                    "chunks_generated": True,
                    "embedding_completed": False,
                    "vector_index_written": False,
                    "keyword_index_written": False,
                    "parent_store_written": False,
                    "chunk_count": 2,
                    "failure_stage": "embedding",
                    "failure_reason": "quota exceeded",
                    "last_operation_id": None,
                    "last_operation_type": None,
                    "created_at": "2026-06-02T00:00:00",
                    "updated_at": "2026-06-02T00:00:00",
                }
            },
            "operations": {},
        },
        status_path,
    )

    rows = list_document_library(
        "",
        {
            "index_manifest_path": str(manifest_path),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
        },
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "Parsed Title"
    assert row["doi"] == "10.1021/example"
    assert row["parse_status"] == "success"
    assert row["index_status"] == STATUS_FAILED
    assert row["chunk_count"] == 2
    assert row["error_summary"] == "quota exceeded"


def test_document_detail_includes_report_chunk_preview_and_failure_fields(tmp_path):
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    report = build_parse_report(
        document_id="doc_detail",
        filename="paper.pdf",
        paper_title="Detail Paper",
        parse_status=PARSE_STATUS_SUCCESS,
        pages_total=2,
        pages_parsed=2,
        chunks_created=1,
    )
    save_parse_report(report, report_dir)
    update_document_status(
        "doc_detail",
        {
            "filename": "paper.pdf",
            "status": STATUS_FAILED,
            "failure_stage": "embedding",
            "failure_reason": "quota exceeded",
            "last_operation_id": "op_1",
        },
        path=status_path,
    )
    status_data = load_index_status(status_path)
    status_data["operations"]["op_1"] = {"operation_id": "op_1", "operation_type": "rebuild_index", "status": "failed"}
    save_index_status(status_data, status_path)

    detail = get_document_detail(
        "doc_detail",
        "",
        {
            "index_manifest_path": str(tmp_path / "manifest.json"),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
        },
        index=FakeIndex(),
    )

    assert detail["parse_report"]["summary"]["paper_title"] == "Detail Paper"
    assert detail["index_status"]["failure_stage"] == "embedding"
    assert detail["errors"]["failure_reason"] == "quota exceeded"
    assert detail["latest_operation"]["operation_id"] == "op_1"
    assert detail["chunk_previews"][0]["chunk_id"] == "chunk_1"
    assert detail["chunk_previews"][0]["page"] == 2


def test_reparse_document_preserves_old_report_on_failure(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    old_report = build_parse_report(
        document_id="doc_reparse",
        filename="paper.pdf",
        parse_status=PARSE_STATUS_SUCCESS,
        pages_total=1,
        pages_parsed=1,
    )
    save_parse_report(old_report, report_dir)

    def fail_parse(*args, **kwargs):
        return {"paper": None, "report": None, "warnings": [], "error": "parse failed"}

    monkeypatch.setattr("app.document_library.parse_single_file", fail_parse)
    summary = reparse_document(
        "doc_reparse",
        "",
        {
            "index_manifest_path": str(tmp_path / "manifest.json"),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
        },
    )

    assert summary["status"] == "failed"
    assert load_parse_report("doc_reparse", report_dir) == old_report
    assert load_index_status(status_path)["documents"]["doc_reparse"]["failure_stage"] == "parsing"


def test_rebuild_document_index_updates_only_target_status(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    save_parse_report(
        build_parse_report(
            document_id="doc_target",
            filename="target.pdf",
            parse_status=PARSE_STATUS_SUCCESS,
            pages_total=1,
            pages_parsed=1,
        ),
        report_dir,
    )
    update_document_status("doc_target", {"filename": "target.pdf", "status": STATUS_FAILED}, path=status_path)
    update_document_status("doc_other", {"filename": "other.pdf", "status": STATUS_INDEXED, "chunk_count": 9}, path=status_path)

    def ok_parse(*args, **kwargs):
        return {
            "paper": {
                "document_id": "doc_target",
                "filename": "target.pdf",
                "filepath": "",
                "paper_name": "target",
                "doi": None,
                "is_si": False,
                "pages": [{"page": 1, "text": "CO2RR evidence. More evidence."}],
            },
            "report": None,
            "warnings": [],
            "error": None,
        }

    monkeypatch.setattr("app.document_library.parse_single_file", ok_parse)
    summary = rebuild_document_index(
        "doc_target",
        "",
        {
            "index_manifest_path": str(tmp_path / "manifest.json"),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
            "chunking": {"child_chunk_max_size": 300, "parent_chunk_size": 800},
        },
        FakeIndex(),
    )

    loaded = load_index_status(status_path)
    assert summary["status"] == "success"
    assert loaded["documents"]["doc_target"]["status"] == STATUS_INDEXED
    assert loaded["documents"]["doc_other"]["status"] == STATUS_INDEXED
    assert loaded["documents"]["doc_other"]["chunk_count"] == 9


def test_rebuild_document_index_failure_preserves_old_indexed_status(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    save_parse_report(
        build_parse_report(
            document_id="doc_keep",
            filename="paper.pdf",
            parse_status=PARSE_STATUS_SUCCESS,
            pages_total=1,
            pages_parsed=1,
        ),
        report_dir,
    )
    update_document_status("doc_keep", {"filename": "paper.pdf", "status": STATUS_INDEXED, "chunk_count": 4}, path=status_path)

    def fail_parse(*args, **kwargs):
        return {"paper": None, "report": None, "warnings": [], "error": "parse unavailable"}

    monkeypatch.setattr("app.document_library.parse_single_file", fail_parse)
    summary = rebuild_document_index(
        "doc_keep",
        "",
        {
            "index_manifest_path": str(tmp_path / "manifest.json"),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
        },
        FakeIndex(),
    )

    status = load_index_status(status_path)["documents"]["doc_keep"]
    assert summary["status"] == "failed"
    assert status["status"] == STATUS_INDEXED
    assert status["chunk_count"] == 4
    assert status["failure_stage"] == "embedding"


def test_delete_document_records_reports_each_item_and_keeps_pdf(tmp_path):
    folder = tmp_path / "pdfs"
    folder.mkdir()
    pdf = folder / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    manifest_path = tmp_path / "index_manifest.json"
    report = build_parse_report(
        document_id="doc_delete",
        filename="paper.pdf",
        filepath=str(pdf),
        parse_status=PARSE_STATUS_SUCCESS,
        pages_total=1,
        pages_parsed=1,
    )
    save_parse_report(report, report_dir)
    update_document_status("doc_delete", {"filename": "paper.pdf", "status": STATUS_INDEXED}, path=status_path)
    manifest_path.write_text(
        json.dumps({"last_updated": "", "files": {"paper.pdf": {"document_id": "doc_delete", "chunk_count": 3}}}),
        encoding="utf-8",
    )

    summary = delete_document_records(
        "doc_delete",
        folder,
        {
            "index_manifest_path": str(manifest_path),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
        },
        index=FakeIndex(),
    )

    assert summary["status"] == "success"
    assert summary["pdf_deleted"] is False
    assert pdf.exists()
    assert {key for key in summary["results"]} >= {
        "manifest",
        "parse_report",
        "chunks",
        "vector_index",
        "keyword_index",
        "parent_store",
        "index_status",
    }
    assert summary["results"]["manifest"]["status"] == "success"
    assert summary["results"]["chunks"]["status"] == "success"
    assert load_parse_report("doc_delete", report_dir) is None
    assert "doc_delete" not in load_index_status(status_path)["documents"]

    rows = list_document_library(
        folder,
        {
            "index_manifest_path": str(manifest_path),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
        },
    )
    assert all(row["document_id"] != "doc_delete" for row in rows)
    assert rows[0]["filename"] == "paper.pdf"
    assert rows[0]["parse_status"] == "unknown"
    assert rows[0]["index_status"] == "not_indexed"
    assert rows[0]["chunk_count"] == 0

    operation = load_index_status(status_path)["operations"][summary["operation_id"]]
    assert operation["operation_type"] == "delete"
    assert operation["results"]["index_status"]["status"] == "success"


def test_delete_document_records_reports_partial_failure(tmp_path):
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    save_parse_report(
        build_parse_report(
            document_id="doc_partial",
            filename="paper.pdf",
            parse_status=PARSE_STATUS_FAILED,
            error_message="old failure",
        ),
        report_dir,
    )

    class FailingIndex(FakeIndex):
        def remove_document_records(self, document_id, filename=None):
            return {
                "vector_index": {"target": "vector_index", "status": "failed", "reason": "chroma locked"},
                "keyword_index": {"target": "keyword_index", "status": "skipped", "reason": "前序失败"},
                "parent_store": {"target": "parent_store", "status": "success", "reason": "ok"},
            }

    summary = delete_document_records(
        "doc_partial",
        "",
        {
            "index_manifest_path": str(tmp_path / "manifest.json"),
            "parse_report_dir": str(report_dir),
            "index_status_path": str(status_path),
        },
        index=FailingIndex(),
    )

    assert summary["status"] == "partial"
    assert summary["results"]["chunks"]["status"] == "failed"
    assert summary["results"]["vector_index"]["status"] == "failed"
    assert "vector_index" in summary["error_messages"][0]
