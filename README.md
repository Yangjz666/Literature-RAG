# CO2RR 文献 RAG Agent

本项目是面向 CO2RR 科研文献的本地 RAG Agent，用于解析本地 PDF / Supporting Information，建立 ChromaDB + BM25 + parent chunk store 索引，并基于检索到的证据生成可追溯回答。

## 核心入口

- `文献查询`：保留现有 V1 结构化抽取和 V2 文献综合入口。
- `文献库管理`：查看本地文献、parse_report、index_status、chunk 预览，并执行单篇重新解析、单篇重建索引、全量重建索引和删除关联记录。

文献库管理页面说明见 [docs/document_library.md](docs/document_library.md)。

## 本地运行

```bash
source .venv/bin/activate
python -m streamlit run ui/streamlit_app.py
```

LLM 和 Embedding 配置优先从 `.env` 或环境变量读取。不要提交 `.env`、API Key、本地 PDF、向量库、BM25、parent store、parse_reports 或 output。

## 测试

```bash
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_index_status.py tests/test_document_library.py -q
```

测试使用临时目录、fixture 和 mock，不依赖真实 LLM、真实 Embedding API 或真实文献库。
