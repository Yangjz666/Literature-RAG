from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.indexer import LiteratureIndex
    from app.llm_client import LLMClient

from app.context_builder import build_retrieval_text
from app.debug_trace import record_error, record_stage_results
from app.schemas_v2 import CandidateChunk

logger = logging.getLogger(__name__)
llm_client = None

KEYWORD_EXPANSION_PROMPT = """你是 CO2RR 文献检索专家。
根据用户问题，生成用于文献检索的英文关键词列表（包含同义词、缩写、相关术语）。
只输出 JSON 数组，例如：["AgNPs", "Ag nanoparticles", "silver nanoparticles"]
不要输出其他内容。

用户问题：{query}"""


def expand_keywords(query: str, llm_client: "LLMClient" | None = None) -> list[str]:
    client = llm_client or globals().get("llm_client")
    if client is None:
        return [query]
    prompt = KEYWORD_EXPANSION_PROMPT.format(query=query)
    try:
        raw = client.chat(prompt, json_mode=False)
        # 兼容返回 JSON 数组或 JSON 对象
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(k) for k in parsed]
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return [str(k) for k in v]
    except Exception as e:
        logger.warning(f"关键词扩展失败，使用原始查询: {e}")
    return [query]


class HybridRetriever:
    """轻量适配器，兼容验收测试中的 bm25/vector mock 接口。"""

    def __init__(self, bm25, vector, final_top_k: int = 10, rrf_k: int = 60):
        self.bm25 = bm25
        self.vector = vector
        self.final_top_k = final_top_k
        self.rrf_k = rrf_k

    def retrieve(self, query: str) -> list[dict]:
        bm25_hits = self.bm25.retrieve(query)
        vec_hits = self.vector.retrieve(query)

        bm25_rank_map = {h["chunk_id"]: i + 1 for i, h in enumerate(bm25_hits)}
        vec_rank_map = {h["chunk_id"]: i + 1 for i, h in enumerate(vec_hits)}
        hit_map = {h["chunk_id"]: h for h in bm25_hits + vec_hits}

        scored = []
        for cid in set(bm25_rank_map) | set(vec_rank_map):
            item = dict(hit_map[cid])
            item["rrf_score"] = rrf_score(
                bm25_rank=bm25_rank_map.get(cid),
                vec_rank=vec_rank_map.get(cid),
                k=self.rrf_k,
            )
            scored.append(item)

        scored.sort(key=lambda x: x["rrf_score"], reverse=True)
        return scored[: self.final_top_k]


def rrf_score(bm25_rank: int | None, vec_rank: int | None, k: int = 60) -> float:
    score = 0.0
    if bm25_rank is not None:
        score += 1 / (k + bm25_rank)
    if vec_rank is not None:
        score += 1 / (k + vec_rank)
    return score


def hybrid_retrieve(
    query: str,
    index: "LiteratureIndex",
    llm_client: "LLMClient",
    config: dict,
) -> list[dict]:
    """
    混合检索：关键词扩展 → BM25 + 向量 → RRF 融合 → 扩展父 chunk。
    返回父 chunk 列表，每个父 chunk 附带命中的子 chunk IDs 和 RRF 分数。
    """
    retrieval_cfg = config.get("retrieval", {})
    bm25_top_k = retrieval_cfg.get("bm25_top_k", 20)
    vec_top_k = retrieval_cfg.get("vector_top_k", 20)
    rrf_k = retrieval_cfg.get("rrf_k", 60)
    final_top_k = retrieval_cfg.get("final_top_k", 10)

    keywords = expand_keywords(query, llm_client)
    expanded_query = " ".join(keywords)
    logger.info(f"扩展关键词: {keywords}")

    vec_hits = index.vector_search(expanded_query, top_k=vec_top_k)
    bm25_hits = index.bm25_search(expanded_query, top_k=bm25_top_k)

    vec_rank_map = {h["chunk_id"]: i for i, h in enumerate(vec_hits)}
    bm25_rank_map = {h["chunk_id"]: i for i, h in enumerate(bm25_hits)}

    all_ids = set(vec_rank_map) | set(bm25_rank_map)
    scored = []
    for cid in all_ids:
        score = rrf_score(
            bm25_rank=bm25_rank_map.get(cid),
            vec_rank=vec_rank_map.get(cid),
            k=rrf_k,
        )
        scored.append((cid, score))
    scored.sort(key=lambda x: x[1], reverse=True)

    # 按父 chunk 去重，保留最高分
    parent_map: dict[str, dict] = {}
    for cid, score in scored:
        child = index.get_chunk_by_id(cid)
        if not child:
            continue
        parent_id = child["metadata"].get("parent_chunk_id", cid)
        if parent_id not in parent_map or parent_map[parent_id]["rrf_score"] < score:
            parent_chunk = index.get_parent(parent_id)
            if not parent_chunk:
                # 父 chunk 不存在时用子 chunk 本身作为上下文
                parent_chunk = {"chunk_id": parent_id, "text": child["text"], **child["metadata"]}
            parent_map[parent_id] = {
                **parent_chunk,
                "rrf_score": score,
                "hit_child_ids": [cid],
            }
        else:
            parent_map[parent_id]["hit_child_ids"].append(cid)

    results = sorted(parent_map.values(), key=lambda x: x["rrf_score"], reverse=True)
    return results[:final_top_k]


def _get_nested_value(item: dict, key: str, default: Any = None) -> Any:
    if key in item and item[key] is not None:
        return item[key]
    metadata = item.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get(key) is not None:
        return metadata[key]
    return default


def _get_chunk(index: "LiteratureIndex", chunk_id: str) -> dict | None:
    for method_name in ("get_chunk_by_id", "get_chunk", "get"):
        method = getattr(index, method_name, None)
        if method is None:
            continue
        try:
            chunk = method(chunk_id)
        except TypeError:
            continue
        if chunk:
            return chunk
    return None


def _get_parent_chunk(index: "LiteratureIndex", parent_id: str, child: dict) -> dict:
    for method_name in ("get_parent", "get_parent_chunk", "get_chunk_by_id", "get_chunk"):
        method = getattr(index, method_name, None)
        if method is None:
            continue
        try:
            parent = method(parent_id)
        except TypeError:
            continue
        if parent:
            return parent
    return {"chunk_id": parent_id, "text": child.get("text", ""), **(child.get("metadata") or {})}


def _search(index: "LiteratureIndex", method_name: str, query: str, top_k: int) -> list[dict]:
    method = getattr(index, method_name, None)
    if method is None:
        return []
    try:
        return list(method(query, top_k=top_k))
    except TypeError:
        return list(method(query, top_k))


def _candidate_from_parent(
    parent_id: str,
    parent: dict,
    child_ids: list[str],
    bm25_rank: int | None,
    vector_rank: int | None,
    score: float,
) -> CandidateChunk:
    metadata = dict(parent.get("metadata") or {})
    candidate = CandidateChunk(
        chunk_id=str(_get_nested_value(parent, "chunk_id", parent_id)),
        parent_chunk_id=parent_id,
        paper_name=str(_get_nested_value(parent, "paper_name", "")),
        filename=_get_nested_value(parent, "filename"),
        doi=_get_nested_value(parent, "doi"),
        title=_get_nested_value(parent, "title"),
        year=_get_nested_value(parent, "year"),
        page=_get_nested_value(parent, "page"),
        section=_get_nested_value(parent, "section"),
        is_si=bool(_get_nested_value(parent, "is_si", False)),
        text=str(_get_nested_value(parent, "text", "")),
        metadata=metadata,
        bm25_rank=bm25_rank,
        vector_rank=vector_rank,
        rrf_score=score,
        hit_child_ids=child_ids,
    )
    candidate.retrieval_text = build_retrieval_text(candidate)
    return candidate


def hybrid_retrieve_candidates(
    query: str,
    index: "LiteratureIndex",
    llm_client: "LLMClient",
    config: dict,
    debug_trace: dict | None = None,
) -> list[CandidateChunk]:
    retrieval_cfg = (config or {}).get("retrieval", {})
    bm25_top_k = int(retrieval_cfg.get("bm25_top_k", 20))
    vec_top_k = int(retrieval_cfg.get("vector_top_k", 20))
    rrf_k = int(retrieval_cfg.get("rrf_k", 60))
    candidate_top_k = int(retrieval_cfg.get("candidate_top_k", 80))

    keywords = expand_keywords(query, llm_client)
    expanded_query = " ".join(keywords)

    try:
        vec_hits = _search(index, "vector_search", expanded_query, vec_top_k)
        record_stage_results(debug_trace, "vector_results", vec_hits, "vector")
    except Exception as exc:
        record_error(debug_trace, "vector_search_failed", exc)
        raise

    try:
        bm25_hits = _search(index, "bm25_search", expanded_query, bm25_top_k)
        record_stage_results(debug_trace, "bm25_results", bm25_hits, "bm25")
    except Exception as exc:
        record_error(debug_trace, "bm25_failed", exc)
        raise

    vector_rank_map = {str(hit["chunk_id"]): rank for rank, hit in enumerate(vec_hits, start=1)}
    bm25_rank_map = {str(hit["chunk_id"]): rank for rank, hit in enumerate(bm25_hits, start=1)}

    parent_map: dict[str, dict] = {}
    for child_id in set(vector_rank_map) | set(bm25_rank_map):
        child = _get_chunk(index, child_id)
        if not child:
            child = next(
                (
                    hit
                    for hit in [*vec_hits, *bm25_hits]
                    if str(hit.get("chunk_id")) == child_id
                ),
                None,
            )
        if not child:
            continue

        parent_id = str(_get_nested_value(child, "parent_chunk_id", child_id))
        score = rrf_score(
            bm25_rank=bm25_rank_map.get(child_id),
            vec_rank=vector_rank_map.get(child_id),
            k=rrf_k,
        )
        entry = parent_map.setdefault(
            parent_id,
            {
                "parent": _get_parent_chunk(index, parent_id, child),
                "hit_child_ids": [],
                "bm25_rank": None,
                "vector_rank": None,
                "rrf_score": 0.0,
            },
        )
        if child_id not in entry["hit_child_ids"]:
            entry["hit_child_ids"].append(child_id)
        if bm25_rank_map.get(child_id) is not None:
            current = entry["bm25_rank"]
            entry["bm25_rank"] = bm25_rank_map[child_id] if current is None else min(current, bm25_rank_map[child_id])
        if vector_rank_map.get(child_id) is not None:
            current = entry["vector_rank"]
            entry["vector_rank"] = vector_rank_map[child_id] if current is None else min(current, vector_rank_map[child_id])
        entry["rrf_score"] = max(entry["rrf_score"], score)

    candidates = [
        _candidate_from_parent(
            parent_id=parent_id,
            parent=entry["parent"],
            child_ids=entry["hit_child_ids"],
            bm25_rank=entry["bm25_rank"],
            vector_rank=entry["vector_rank"],
            score=entry["rrf_score"],
        )
        for parent_id, entry in parent_map.items()
    ]
    candidates.sort(key=lambda candidate: candidate.rrf_score or 0.0, reverse=True)
    candidates = candidates[:candidate_top_k]
    record_stage_results(debug_trace, "rrf_results", candidates, "rrf")
    return candidates
