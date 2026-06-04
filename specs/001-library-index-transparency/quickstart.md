# Quickstart: 文献库管理与索引透明化

## 前置条件

- 当前分支：`001-library-index-transparency`。
- 配置文件：`config.yaml` 保留现有 `chroma_db_path`、`index_manifest_path`，实现阶段新增或默认推导 `parse_report_dir=./data/parse_reports`、`index_status_path=./data/index_status.json`。
- 不提交真实 API Key；LLM/Embedding Key 继续从 `.env` 或环境变量读取。

## 实现步骤

1. 新增 `app/parse_report.py`，实现 parse_report 构建、校验、原子保存、读取、列表和 diff。
2. 新增 `app/index_status.py`，实现状态枚举、阶段更新、失败记录和 operation summary。
3. 新增 `app/document_library.py`，聚合本地 PDF/SI 目录、`index_manifest`、parse_report 和 index_status。
4. 修改 `app/ingest.py`，增加单文件解析入口，并在解析完成、部分成功或失败时写 parse_report。
5. 修改 `app/indexer.py`，增加单文档索引重建和删除关联记录能力，复用现有 ChromaDB、BM25 和 parent store。
6. 修改 `ui/streamlit_app.py`，新增“文献库管理”独立入口，保留现有 V1 结构化抽取和 V2 文献综合入口。
7. 新增 pytest：`tests/test_parse_report.py`、`tests/test_document_library.py`，建议增加 `tests/test_index_status.py`。
8. 新增 `docs/document_library.md` 或更新 README，说明页面、字段、状态、重建、删除和限制。

## 验收命令

```bash
pytest tests/test_parse_report.py tests/test_document_library.py
pytest tests/test_acceptance.py tests/test_v2_pipeline.py tests/test_v2_router.py
```

如测试依赖真实 LLM/Embedding Key，需把不可离线运行的检查标记为手工 smoke test，并记录原因。

## 手工验收

1. 启动 Streamlit 应用，进入文献库管理入口。
2. 使用已有本地 PDF/SI 目录，确认列表能显示本地文件、旧 manifest 已索引文件、缺失 parse_report 的未知状态。
3. 打开已索引文献详情，确认能看到 parse_report 摘要、chunk 数量、chunk page/section/SI 来源、index_status。
4. 对单篇执行重新解析，确认不触发全库索引重建。
5. 对同一篇执行单篇索引重建，确认只更新该文献的 ChromaDB/BM25/parent store 记录。
6. 删除单篇文献关联记录，确认 UI 逐项报告 manifest、parse_report、chunks、vector index、BM25、parent store、index_status 的成功/失败。
7. 返回现有查询入口，确认 V1 结构化抽取和 V2 文献综合入口仍可启动，默认参数和输出格式不变。

## 数据安全检查

- 删除操作必须有用户确认。
- 默认不删除 PDF 文件本体。
- 单篇操作失败时旧 parse_report/index_status 不被清空。
- UI 不显示或记录 API Key。
