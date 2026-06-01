import json
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - only used when optional dependency is absent
    BM25Okapi = None
from openai import OpenAI, OpenAIError, RateLimitError

from app.llm_client import load_env_file

logger = logging.getLogger(__name__)

load_env_file(Path(__file__).resolve().parent.parent / ".env")

DEFAULT_EMBEDDING_MODEL = "text-embedding-v4"
DEFAULT_EMBEDDING_DIM = 1024
DEFAULT_EMBEDDING_BATCH_SIZE = 10
EMBEDDING_COLLECTION_NAME = "literature_chunks"


def get_file_fingerprint(path: str) -> str:
    stat = os.stat(path)
    return f"{stat.st_mtime}_{stat.st_size}"


def get_changed_files(folder: str, manifest: dict) -> tuple[list[str], list[str]]:
    files_manifest = manifest.get("files", manifest)
    current = {
        f: get_file_fingerprint(os.path.join(folder, f))
        for f in os.listdir(folder)
        if f.lower().endswith(".pdf")
    }
    added = [
        f for f, fp in current.items()
        if f not in files_manifest
        or (isinstance(files_manifest[f], str) and files_manifest[f] != fp)
        or (isinstance(files_manifest[f], dict) and files_manifest[f].get("fingerprint") != fp)
    ]
    removed = [f for f in files_manifest if f not in current]
    return added, removed


def load_manifest(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": "", "files": {}}


def save_manifest(path: str, manifest: dict) -> None:
    manifest["last_updated"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


class LiteratureIndex:
    def __init__(self, config: dict):
        self.config = config
        self.chroma_path = config.get("chroma_db_path", "./data/chroma_db")
        self.manifest_path = config.get("index_manifest_path", "./data/index_manifest.json")
        self.embed_model_name = (
            os.environ.get("EMBEDDING_MODEL")
            or config.get("embedding_model")
            or DEFAULT_EMBEDDING_MODEL
        )
        self.embedding_dim = self._int_config(
            "EMBEDDING_DIM",
            "embedding_dim",
            DEFAULT_EMBEDDING_DIM,
            legacy_keys=("embedding_dimension", "embedding_dimensions"),
        )
        self.embedding_batch_size = min(
            self._int_config("EMBEDDING_BATCH_SIZE", "embedding_batch_size", DEFAULT_EMBEDDING_BATCH_SIZE),
            DEFAULT_EMBEDDING_BATCH_SIZE,
        )

        import chromadb

        os.makedirs(self.chroma_path, exist_ok=True)
        self._chroma = chromadb.PersistentClient(path=self.chroma_path)
        self._collection = self._chroma.get_or_create_collection(
            EMBEDDING_COLLECTION_NAME,
            metadata={
                "embedding_model": self.embed_model_name,
                "embedding_dim": self.embedding_dim,
            },
        )
        self._validate_collection_embedding_config()

        # Embedding 使用独立的 OpenAI-compatible /v1/embeddings 通道，不复用问答模型配置。
        api_key = os.environ.get("EMBEDDING_API_KEY") or config.get("embedding_api_key")
        base_url = os.environ.get("EMBEDDING_BASE_URL") or config.get("embedding_base_url")
        if not api_key:
            raise RuntimeError(
                "Embedding API Key 未配置。请在 .env 中设置 EMBEDDING_API_KEY，"
                "例如填写阿里云百炼 API Key。"
            )
        if not base_url:
            raise RuntimeError(
                "Embedding Base URL 未配置。请在 .env 中设置 EMBEDDING_BASE_URL，"
                "例如 https://dashscope.aliyuncs.com/compatible-mode/v1。"
            )
        self._openai = OpenAI(api_key=api_key, base_url=base_url)

        # BM25 和父 chunk store 保存在 chroma_path 旁边
        self._bm25_path = os.path.join(self.chroma_path, "bm25.pkl")
        self._parent_store_path = os.path.join(self.chroma_path, "parent_store.pkl")
        self._bm25: BM25Okapi | None = None
        self._bm25_ids: list[str] = []
        self._parent_store: dict[str, dict] = {}

        self._load_bm25()
        self._load_parent_store()

    def _int_config(
        self,
        env_name: str,
        config_key: str,
        default: int,
        legacy_keys: tuple[str, ...] = (),
    ) -> int:
        raw = os.environ.get(env_name) or self.config.get(config_key)
        if raw is None:
            for key in legacy_keys:
                if self.config.get(key) is not None:
                    raw = self.config[key]
                    break
        if raw in (None, ""):
            return default
        try:
            return int(raw)
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"{env_name} / {config_key} 必须是整数，当前值为 {raw!r}。") from e

    def _validate_collection_embedding_config(self) -> None:
        count = self._collection.count()
        if count == 0:
            return

        metadata = self._collection.metadata or {}
        stored_model = metadata.get("embedding_model")
        stored_dim = metadata.get("embedding_dim")
        if stored_model == self.embed_model_name and int(stored_dim or 0) == self.embedding_dim:
            return

        raise RuntimeError(
            "当前 Chroma 向量库已存在，但 embedding 配置与当前配置不一致或缺少元数据。"
            f"当前配置：model={self.embed_model_name}, dim={self.embedding_dim}；"
            f"向量库元数据：model={stored_model}, dim={stored_dim}。"
            f"请先备份或删除旧向量库目录 {self.chroma_path}，然后重新入库。"
        )

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        try:
            for start in range(0, len(texts), self.embedding_batch_size):
                batch = texts[start:start + self.embedding_batch_size]
                resp = self._openai.embeddings.create(
                    model=self.embed_model_name,
                    input=batch,
                    dimensions=self.embedding_dim,
                    encoding_format="float",
                )
                embeddings.extend(item.embedding for item in resp.data)
        except RateLimitError as e:
            raise RuntimeError(
                "Embedding API 额度不足或触发限流，无法建立/查询向量索引。"
                "请检查阿里云百炼账号额度，或稍后重试。"
            ) from e
        except OpenAIError as e:
            raise RuntimeError(
                "Embedding API 调用失败。当前模型为 "
                f"{self.embed_model_name!r}，维度为 {self.embedding_dim}；"
                "如果报 model_not_found，请在 .env 中修改 EMBEDDING_MODEL，"
                "并确认 EMBEDDING_API_KEY / EMBEDDING_BASE_URL 指向支持 embeddings 的 OpenAI-compatible 通道。"
                f"\n原始错误：{e}"
            ) from e
        return embeddings

    # ── BM25 持久化 ──────────────────────────────────────────────────────────

    def _load_bm25(self) -> None:
        if os.path.exists(self._bm25_path):
            with open(self._bm25_path, "rb") as f:
                data = pickle.load(f)
            self._bm25 = data["bm25"]
            self._bm25_ids = data["ids"]

    def _save_bm25(self) -> None:
        with open(self._bm25_path, "wb") as f:
            pickle.dump({"bm25": self._bm25, "ids": self._bm25_ids}, f)

    def _load_parent_store(self) -> None:
        if os.path.exists(self._parent_store_path):
            with open(self._parent_store_path, "rb") as f:
                self._parent_store = pickle.load(f)

    def _save_parent_store(self) -> None:
        with open(self._parent_store_path, "wb") as f:
            pickle.dump(self._parent_store, f)

    # ── 索引操作 ─────────────────────────────────────────────────────────────

    def add_chunks(self, children: list[dict], parents: list[dict]) -> None:
        """将子 chunk 加入向量索引和 BM25，父 chunk 加入 parent_store。"""
        if not children:
            return

        texts = [c["text"] for c in children]
        ids = [c["chunk_id"] for c in children]
        metadatas = [
            {k: v for k, v in c.items() if k not in ("text",) and isinstance(v, (str, int, float, bool))}
            for c in children
        ]

        embeddings = self._embed_texts(texts)
        self._collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)

        # 更新 BM25：重建（小规模文献库可接受）
        existing = self._collection.get(include=["documents"])
        all_texts = existing["documents"]
        all_ids = existing["ids"]
        tokenized = [t.lower().split() for t in all_texts]
        if BM25Okapi is None:
            raise RuntimeError("rank-bm25 is required to build BM25 index.")
        self._bm25 = BM25Okapi(tokenized)
        self._bm25_ids = all_ids
        self._save_bm25()

        # 更新父 chunk store
        for p in parents:
            self._parent_store[p["chunk_id"]] = p
        self._save_parent_store()

    def remove_by_filename(self, filename: str) -> None:
        """从索引中删除指定文件的所有 chunk。"""
        results = self._collection.get(where={"filename": filename})
        if results["ids"]:
            self._collection.delete(ids=results["ids"])
            logger.info(f"从索引删除 {len(results['ids'])} 个 chunk（{filename}）")

        # 重建 BM25
        existing = self._collection.get(include=["documents"])
        if existing["documents"]:
            tokenized = [t.lower().split() for t in existing["documents"]]
            if BM25Okapi is None:
                raise RuntimeError("rank-bm25 is required to build BM25 index.")
            self._bm25 = BM25Okapi(tokenized)
            self._bm25_ids = existing["ids"]
        else:
            self._bm25 = None
            self._bm25_ids = []
        self._save_bm25()

        # 清理父 chunk store
        to_del = [k for k, v in self._parent_store.items() if v.get("filename") == filename]
        for k in to_del:
            del self._parent_store[k]
        self._save_parent_store()

    def vector_search(self, query: str, top_k: int = 20) -> list[dict]:
        if self._collection.count() == 0:
            return []
        emb = self._embed_texts([query])
        results = self._collection.query(query_embeddings=emb, n_results=min(top_k, self._collection.count()))
        hits = []
        for i, doc_id in enumerate(results["ids"][0]):
            hits.append({
                "chunk_id": doc_id,
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": 1 - results["distances"][0][i],
            })
        return hits

    def bm25_search(self, query: str, top_k: int = 20) -> list[dict]:
        if not self._bm25 or not self._bm25_ids:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        hits = []
        for idx, score in ranked:
            if score <= 0:
                continue
            chunk_id = self._bm25_ids[idx]
            hits.append({"chunk_id": chunk_id, "score": score})
        return hits

    def get_parent(self, parent_chunk_id: str) -> dict | None:
        return self._parent_store.get(parent_chunk_id)

    def get_chunk_by_id(self, chunk_id: str) -> dict | None:
        result = self._collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if result["ids"]:
            return {"chunk_id": chunk_id, "text": result["documents"][0], "metadata": result["metadatas"][0]}
        return None
