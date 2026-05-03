from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.indexer import LiteratureIndex
    from app.llm_client import LLMClient

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
