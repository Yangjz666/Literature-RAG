# Contract: 本地状态文件

## data/parse_reports/{document_id}.json

```json
{
  "document_id": "doc_abc123",
  "filename": "paper.pdf",
  "filepath": "/path/to/paper.pdf",
  "file_fingerprint": "mtime_size",
  "paper_title": "Title",
  "doi": "10.xxxx/yyyy",
  "year": 2024,
  "journal": "Journal",
  "is_si": false,
  "main_document_id": null,
  "metadata_source": {
    "paper_title": "pdf_metadata",
    "doi": "text_regex",
    "year": "filename_heuristic",
    "journal": "unknown"
  },
  "parse_status": "success",
  "pages_total": 12,
  "pages_parsed": 12,
  "text_length": 34567,
  "chunks_created": 123,
  "tables_found": 0,
  "figure_captions_found": 0,
  "ocr_used": false,
  "error_message": null,
  "warnings": [],
  "created_at": "2026-06-02T10:00:00",
  "updated_at": "2026-06-02T10:00:00"
}
```

Allowed `parse_status`: `success`、`partial`、`failed`。

## data/index_status.json

```json
{
  "last_updated": "2026-06-02T10:00:00",
  "documents": {
    "doc_abc123": {
      "document_id": "doc_abc123",
      "filename": "paper.pdf",
      "status": "indexed",
      "parse_completed": true,
      "chunks_generated": true,
      "embedding_completed": true,
      "vector_index_written": true,
      "keyword_index_written": true,
      "parent_store_written": true,
      "chunk_count": 123,
      "failure_stage": null,
      "failure_reason": null,
      "last_operation_id": "op_001",
      "last_operation_type": "rebuild_index",
      "created_at": "2026-06-02T10:00:00",
      "updated_at": "2026-06-02T10:00:00"
    }
  },
  "operations": {
    "op_001": {
      "operation_id": "op_001",
      "operation_type": "rebuild_index",
      "document_id": "doc_abc123",
      "filename": "paper.pdf",
      "status": "success",
      "current_stage": "indexed",
      "completed_document_count": 1,
      "failed_document_count": 0,
      "current_document_chunk_count": 123,
      "results": {},
      "old_state": {},
      "new_state": {},
      "diff": {},
      "error_messages": [],
      "created_at": "2026-06-02T10:00:00",
      "updated_at": "2026-06-02T10:00:00"
    }
  }
}
```

Allowed `status`: `not_indexed`、`parsing`、`parsed`、`chunked`、`embedding`、`indexed`、`failed`。

## data/index_manifest.json

兼容现有格式：

```json
{
  "last_updated": "2026-05-31T16:11:28",
  "files": {
    "paper.pdf": {
      "fingerprint": "mtime_size",
      "chunk_count": 181,
      "status": "indexed",
      "error": null
    }
  }
}
```

新增字段允许但不强制旧记录存在：

```json
{
  "document_id": "doc_abc123",
  "filepath": "/path/to/paper.pdf",
  "fingerprint": "mtime_size",
  "chunk_count": 181,
  "status": "indexed",
  "error": null,
  "updated_at": "2026-06-02T10:00:00"
}
```

## Atomic Write Rule

所有 JSON 状态文件写入必须采用同目录临时文件 + replace 的方式。写入失败时不得清空旧状态文件。
