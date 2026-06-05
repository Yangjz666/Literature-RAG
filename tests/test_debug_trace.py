import json
from datetime import datetime

from app.debug_trace import (
    create_debug_trace,
    mark_stage_not_available,
    normalize_trace_chunk,
    normalize_trace_chunks,
    normalize_trace_citation,
    prepare_debug_trace_table,
    record_final_answer,
    record_final_context,
    record_stage_results,
    record_citations,
    record_error,
    safe_trace_call,
    to_json_safe,
)


def test_create_debug_trace_has_base_structure():
    trace = create_debug_trace("What catalysts improve CO2RR?", query_mode="qa")

    assert isinstance(trace, dict)
    assert trace["trace_id"]
    assert trace["created_at"]
    assert trace["user_query"] == "What catalysts improve CO2RR?"
    assert trace["original_query"] == "What catalysts improve CO2RR?"
    assert trace["query_mode"] == "qa"
    assert trace["rewritten_query"] == "not_available"
    assert trace["bm25_results"] == "not_available"
    assert trace["vector_results"] == "not_available"
    assert trace["rrf_results"] == "not_available"
    assert trace["reranker_results"] == "not_available"
    assert trace["final_context_chunks"] == []
    assert trace["citations_used"] == []
    assert trace["warning"] == []
    assert trace["error"] is None
    assert trace["failed_stage"] is None


def test_normalize_trace_chunk_handles_dict_metadata_and_preview():
    raw_chunk = {
        "chunk_id": "chunk-1",
        "text": "x" * 520,
        "score": 0.92,
        "metadata": {
            "document_id": "doc-1",
            "filename": "paper.pdf",
            "page": 3,
            "section": "Results",
            "parent_chunk_id": "parent-1",
        },
    }

    chunk = normalize_trace_chunk(raw_chunk, "bm25")

    assert chunk["document_id"] == "doc-1"
    assert chunk["filename"] == "paper.pdf"
    assert chunk["page"] == 3
    assert chunk["section"] == "Results"
    assert chunk["chunk_id"] == "chunk-1"
    assert chunk["parent_chunk_id"] == "parent-1"
    assert chunk["score"] == 0.92
    assert chunk["source_stage"] == "bm25"
    assert len(chunk["text_preview"]) <= 403
    assert chunk["text_preview"].endswith("...")


def test_normalize_trace_chunk_missing_fields_are_none():
    chunk = normalize_trace_chunk({"text": "short evidence"}, "vector")

    assert chunk["document_id"] is None
    assert chunk["filename"] is None
    assert chunk["page"] is None
    assert chunk["section"] is None
    assert chunk["chunk_id"] is None
    assert chunk["parent_chunk_id"] is None
    assert chunk["score"] is None
    assert chunk["source_stage"] == "vector"
    assert chunk["text_preview"] == "short evidence"


def test_normalize_trace_chunks_handles_empty_and_items():
    assert normalize_trace_chunks([], "bm25") == []
    assert normalize_trace_chunks(None, "bm25") == []

    chunks = normalize_trace_chunks(
        [{"chunk_id": "c1", "text": "one"}, {"chunk_id": "c2", "text": "two"}],
        "reranker",
    )

    assert [chunk["chunk_id"] for chunk in chunks] == ["c1", "c2"]
    assert all(chunk["source_stage"] == "reranker" for chunk in chunks)


def test_record_stage_results_writes_normalized_chunks():
    trace = create_debug_trace("query")

    record_stage_results(trace, "bm25_results", [{"chunk_id": "c1", "text": "bm25"}], "bm25")

    assert trace["bm25_results"][0]["chunk_id"] == "c1"
    assert trace["bm25_results"][0]["source_stage"] == "bm25"


def test_record_final_context_and_answer():
    trace = create_debug_trace("query")

    record_final_context(trace, [{"chunk_id": "ctx-1", "text": "context"}])
    record_final_answer(trace, "answer text")

    assert trace["final_context_chunks"][0]["chunk_id"] == "ctx-1"
    assert trace["final_context_chunks"][0]["source_stage"] == "final_context"
    assert trace["final_answer"] == "answer text"


def test_mark_stage_not_available_sets_stage_and_warning():
    trace = create_debug_trace("query")

    mark_stage_not_available(trace, "rrf_results", "RRF disabled")

    assert trace["rrf_results"] == "not_available"
    assert "RRF disabled" in trace["warning"]
    assert trace["bm25_results"] == "not_available"


def test_record_error_normalizes_failed_stage_and_sanitizes_message():
    trace = create_debug_trace("query")

    record_error(trace, "not_a_stage", RuntimeError("failure at /home/user/private/file.pdf with test-secret-token"))

    assert trace["failed_stage"] == "unknown_failed"
    assert "failure at" in trace["error"]
    assert "/home/" not in trace["error"]
    assert "test-secret-token" in trace["error"]
    json.dumps(to_json_safe(trace))


def test_to_json_safe_handles_non_serializable_values():
    trace = create_debug_trace("query")
    trace["created_at_obj"] = datetime(2026, 6, 5, 1, 2, 3)
    trace["ids"] = {"a", "b"}

    safe = to_json_safe(trace)

    assert safe["created_at_obj"] == "2026-06-05T01:02:03"
    assert sorted(safe["ids"]) == ["a", "b"]
    json.dumps(safe)


def test_normalize_trace_citation_marks_matched_by_chunk_id():
    final_context = [
        {
            "document_id": "doc-1",
            "filename": "paper.pdf",
            "page": 2,
            "section": "Intro",
            "chunk_id": "chunk-1",
            "text_preview": "context evidence",
        }
    ]
    citation = {"citation_id": "S1", "chunk_id": "chunk-1", "evidence_text": "cited evidence"}

    normalized = normalize_trace_citation(citation, final_context)

    assert normalized["citation_id"] == "S1"
    assert normalized["chunk_id"] == "chunk-1"
    assert normalized["filename"] == "paper.pdf"
    assert normalized["evidence_text_preview"] == "cited evidence"
    assert normalized["matched_final_context"] is True
    assert normalized["match_status"] == "matched"


def test_normalize_trace_citation_marks_unmatched_without_claim_verification():
    final_context = [{"chunk_id": "chunk-1", "filename": "paper.pdf"}]
    citation = {"citation_id": "S2", "chunk_id": "missing", "evidence_text": "unmatched evidence"}

    normalized = normalize_trace_citation(citation, final_context)

    assert normalized["citation_id"] == "S2"
    assert normalized["chunk_id"] == "missing"
    assert normalized["matched_final_context"] is False
    assert normalized["match_status"] == "unmatched"
    assert "verification" not in normalized


def test_record_citations_writes_matched_and_unmatched_entries():
    trace = create_debug_trace("query")
    trace["final_context_chunks"] = [
        {"chunk_id": "chunk-1", "filename": "paper.pdf", "text_preview": "context"}
    ]

    record_citations(
        trace,
        [
            {"citation_id": "S1", "chunk_id": "chunk-1", "evidence_text": "matched"},
            {"citation_id": "S2", "chunk_id": "missing", "evidence_text": "unmatched"},
        ],
    )

    assert [citation["match_status"] for citation in trace["citations_used"]] == [
        "matched",
        "unmatched",
    ]


def test_record_citations_handles_missing_citations_as_empty_list():
    trace = create_debug_trace("query")

    record_citations(trace, None)

    assert trace["citations_used"] == []


def test_prepare_debug_trace_table_handles_not_available_stage():
    trace = create_debug_trace("query")

    rows = prepare_debug_trace_table(trace, "bm25_results")

    assert rows == [{"status": "not_available"}]


def test_prepare_debug_trace_table_returns_chunk_fields():
    trace = create_debug_trace("query")
    trace["final_context_chunks"] = [
        {
            "document_id": "doc-1",
            "filename": "paper.pdf",
            "page": 1,
            "section": "Results",
            "chunk_id": "c1",
            "parent_chunk_id": "p1",
            "score": 0.5,
            "source_stage": "final_context",
            "text_preview": "bounded preview",
            "text": "should not be displayed",
        }
    ]

    rows = prepare_debug_trace_table(trace, "final_context_chunks")

    assert rows == [
        {
            "document_id": "doc-1",
            "filename": "paper.pdf",
            "page": 1,
            "section": "Results",
            "chunk_id": "c1",
            "parent_chunk_id": "p1",
            "score": 0.5,
            "source_stage": "final_context",
            "text_preview": "bounded preview",
        }
    ]


def test_prepare_debug_trace_table_returns_citation_fields():
    trace = create_debug_trace("query")
    trace["citations_used"] = [
        {
            "citation_id": "S1",
            "filename": "paper.pdf",
            "page": 1,
            "section": "Results",
            "chunk_id": "c1",
            "evidence_text_preview": "evidence preview",
            "match_status": "matched",
            "matched_final_context": True,
        }
    ]

    rows = prepare_debug_trace_table(trace, "citations_used")

    assert rows == [
        {
            "citation_id": "S1",
            "filename": "paper.pdf",
            "page": 1,
            "section": "Results",
            "chunk_id": "c1",
            "evidence_text_preview": "evidence preview",
            "match_status": "matched",
        }
    ]


def test_raw_debug_trace_json_is_serializable_after_table_preparation():
    trace = create_debug_trace("query")
    trace["raw_object"] = datetime(2026, 6, 5, 12, 0, 0)

    prepare_debug_trace_table(trace, "bm25_results")
    json.dumps(to_json_safe(trace))


def test_debug_trace_failure_becomes_warning_and_does_not_affect_answer():
    trace = create_debug_trace("query")

    def failing_trace_record():
        raise RuntimeError("trace failed at /home/user/private.py")

    answer = "主回答仍然返回"
    safe_trace_call(trace, failing_trace_record, "Debug Trace 测试记录失败")

    assert answer == "主回答仍然返回"
    assert trace["error"] is None
    assert trace["failed_stage"] is None
    assert trace["warning"]
    assert "Debug Trace 测试记录失败" in trace["warning"][0]
    assert "/home/" not in trace["warning"][0]
    assert "Traceback" not in trace["warning"][0]


def test_safe_trace_call_returns_default_when_trace_operation_fails():
    trace = create_debug_trace("query")

    result = safe_trace_call(
        trace,
        lambda: (_ for _ in ()).throw(RuntimeError("trace write failed")),
        "Debug Trace 写入失败",
        default="not_available",
    )

    assert result == "not_available"
    assert trace["warning"] == ["Debug Trace 写入失败: trace write failed"]


def test_consecutive_debug_traces_do_not_mix_context_or_citations():
    first = create_debug_trace("first query")
    second = create_debug_trace("second query")

    record_final_context(first, [{"chunk_id": "first-context", "text": "first"}])
    record_citations(first, [{"citation_id": "S1", "chunk_id": "first-context"}])
    record_final_context(second, [{"chunk_id": "second-context", "text": "second"}])
    record_citations(second, [{"citation_id": "S2", "chunk_id": "second-context"}])

    assert first["trace_id"] != second["trace_id"]
    assert first["original_query"] == "first query"
    assert second["original_query"] == "second query"
    assert [chunk["chunk_id"] for chunk in second["final_context_chunks"]] == ["second-context"]
    assert [citation["citation_id"] for citation in second["citations_used"]] == ["S2"]
    assert "first-context" not in json.dumps(to_json_safe(second), ensure_ascii=False)
    assert "S1" not in json.dumps(to_json_safe(second), ensure_ascii=False)
