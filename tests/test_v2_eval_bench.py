import json

import pytest

from app.eval_bench import (
    compute_evidence_hit_rate,
    compute_recall_at_k,
    compute_unsupported_claim_rate,
    load_eval_jsonl,
    summarize_eval_results,
)


def test_load_eval_jsonl_reads_sample_records(tmp_path):
    path = tmp_path / "bench.jsonl"
    records = [
        {
            "question": "How were Ag NPs synthesized?",
            "mode": "synthesis",
            "gold_evidence": [
                {
                    "chunk_id": "c1",
                    "citation_id": "S1",
                    "paper_name": "Zhang_2023",
                    "evidence_text": "Ag NPs were prepared by chemical reduction.",
                }
            ],
            "expected_answer_points": ["chemical reduction"],
        }
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    loaded = load_eval_jsonl(path)

    assert loaded == records


def test_empty_jsonl_returns_empty_list(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")

    assert load_eval_jsonl(path) == []


def test_invalid_json_line_raises_clear_error(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"question": "ok"}\nnot json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON on line 2"):
        load_eval_jsonl(path)


def test_recall_at_k_is_correct():
    assert compute_recall_at_k(["c1", "c2", "c3"], ["c2", "c4"], k=2) == 0.5
    assert compute_recall_at_k(["c1", "c2", "c3"], ["c2", "c4"], k=1) == 0.0


def test_evidence_hit_rate_is_correct():
    assert compute_evidence_hit_rate(["c1", "c2"], ["c3", "c2"]) == 1.0
    assert compute_evidence_hit_rate(["c1"], ["c3"]) == 0.0


def test_unsupported_claim_rate_is_correct():
    claims = [
        {"claim": "a", "support_status": "supported"},
        {"claim": "b", "support_status": "unsupported"},
        {"claim": "c", "support_status": "partially_supported"},
    ]

    assert compute_unsupported_claim_rate(claims) == 1 / 3


def test_no_gold_evidence_does_not_crash():
    assert compute_recall_at_k(["c1"], [], k=5) == 0.0
    assert compute_evidence_hit_rate(["c1"], []) == 0.0


def test_no_retrieved_evidence_does_not_crash():
    assert compute_recall_at_k([], ["c1"], k=5) == 0.0
    assert compute_evidence_hit_rate([], ["c1"]) == 0.0


def test_duplicate_retrieved_ids_do_not_break_metrics():
    assert compute_recall_at_k(["c1", "c1", "c2"], ["c1", "c2"], k=3) == 1.0
    assert compute_evidence_hit_rate(["c1", "c1"], ["c1"]) == 1.0


def test_summarize_eval_results_handles_empty_and_averages():
    assert summarize_eval_results([]) == {
        "total_questions": 0,
        "average_recall": 0.0,
        "average_hit_rate": 0.0,
        "unsupported_claim_rate": 0.0,
    }

    summary = summarize_eval_results(
        [
            {"recall": 1.0, "hit_rate": 1.0, "claims": [{"support_status": "unsupported"}]},
            {"recall": 0.0, "hit_rate": 0.0, "claims": [{"support_status": "supported"}]},
        ]
    )

    assert summary["total_questions"] == 2
    assert summary["average_recall"] == 0.5
    assert summary["average_hit_rate"] == 0.5
    assert summary["unsupported_claim_rate"] == 0.5
