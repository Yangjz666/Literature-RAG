from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.parse_report import (
    PARSE_STATUS_FAILED,
    PARSE_STATUS_SUCCESS,
    build_parse_report,
    diff_parse_reports,
    generate_document_id,
    list_parse_reports,
    load_parse_report,
    save_parse_report,
)
from app.document_library import reparse_document


def test_generate_document_id_is_stable_for_relative_path(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    first = generate_document_id(pdf, tmp_path)
    second = generate_document_id(pdf, tmp_path)

    assert first == second
    assert first.startswith("doc_")


def test_parse_report_save_load_and_list(tmp_path):
    report = build_parse_report(
        document_id="doc_test",
        filename="paper.pdf",
        filepath=str(tmp_path / "paper.pdf"),
        paper_title="CO2RR Paper",
        parse_status=PARSE_STATUS_SUCCESS,
        pages_total=2,
        pages_parsed=2,
        chunks_created=5,
    )

    saved_path = save_parse_report(report, tmp_path)
    loaded = load_parse_report("doc_test", tmp_path)
    reports = list_parse_reports(tmp_path)

    assert saved_path == tmp_path / "doc_test.json"
    assert loaded == report
    assert reports["doc_test"] == report


def test_parse_report_rejects_invalid_status():
    with pytest.raises(ValueError, match="parse_status"):
        build_parse_report(
            document_id="doc_test",
            filename="paper.pdf",
            parse_status="done",
        )


def test_failed_parse_report_requires_error_or_warning():
    with pytest.raises(ValueError, match="failed"):
        build_parse_report(
            document_id="doc_test",
            filename="paper.pdf",
            parse_status=PARSE_STATUS_FAILED,
        )


def test_diff_parse_reports_reports_changed_fields():
    old = {"document_id": "doc_test", "parse_status": "failed", "chunks_created": 0}
    new = {"document_id": "doc_test", "parse_status": "success", "chunks_created": 3}

    diff = diff_parse_reports(old, new)

    assert diff["parse_status"] == {"old": "failed", "new": "success"}
    assert diff["chunks_created"] == {"old": 0, "new": 3}


def test_single_document_reparse_failure_preserves_old_parse_report(tmp_path):
    report_dir = tmp_path / "reports"
    status_path = tmp_path / "index_status.json"
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    old_report = build_parse_report(
        document_id="doc_test",
        filename="paper.pdf",
        filepath=str(pdf),
        paper_title="Old usable report",
        parse_status=PARSE_STATUS_SUCCESS,
        pages_total=2,
        pages_parsed=2,
        chunks_created=6,
    )
    save_parse_report(old_report, report_dir)

    def failing_parse(*args, **kwargs):
        return {
            "document_id": "doc_test",
            "filename": "paper.pdf",
            "filepath": str(pdf),
            "pages": [],
            "metadata": {},
            "warnings": [],
            "error": "无法打开文件",
            "report": build_parse_report(
                document_id="doc_test",
                filename="paper.pdf",
                filepath=str(pdf),
                parse_status=PARSE_STATUS_FAILED,
                error_message="无法打开文件",
            ),
        }

    summary = reparse_document(
        document={"document_id": "doc_test", "filename": "paper.pdf", "filepath": str(pdf)},
        config={"parse_report_dir": str(report_dir), "index_status_path": str(status_path)},
        parse_func=failing_parse,
    )

    assert load_parse_report("doc_test", report_dir) == old_report
    assert summary["status"] == "failed"
    assert summary["failure_stage"] == "parsing"
    assert summary["failure_reason"] == "无法打开文件"
    assert summary["old_state"]["parse_status"] == PARSE_STATUS_SUCCESS
    assert summary["new_state"]["parse_status"] == PARSE_STATUS_FAILED
