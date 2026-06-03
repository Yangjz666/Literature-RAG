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
    load_parse_report_detail,
    load_parse_report,
    delete_parse_report,
    save_parse_report,
)


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


def test_parse_report_detail_includes_failed_report_summary(tmp_path):
    report = build_parse_report(
        document_id="doc_failed",
        filename="bad.pdf",
        parse_status=PARSE_STATUS_FAILED,
        error_message="无法打开文件",
    )
    save_parse_report(report, tmp_path)

    detail = load_parse_report_detail("doc_failed", tmp_path)

    assert detail["exists"] is True
    assert detail["summary"]["parse_status"] == PARSE_STATUS_FAILED
    assert detail["summary"]["error_message"] == "无法打开文件"
    assert detail["raw"] == report


def test_parse_report_detail_missing_shape(tmp_path):
    detail = load_parse_report_detail("missing", tmp_path)

    assert detail["exists"] is False
    assert detail["raw"] is None
    assert "未找到" in detail["error_message"]


def test_delete_parse_report_only_removes_target_report(tmp_path):
    report = build_parse_report(
        document_id="doc_delete",
        filename="paper.pdf",
        parse_status=PARSE_STATUS_SUCCESS,
        pages_total=1,
        pages_parsed=1,
    )
    save_parse_report(report, tmp_path)

    result = delete_parse_report("doc_delete", tmp_path)
    missing = delete_parse_report("doc_delete", tmp_path)

    assert result["status"] == "success"
    assert missing["status"] == "skipped"
    assert load_parse_report("doc_delete", tmp_path) is None
