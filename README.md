# CO2RR 文献 RAG Agent

本项目是面向 CO2RR 科研文献的本地 RAG Agent，用于解析本地 PDF / Supporting Information，建立 ChromaDB + BM25 + parent chunk store 索引，并基于检索到的证据生成可追溯回答。

回答和报告必须坚持 evidence-first：没有本地检索证据时不能编造结论，关键事实应能回到文献、chunk、页码或原文片段。

## 核心入口

- `文献查询`：保留现有 V1 结构化抽取和 V2 文献综合入口。
- `文献库管理`：Feature 001 新增入口，用于查看文献库状态、单篇详情、解析报告、chunk 预览、索引阶段和失败原因，并执行文献库维护操作。

## Feature 002：检索调试 Debug Trace

Feature 002 在 `文献查询` 回答区域下方增加默认折叠的「检索调试 Debug Trace」面板，用于查看本轮查询的 original query、BM25 / vector / RRF / reranker 阶段结果、final context chunks、Citation / Evidence 基础匹配和 Raw JSON。

注意事项：

- Debug Trace 默认只保存当前 Streamlit session 中的本轮 trace，不落盘。
- 缺失或未启用阶段显示 `not_available`。
- Citation / Evidence 只展示 `matched` / `unmatched` 基础映射，不做 claim-level verification，也不自动判断回答真假。
- Debug Trace 记录失败只写入 warning，不应影响正常回答。

详细说明见 [docs/retrieval_debug.md](docs/retrieval_debug.md)。

## Feature 001：文献库管理与索引透明化

Feature 001 已完成以下能力：

- 文献库列表：聚合本地 PDF/SI、`index_manifest.json`、`parse_reports/` 和 `index_status.json`。
- 单篇文献详情：展示 parse_report 摘要与原始 JSON、index_status、失败阶段、失败原因、最近一次操作和 chunk preview。
- 单篇重新解析：只重新解析当前文献，失败时保留旧 parse_report。
- 单篇重建索引：只重建当前文献的 ChromaDB、BM25 和 parent store 记录，不触发全库重建。
- 全量重建索引：用户明确点击后按文献边界执行，并显示进度和摘要。
- 删除文献关联记录：逐项清理 manifest、parse_report、chunks、ChromaDB、BM25、parent store 和 index_status。
- 删除保护：删除关联记录默认不会删除原始 PDF 文件。

详细使用说明见 [docs/document_library.md](docs/document_library.md)。

## 本地运行

```bash
source .venv/bin/activate
.venv/bin/python -m streamlit run ui/streamlit_app.py
```

LLM 和 Embedding 配置优先从 `.env` 或环境变量读取。不要提交 `.env`、API Key、本地 PDF、向量库、BM25、parent store、parse_reports 或 output。

## 测试

Feature 001 相关测试：

```bash
.venv/bin/python -m py_compile app/indexer.py app/document_library.py app/index_status.py app/parse_report.py ui/streamlit_app.py
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py tests/test_indexer_delete.py -q
```

完整回归：

```bash
.venv/bin/python -m pytest
```

测试使用临时目录、fixture 和 mock，不依赖真实 LLM、真实 Embedding API 或真实文献库。

## 已知限制

- 文献库管理使用本地 JSON/manifest、ChromaDB、BM25 和 parent store，不引入数据库。
- 索引操作需要正确配置 Embedding API；配置缺失时列表和 parse_report 仍可查看，但 chunk preview 和索引重建会受限。
- Streamlit smoke test 只能确认服务启动；删除、重建和真实检索仍建议在小型测试文献夹中手动验证。
- Feature 002 的 Debug Trace 不包含完整 citation verification、FastAPI、Docker、联网文献下载、多用户系统或 V1/V2 主流程重写。
