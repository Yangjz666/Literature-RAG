# Contract: 文献库管理页面与操作接口

## UI Contract

入口名称：`文献库管理`

列表必须展示：

- `filename`
- `title` / `paper_title`
- `doi`
- `year`
- `journal`
- `is_si`
- `main_document_id` 或未关联提示
- `parse_status`
- `index_status`
- `pages_total`
- `pages_parsed`
- `chunk_count`
- `tables_found`
- `figure_captions_found`
- `ocr_used`
- `last_updated`
- `error_summary`

详情必须展示：

- 文献基本信息。
- parse_report 字段摘要与原始 JSON 查看入口。
- chunk 列表：`chunk_id`、`page`、`section`、`is_si`、`main_document_id`、文本预览。
- index_status 阶段布尔值、失败阶段、失败原因、最近操作摘要。

操作按钮：

- `重新解析当前文献`：只处理当前 `document_id`。
- `重建当前文献索引`：只处理当前 `document_id`。
- `删除当前文献关联记录`：需要确认，默认不删除 PDF 本体。
- `全量重建索引`：需要明确启动，显示跨文献进度。

## Backend Function Contract

### list_document_library

```python
def list_document_library(folder: str, config: dict) -> list[dict]:
    ...
```

返回 `Document` 聚合列表。必须接受空目录、缺失 manifest、缺失 parse_report、缺失 index_status。

### reparse_document

```python
def reparse_document(document_id: str, filepath: str, config: dict) -> dict:
    ...
```

返回 `IndexOperation` 摘要。成功时写入新 parse_report；失败时保留旧报告并返回 diff/failure reason。

### rebuild_document_index

```python
def rebuild_document_index(document_id: str, filepath: str, config: dict, progress_cb=None) -> dict:
    ...
```

只重建当前文献索引。必须更新 `index_status`，并在失败时保留旧状态记录。

### delete_document_records

```python
def delete_document_records(document_id: str, filename: str, config: dict) -> dict:
    ...
```

返回逐项结果：

```json
{
  "manifest": {"status": "success", "message": ""},
  "parse_report": {"status": "success", "message": ""},
  "chunks": {"status": "success", "message": ""},
  "vector_index": {"status": "success", "message": ""},
  "keyword_index": {"status": "success", "message": ""},
  "parent_store": {"status": "success", "message": ""},
  "index_status": {"status": "success", "message": ""}
}
```

任一项失败不得阻止后续项尝试，最终 operation status 可为 `partial`。

## Compatibility Contract

- V1 结构化抽取默认入口、参数和 Markdown 输出格式不变。
- V2 文献综合入口、模式选择和报告输出格式不变。
- 现有 `index_manifest` 旧格式必须可读。
- 新增页面不得要求用户先全库重建才能查看本地 PDF/SI 列表。
