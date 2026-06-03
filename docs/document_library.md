# 文献库管理与索引透明化

## 页面用途

`文献库管理` 是独立管理入口，用于查看本地 PDF/SI、解析报告、索引状态、失败原因和 chunk 预览。该页面不改变现有 `文献查询` 的 V1 结构化抽取和 V2 文献综合主流程。

## 列表字段

- `parse_status`：`unknown`、`success`、`partial`、`failed`。
- `index_status`：`not_indexed`、`parsing`、`parsed`、`chunked`、`embedding`、`indexed`、`failed`。
- `SI`：是否识别为 Supporting Information。
- `chunk 数量`：优先来自 index_status，其次来自 parse_report 或 manifest。
- `错误摘要`：优先显示 index_status 的失败原因，其次显示 parse_report 或 manifest 错误。

## 单篇详情

选择一篇文献后，页面显示：

- parse_report 摘要和原始 JSON。
- index_status、失败阶段、失败原因、最近一次操作。
- chunk 预览，包括 `chunk_id`、`page`、`section`、`is_si`、`text_preview`。

如果索引对象无法加载，页面仍会显示文献状态和 parse_report，但 chunk 预览和索引操作会受限。

## 重新解析与重建索引

- `单篇重新解析`：只解析当前文献，更新 parse_report 和解析阶段状态，不触发全库重建。
- `单篇重建索引`：只处理当前文献，复用现有 chunk、ChromaDB、BM25 和 parent store 写入逻辑，不调用全库重建路径。
- `全量重建索引`：明确由用户点击触发，按文献边界显示进度和摘要。

失败保护：

- 单篇重新解析失败时保留旧 parse_report。
- 单篇重建索引失败时保留旧可用 index_status，并记录失败阶段和原因。

## 删除关联记录

删除操作需要输入当前文件名确认。默认绝对不会删除原始 PDF 文件。

删除时逐项尝试清理：

- manifest
- parse_report
- ChromaDB vector records
- BM25
- parent store
- index_status

每一项都会返回 `success`、`failed` 或 `skipped`，并显示原因。若某项失败，后续项仍会尝试执行，页面会显示失败项和失败原因。

## 已知限制

- 该功能不引入数据库、FastAPI、Docker、完整 Debug Trace 或 citation verification。
- chunk 预览依赖现有 ChromaDB / parent store 可读。
- 真实 Embedding 配置缺失时，索引对象可能无法初始化，索引操作需要先补齐本地 `.env` 配置。
