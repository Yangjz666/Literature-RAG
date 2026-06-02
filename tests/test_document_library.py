import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.document_library import list_document_library
from app.index_status import STATUS_FAILED, STATUS_INDEXED, save_index_status
from app.parse_report import PARSE_STATUS_SUCCESS, build_parse_report, save_parse_report


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
