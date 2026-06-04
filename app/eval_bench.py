from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_eval_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no}: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Invalid JSONL record on line {line_no}: expected object")
            records.append(record)
    return records


def _unique_ids(ids: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in ids or []:
        item = str(value)
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def compute_recall_at_k(
    retrieved_ids: list[str] | tuple[str, ...] | set[str] | None,
    gold_ids: list[str] | tuple[str, ...] | set[str] | None,
    k: int,
) -> float:
    gold = set(_unique_ids(gold_ids))
    if not gold:
        return 0.0
    retrieved = set(_unique_ids(retrieved_ids)[: max(k, 0)])
    return len(retrieved & gold) / len(gold)


def compute_evidence_hit_rate(
    retrieved_ids: list[str] | tuple[str, ...] | set[str] | None,
    gold_ids: list[str] | tuple[str, ...] | set[str] | None,
) -> float:
    gold = set(_unique_ids(gold_ids))
    if not gold:
        return 0.0
    retrieved = set(_unique_ids(retrieved_ids))
    return 1.0 if retrieved & gold else 0.0


def compute_unsupported_claim_rate(claims: list[dict[str, Any]] | None) -> float:
    if not claims:
        return 0.0
    unsupported = [
        claim
        for claim in claims
        if str(claim.get("support_status", "")).lower() == "unsupported"
    ]
    return len(unsupported) / len(claims)


def summarize_eval_results(results: list[dict[str, Any]] | None) -> dict[str, float | int]:
    rows = results or []
    if not rows:
        return {
            "total_questions": 0,
            "average_recall": 0.0,
            "average_hit_rate": 0.0,
            "unsupported_claim_rate": 0.0,
        }

    recall_values = [float(row.get("recall", 0.0)) for row in rows]
    hit_values = [float(row.get("hit_rate", 0.0)) for row in rows]
    claims = []
    for row in rows:
        claims.extend(row.get("claims", []) or [])

    return {
        "total_questions": len(rows),
        "average_recall": sum(recall_values) / len(rows),
        "average_hit_rate": sum(hit_values) / len(rows),
        "unsupported_claim_rate": compute_unsupported_claim_rate(claims),
    }
