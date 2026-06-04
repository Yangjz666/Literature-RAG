# PROJECT_CONTEXT.md

## 1. 项目名称

CO2RR-LocalScholar / CO2RR 文献 RAG Agent。

当前文档中的最新产品定位是 `CO2RR-LocalScholar V3：面向 CO2RR 科研文献的工程化可验证 RAG 系统`；代码层面更接近“V1 基础能力 + V2 文献综合流水线已部分落地，V3 仍主要停留在需求规划阶段”。

## 2. 项目一句话介绍

本项目是一个面向 CO2RR 电催化文献的本地 RAG 助手，用于读取本地 PDF / SI 文献，建立本地索引，并基于检索到的原文片段生成带证据的结构化抽取结果或文献综合报告。

项目核心约束是 evidence-first：回答、表格和结论必须尽量能追溯到本地文献 chunk、页码、章节和原文摘录；证据不足时应保守拒答或标记不确定。

## 3. 项目目标

- 从本地 CO2RR 文献库中解析 PDF 和 Supporting Information。
- 生成父子 chunk、BM25 索引、ChromaDB 向量索引和 parent chunk store。
- 支持 CO2RR 相关问题的结构化信息抽取，例如 AgNPs 合成方法、测试条件、添加剂机理。
- 为抽取记录提供 `evidence_sentence`、文献名、页码或章节，并进行原文回查。
- 支持 V2 文献综合模式：候选召回、可选 rerank、引用上下文、citation-aware synthesis、claim-level verification、Markdown V2 报告。
- 后续 V3 目标是让检索可调试、证据可追溯、结论可校验、过程可评估、系统可部署。

## 4. 当前开发阶段

当前处于 **V2 已部分实现，V3 需求已规划但尚未完整实现** 的阶段。

分层判断：

- V1：基础 RAG 问答和结构化抽取能力已经有代码闭环，包括 PDF 解析、chunk、索引、混合检索、LLM 抽取、evidence 校验、Markdown 输出和 Streamlit UI。
- V2：核心模块多数已经存在，包括 `schemas_v2.py`、`report_v2.py`、`context_builder.py`、`reranker.py`、`synthesizer.py`、`claim_verifier.py`、`feedback.py`、`followup_retriever.py`、`pipeline_v2.py`、`query_router.py`、`eval_bench.py`、`metadata_enricher.py`；其中部分能力默认关闭或是保守降级实现。
- V3：PRD 已定义文献管理、Debug Trace、历史记录、日志成本统计、评测和部署等工程化目标，但代码中没有看到完整的文献库管理页、检索 Debug 面板、历史记录页、成本统计页或部署方案闭环。

## 5. 当前技术栈

- 后端语言：Python。
- UI：Streamlit，入口为 `ui/streamlit_app.py`。
- PDF 解析：PyMuPDF。
- OCR：pytesseract + Pillow，配置位于 `config.yaml` 的 `ocr` 段。
- 文本切分：自定义父子 chunk 切分，核心文件 `app/chunker.py`。
- 向量数据库：ChromaDB，本地持久化目录默认 `./data/chroma_db`。
- BM25：`rank-bm25`，索引持久化为 `bm25.pkl`。
- Embedding：OpenAI-compatible embeddings 通道，默认模型配置为 `text-embedding-v4`，需要 `EMBEDDING_API_KEY` 和 `EMBEDDING_BASE_URL`。
- LLM：OpenAI-compatible 或 Anthropic-compatible，统一封装在 `app/llm_client.py`。
- 数据模型：Pydantic v2。
- 配置：`config.yaml` + `.env` / 环境变量。
- 测试：pytest 测试文件已存在，但当前环境未安装 pytest，未能运行。

## 6. 当前启动方式

项目没有根目录 `README.md`，启动方式需根据代码和依赖推断：

```bash
cd /home/yang_mind/projects/Literature-rag

# 建议先安装依赖，或进入已有虚拟环境
pip install -r requirements.txt

# 配置 .env，至少包含：
# LLM_PROVIDER=openai 或 anthropic
# OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
# 或 ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL / ANTHROPIC_MODEL
# EMBEDDING_API_KEY / EMBEDDING_BASE_URL

streamlit run ui/streamlit_app.py
```

运行后在侧边栏输入文献文件夹路径，先“建立 / 更新索引”，再在查询区选择结构化抽取、文献综合或精读解释模式。

## 7. 已经实现

### 7.1 V1 基础能力

- PDF 文件夹导入：`app/ingest.py` 提供 `load_folder()`、`extract_text()`、`extract_metadata()`、`is_supporting_information()`。
- OCR 降级：文字为空时可调用 pytesseract；Tesseract 可执行路径通过配置传入。
- DOI 提取和文献去重：支持 DOI 正则和内容 hash 去重。
- 父子 chunk：`app/chunker.py` 提供 child chunk、parent chunk 和 paper chunk 结构。
- 本地索引：`app/indexer.py` 使用 ChromaDB 存 child chunk embedding，BM25 pickle 存关键词索引，parent store pickle 存父 chunk。
- 增量索引：`get_changed_files()`、`index_manifest.json` 支持新增和删除文件检测。
- 混合检索：`app/retriever.py` 支持关键词扩展、BM25、向量检索、RRF 融合和父 chunk 扩展。
- V1 结构化抽取：`app/extractor.py` 定义 synthesis / test / mechanism 三类 schema 和抽取函数。
- Evidence sentence 校验：`app/verifier.py` 支持文本规范化、精确匹配、模糊句窗匹配和批量校验。
- V1 Markdown 输出：`app/generator.py` 支持主表格、Agent 分析、不确定项和证据摘录，且可保存到 `data/output`。
- Streamlit UI：支持配置 API Key、选择文献文件夹、建立索引、输入问题、结构化抽取、AI 分析和保存结果。

### 7.2 V2 已落地能力

- V2 schema：`CandidateChunk`、`SourceCitation`、`ClaimRecord`、`FeedbackRecord`、`ExternalMetadata`、`SynthesisResult` 已存在。
- V2 检索候选：`hybrid_retrieve_candidates()` 已在 `app/retriever.py` 中实现，保持 V1 `hybrid_retrieve()` 默认行为兼容。
- 上下文构建：`app/context_builder.py` 支持 `[S1]` 引用编号、metadata-aware retrieval text、单篇文献 chunk 数限制和上下文 token 预算。
- Reranker：`app/reranker.py` 支持默认 RRF 降级；当 `reranker.enabled=true` 时尝试加载 `sentence_transformers.CrossEncoder`。
- Citation-aware synthesis：`app/synthesizer.py` 要求 LLM 输出 JSON，解析失败时保守返回“证据不足”。
- Claim-level citation verification：`app/claim_verifier.py` 已实现基础校验，包括 citation id 存在性、数值信号匹配和 Agent 分析降级。
- Self-feedback：`app/feedback.py` 已有一轮反馈解析能力，但默认配置 `self_feedback.enabled=false`。
- Follow-up retrieval：`app/followup_retriever.py` 已有本地二次检索入口，但默认 `allow_followup_retrieval=false`。
- V2 报告：`app/report_v2.py` 生成七段式 Markdown V2，并保存为包含 `v2_synthesis` 的文件名。
- V2 pipeline：`app/pipeline_v2.py` 串联 candidates、rerank、context、synthesis、claim verification、feedback、可选 follow-up、报告保存。
- 模式路由：`app/query_router.py` 和 UI 中的模式选择已接入；结构化抽取是默认模式，文献综合可进入 V2 pipeline。
- 评测辅助：`app/eval_bench.py` 提供 JSONL 加载、Recall@K、Evidence Hit Rate、Unsupported Claim Rate 等指标函数。
- 外部 metadata 增强：`app/metadata_enricher.py` 已存在，默认关闭，且不作为 evidence 来源。

## 8. 部分完成

- 文献综合模式：代码闭环存在，但依赖真实索引、真实 LLM JSON 稳定输出和配置；尚未在当前环境完成端到端验证。
- Reranker：接口存在，但默认关闭；`requirements.txt` 未包含 `sentence-transformers`，启用后可能需要额外安装依赖和下载模型。
- Self-feedback：有反馈解析和 trace 记录，但默认关闭；当前 pipeline 不执行真正的“根据反馈修订答案”闭环，更多是记录问题和可选触发 follow-up。
- Follow-up retrieval：入口存在，默认关闭；可追加二次检索 chunk 并记录 trace，但是否重新综合修订答案仍需进一步确认和完善。
- Claim-level verification：已有保守规则，但不是完整语义级 NLI / LLM verifier；目前主要检查引用存在、数值信号和 Agent 分析降级。
- 精读解释模式：UI 和 router 有模式入口，但 UI 明确提示“尚未完整实现”。
- V2/V3 文档同步：需求、TDD、DEV_PLAN 与代码已有差异，特别是 DEV_PLAN 中早期“未新增”的模块现在已经存在。

## 9. 只是需求里写了但还没完整实现

- V3 文献库管理页面。
- 检索 Debug Trace 面板，展示 BM25 / vector / RRF / rerank 的完整中间结果。
- 查询历史页面。
- 日志、Token、耗时、成本统计。
- 标准 CO2RR-RAG-Bench 数据集和一键评测工作流。
- 部署说明和可复现实验演示流程。
- 深度单篇精读解释 pipeline。
- OpenScholar 级别的 posthoc citation attribution。
- 完整的 self-feedback 修订生成闭环。
- 默认可用的 cross-encoder reranker 运行环境。
- 外部 metadata 联网增强的产品化流程。
- README 主项目说明。
- `.env.example`、`docker-compose.yml`、`pyproject.toml` 未在当前仓库根目录发现。

## 10. 待确认

- 真实 PDF 文献库、ChromaDB、BM25、parent store 是否已在本机存在并可正常查询。
- `.env` 是否已配置 LLM 和 Embedding 通道；代码要求 LLM、Embedding 都必须配置，否则 UI 会停止或索引失败。
- V1 结构化抽取在真实 CO2RR 文献上的准确率和 evidence 校验通过率。
- V2 文献综合在真实索引和真实 LLM 下是否能稳定输出合法 JSON。
- 当前分支策略是否符合 constitution 要求：开发应避免直接在 `main` 上进行功能改动。
- `.agents/skills/rag-project-context/` 当前为未跟踪文件，是否是用户期望保留的本地 skill 目录。

## 11. 当前主要风险

- 当前环境没有安装 pytest，无法在本次上下文更新中验证测试通过情况。
- 根目录缺少 README，降低新开发者启动和配置效率。
- `config.yaml` 中存在空 API Key 字段，真实密钥应只放 `.env` 或环境变量。
- V2 pipeline 已接入 UI，但真实端到端依赖 LLM、Embedding、ChromaDB 和本地文献库，失败点较多。
- Reranker 启用需要 `sentence-transformers`，但依赖文件未列出该包。
- `__pycache__` 文件大量存在于仓库目录，应确认是否被 git ignore；不应作为业务资产。

## 12. 当前文档和代码依据

本文件基于以下文件和目录审计生成：

- `AGENTS.md`
- `.specify/memory/constitution.md`
- `CO2RR_RAG_Agent_PRD.md`
- `CO2RR_RAG_Agent_PRD_V2.md`
- `CO2RR_RAG_Agent_PRD_V3.md`
- `TDD.md`
- `CO2RR_RAG_Agent_TDD_V2.md`
- `CO2RR_RAG_Agent_DEV_PLAN_V2.md`
- `config.yaml`
- `requirements.txt`
- `app/`
- `ui/`
- `tests/`

