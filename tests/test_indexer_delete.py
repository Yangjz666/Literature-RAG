from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.indexer as indexer_module
from app.indexer import LiteratureIndex


class FakeCollection:
    def __init__(self):
        self.records = {
            "chunk_target_1": {
                "document": "CO2RR target chunk",
                "metadata": {"document_id": "doc_target", "filename": "target.pdf"},
            },
            "chunk_other_1": {
                "document": "CO2RR other chunk",
                "metadata": {"document_id": "doc_other", "filename": "other.pdf"},
            },
        }
        self.deleted_ids = []

    def get(self, where=None, include=None):
        ids = []
        documents = []
        metadatas = []
        for chunk_id, record in self.records.items():
            metadata = record["metadata"]
            if where is None or all(metadata.get(key) == value for key, value in where.items()):
                ids.append(chunk_id)
                documents.append(record["document"])
                metadatas.append(metadata)
        result = {"ids": ids}
        if include and "documents" in include:
            result["documents"] = documents
        if include and "metadatas" in include:
            result["metadatas"] = metadatas
        return result

    def delete(self, ids):
        self.deleted_ids.extend(ids)
        for chunk_id in ids:
            self.records.pop(chunk_id, None)


class FakeBM25:
    def __init__(self, tokenized):
        self.tokenized = tokenized


def test_remove_document_records_deletes_vector_rebuilds_bm25_and_cleans_parent_store(tmp_path, monkeypatch):
    monkeypatch.setattr(indexer_module, "BM25Okapi", FakeBM25)
    index = LiteratureIndex.__new__(LiteratureIndex)
    index._collection = FakeCollection()
    index._bm25_path = str(tmp_path / "bm25.pkl")
    index._parent_store_path = str(tmp_path / "parent_store.pkl")
    index._bm25 = None
    index._bm25_ids = []
    index._parent_store = {
        "parent_target": {"document_id": "doc_target", "filename": "target.pdf"},
        "parent_other": {"document_id": "doc_other", "filename": "other.pdf"},
    }

    result = index.remove_document_records("doc_target", filename="target.pdf")

    assert result["vector_index"]["status"] == "success"
    assert result["keyword_index"]["status"] == "success"
    assert result["parent_store"]["status"] == "success"
    assert index._collection.deleted_ids == ["chunk_target_1"]
    assert set(index._collection.records) == {"chunk_other_1"}
    assert index._bm25_ids == ["chunk_other_1"]
    assert set(index._parent_store) == {"parent_other"}


def test_remove_document_records_skips_missing_vector_and_parent_records(tmp_path, monkeypatch):
    monkeypatch.setattr(indexer_module, "BM25Okapi", FakeBM25)
    index = LiteratureIndex.__new__(LiteratureIndex)
    index._collection = FakeCollection()
    index._bm25_path = str(tmp_path / "bm25.pkl")
    index._parent_store_path = str(tmp_path / "parent_store.pkl")
    index._bm25 = None
    index._bm25_ids = []
    index._parent_store = {
        "parent_other": {"document_id": "doc_other", "filename": "other.pdf"},
    }

    result = index.remove_document_records("doc_missing", filename="missing.pdf")

    assert result["vector_index"]["status"] == "skipped"
    assert result["keyword_index"]["status"] == "success"
    assert result["parent_store"]["status"] == "skipped"
    assert index._collection.deleted_ids == []
    assert set(index._collection.records) == {"chunk_target_1", "chunk_other_1"}
