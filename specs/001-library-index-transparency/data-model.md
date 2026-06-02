# Data Model: 文献库管理与索引透明化

## Document

代表本地 PDF 或 Supporting Information 文件，由本地目录扫描结果、manifest、parse_report 和 index_status 聚合得到。

**Fields**:

- `document_id`: string，稳定文档标识。
- `filename`: string，文件名，兼容旧 `index_manifest` key。
- `filepath`: string，本地路径；UI 可缩略显示。
- `file_fingerprint`: string，mtime + size 或后续内容 hash。
- `title`: string|null，优先来自 parse_report。
- `doi`: string|null。
- `year`: int|string|null。
- `journal`: string|null。
- `is_si`: bool。
- `main_document_id`: string|null。
- `parse_status`: `success` | `partial` | `failed` | `unknown`。
- `index_status`: `not_indexed` | `parsing` | `parsed` | `chunked` | `embedding` | `indexed` | `failed`。
- `pages_total`: int|null。
- `pages_parsed`: int|null。
- `chunk_count`: int。
- `tables_found`: int。
- `figure_captions_found`: int。
- `ocr_used`: bool。
- `last_updated`: string|null，ISO datetime。
- `error_summary`: string|null。

**Relationships**:

- 一个 Document 可有一个 Parse Report。
- 一个 Document 可有一个 Index Status。
- 一个 Document 可有多个 Chunk Record。
- SI Document 可通过 `main_document_id` 指向主文献。

## Parse Report

每篇文献一次成功、部分成功或失败解析后的事实记录。

**Fields**:

- `document_id`: string。
- `filename`: string。
- `filepath`: string。
- `file_fingerprint`: string。
- `paper_title`: string|null。
- `doi`: string|null。
- `year`: int|string|null。
- `journal`: string|null。
- `is_si`: bool。
- `main_document_id`: string|null。
- `metadata_source`: object，例如 `{"title": "pdf_metadata", "doi": "text_regex", "year": "filename_heuristic"}`。
- `parse_status`: `success` | `partial` | `failed`。
- `pages_total`: int。
- `pages_parsed`: int。
- `text_length`: int。
- `chunks_created`: int。
- `tables_found`: int。
- `figure_captions_found`: int。
- `ocr_used`: bool。
- `error_message`: string|null。
- `warnings`: list[string]。
- `created_at`: string，ISO datetime。
- `updated_at`: string，ISO datetime。

**Validation Rules**:

- `parse_status` 只允许 `success`、`partial`、`failed`。
- `pages_parsed <= pages_total`。
- `failed` 必须有 `error_message` 或至少一条 warning。
- `document_id`、`filename`、`created_at`、`updated_at` 必填。

## Library Manifest Entry

兼容现有 `data/index_manifest.json` 的索引清单记录。

**Fields**:

- `document_id`: string|null，旧记录可能缺失。
- `filename`: string，由 key 或字段提供。
- `filepath`: string|null。
- `fingerprint`: string。
- `chunk_count`: int。
- `status`: string，旧值可为 `indexed`。
- `error`: string|null。
- `updated_at`: string|null。

**Validation Rules**:

- 聚合层必须接受旧格式 `{filename: fingerprint}` 和当前格式 `{filename: {fingerprint, chunk_count, status, error}}`。

## Index Status

描述每篇文献的当前索引阶段、阶段完成布尔值和失败原因。

**Fields**:

- `document_id`: string。
- `filename`: string。
- `status`: `not_indexed` | `parsing` | `parsed` | `chunked` | `embedding` | `indexed` | `failed`。
- `parse_completed`: bool。
- `chunks_generated`: bool。
- `embedding_completed`: bool。
- `vector_index_written`: bool。
- `keyword_index_written`: bool。
- `parent_store_written`: bool。
- `chunk_count`: int。
- `failure_stage`: string|null。
- `failure_reason`: string|null。
- `last_operation_id`: string|null。
- `last_operation_type`: `reparse` | `rebuild_index` | `full_rebuild` | `delete` | null。
- `created_at`: string。
- `updated_at`: string。

**State Transitions**:

- `not_indexed` → `parsing` → `parsed` → `chunked` → `embedding` → `indexed`。
- 任意状态 → `failed`。
- `failed` 可在用户重新解析或重建索引后重新进入 `parsing` 或 `embedding`。

## Chunk Record

现有 ChromaDB/BM25/parent store 中的文献片段，新增实现应保证 metadata 可追溯。

**Fields**:

- `chunk_id`: string。
- `parent_chunk_id`: string|null。
- `document_id`: string。
- `filename`: string。
- `paper_name`: string|null。
- `doi`: string|null。
- `page`: int|null。
- `section`: string|null。
- `is_si`: bool。
- `main_document_id`: string|null。
- `text`: string。

## Index Operation

用户触发的重新解析、单篇索引重建、全量重建或删除操作摘要。

**Fields**:

- `operation_id`: string。
- `operation_type`: `reparse` | `rebuild_index` | `full_rebuild` | `delete`。
- `document_id`: string|null。
- `filename`: string|null。
- `status`: `running` | `success` | `partial` | `failed`。
- `current_stage`: string|null。
- `completed_document_count`: int。
- `failed_document_count`: int。
- `current_document_chunk_count`: int。
- `results`: object，删除时按 `manifest`、`parse_report`、`chunks`、`vector_index`、`keyword_index`、`parent_store`、`index_status` 分项。
- `old_state`: object|null。
- `new_state`: object|null。
- `diff`: object|null。
- `error_messages`: list[string]。
- `created_at`: string。
- `updated_at`: string。
