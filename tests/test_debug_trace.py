import json
from datetime import datetime

from app.debug_trace import (
    create_debug_trace,
    mark_stage_not_available,
    normalize_trace_chunk,
    normalize_trace_chunks,
    normalize_trace_citation,
    record_final_answer,
    record_final_context,
    record_stage_results,
    record_citations,
    record_error,
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

    record_error(trace, "not_a_stage", RuntimeError("failure at /home/user/private/file.pdf with sk-testsecret"))

    assert trace["failed_stage"] == "unknown_failed"
    assert "failure at" in trace["error"]
    assert "/home/" not in trace["error"]
    assert "sk-testsecret" not in trace["error"]
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
