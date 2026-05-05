# CO2RR-LocalScholar V2 开发实施计划

## 0. 开发原则

- V2 只做增量开发，不重写 V1。
- 每次只实现一个小闭环。
- 每个新增模块必须有测试。
- 每次修改后必须运行 V1 回归测试。
- P0 阶段不启用外部 metadata。
- P0 阶段不强制依赖 reranker 模型下载。
- 不允许一次性实现整个 V2。
- 不允许删除 V1 现有模块。
- 不允许重构无关代码。
- V2 新能力优先放在新文件中；确需改 V1 文件时，只增加兼容入口，不改变 V1 默认行为。
- 所有阶段都必须能单独提交、单独测试、单独回滚。

## 1. 当前代码库审计

### 当前项目结构摘要

`app/` 下已有文件：

- `app/__init__.py`
- `app/chunker.py`
- `app/extractor.py`
- `app/generator.py`
- `app/indexer.py`
- `app/ingest.py`
- `app/llm_client.py`
- `app/retriever.py`
- `app/verifier.py`
- `app/__pycache__/...`：运行生成缓存，不作为业务代码规划对象。

`tests/` 下已有文件：

- `tests/test_acceptance.py`
- `tests/__pycache__/...`：运行生成缓存，不作为测试源码规划对象。

`config.yaml`：存在。

当前主入口：

- UI 主入口是 `ui/streamlit_app.py`。
- 当前没有独立 CLI 主入口。
- 当前 V1 查询主流程在 `ui/streamlit_app.py` 中串联：
  `hybrid_retrieve` -> `detect_query_type` / V1 extractor -> `verify_batch` -> `generate_markdown_output` -> `save_output`。

V1 模块存在情况：

- `ingest`：存在，`app/ingest.py`。
- `chunker`：存在，`app/chunker.py`。
- `indexer`：存在，`app/indexer.py`。
- `retriever`：存在，`app/retriever.py`。
- `extractor`：存在，`app/extractor.py`。
- `verifier`：存在，`app/verifier.py`。
- `generator`：存在，`app/generator.py`。
- `llm_client`：存在，`app/llm_client.py`。

当前 UI 文件存在情况：

- `ui/streamlit_app.py`：存在。
- `ui/styles.css`：存在。

### TDD 要求与当前代码库差距表

| TDD 模块 | 当前是否存在 | 新增 / 修改 | 风险等级 | 备注 |
|---|---|---|---|---|
| V1 ingest | 是 | 不修改 | 低 | P0-P2 不应触碰，作为 V1 保护对象。 |
| V1 chunker | 是 | 不修改 | 低 | 父子 chunk 已存在，V2 复用 metadata。 |
| V1 indexer / LiteratureIndex | 是 | 原则不修改 | 中 | V2 candidate retrieval 需要读取 `vector_search`、`bm25_search`、`get_chunk_by_id`、`get_parent`；如接口不够，优先在 `retriever.py` 适配。 |
| V1 retriever / `hybrid_retrieve` | 是 | 修改 | 中 | 仅允许新增 `hybrid_retrieve_candidates` 或可选参数，不改变 `hybrid_retrieve` 默认返回。 |
| V1 extractor | 是 | 不修改 | 低 | 结构化抽取模式继续走 V1。 |
| V1 verifier / evidence verifier | 是 | 不修改 | 低 | V2 claim verifier 必须新建，不能替代 V1 evidence verifier。 |
| V1 generator | 是 | 不修改或仅复用 `save_output` | 低 | V2 Markdown 放入 `report_v2.py`，不改变 V1 表格输出。 |
| V1 llm_client | 是 | 原则不修改 | 中 | P0 可直接复用 `LLMClient.chat(json_mode=True)`；只有明确缺口时才新增兼容方法。 |
| `schemas_v2.py` | 否 | 新增 | 低 | 定义 `CandidateChunk`、`SourceCitation`、`ClaimRecord`、`SynthesisResult` 等 Pydantic schema。 |
| `report_v2.py` | 否 | 新增 | 低 | 负责七段式中文 Markdown 渲染和 V2 保存命名。 |
| `context_builder.py` | 否 | 新增 | 中 | 负责 `[S1]` 引用编号、metadata-aware context、token budget。 |
| `reranker.py` | 否 | 新增 | 中 | P0 不强制下载模型；必须支持关闭和降级为 RRF。 |
| `synthesizer.py` | 否 | 新增 | 高 | 依赖 LLM JSON 稳定性；P0 必须测试解析失败和空证据路径。 |
| `claim_verifier.py` | 否 | 新增 | 高 | 从 evidence substring 校验升级到 claim-evidence 支持判定，需保守规则和测试。 |
| `query_router.py` | 否 | 新增 | 中 | 后续接入 UI；不能影响 V1 默认结构化抽取。 |
| `feedback.py` | 否 | 新增 | 高 | P1 实现，P0 不做复杂 self-feedback。 |
| `followup_retriever.py` | 否 | 新增 | 高 | P1 实现，只允许本地二次检索。 |
| `eval_bench.py` | 否 | 新增 | 中 | P2 实现，小型 JSONL/CSV 评测，不进入 P0。 |
| `metadata_enricher.py` | 否 | 新增 | 高 | P3 实现，默认关闭，不作为 evidence 来源。 |
| `config.yaml` V2 配置段 | 部分，只有 V1 配置 | 修改 | 中 | 分阶段追加配置，不删除已有键；P0 可先由代码默认值兜底。 |
| Streamlit UI 模式选择 | 否 | 修改 | 高 | Phase 7 才接入，避免 P0 破坏 V1 UI。 |

## 2. 开发阶段总览

- Phase 0：审计和保护 V1
- Phase 1：P0-A schemas_v2 + report_v2
- Phase 2：P0-B context_builder
- Phase 3：P0-C hybrid_retrieve_candidates
- Phase 4：P0-D minimal synthesis pipeline
- Phase 5：P0-E minimal claim_verifier
- Phase 6：query_router 接入
- Phase 7：Streamlit UI 模式选择
- Phase 8：P1 self-feedback
- Phase 9：P1 follow-up retrieval
- Phase 10：P2 eval_bench
- Phase 11：P3 external_metadata

## 3. 每个阶段的详细任务

### Phase 0：审计和保护 V1

### 阶段目标

确认 V1 当前行为可回归测试保护，建立 V2 开发边界。不实现任何 V2 功能，不修改业务流程。

### 涉及文件

- 允许新增或修改：`CO2RR_RAG_Agent_DEV_PLAN_V2.md`
- 允许只读：`app/*.py`、`ui/streamlit_app.py`、`tests/test_acceptance.py`、`config.yaml`、`CO2RR_RAG_Agent_TDD_V2.md`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `ui/styles.css`
- `tests/test_acceptance.py`
- `config.yaml`

### 实施步骤

1. 运行 `git status --short`，记录已有未提交改动。
2. 读取 `CO2RR_RAG_Agent_TDD_V2.md`，提取 V2 模块边界。
3. 列出 `app/`、`tests/`、`ui/` 当前文件。
4. 读取 V1 主流程函数和 UI 调用链。
5. 生成本开发计划文档。
6. 不进行任何功能代码修改。

### 测试文件

- 运行：`tests/test_acceptance.py`
- 不新增测试。

### 验收标准

- `CO2RR_RAG_Agent_DEV_PLAN_V2.md` 存在。
- 文档包含当前代码库审计、差距表、阶段拆分、每阶段任务、验收命令和回滚方式。
- 除计划文档外无新增或修改文件。
- V1 回归测试可运行并通过；若因环境缺依赖失败，需记录失败原因，不得继续功能阶段。

### 验收命令

```bash
pytest tests/test_acceptance.py -v
git diff -- CO2RR_RAG_Agent_DEV_PLAN_V2.md
git status --short
```

### 回滚方式

```bash
git restore CO2RR_RAG_Agent_DEV_PLAN_V2.md
```

如果文件尚未纳入 git 跟踪：

```bash
rm CO2RR_RAG_Agent_DEV_PLAN_V2.md
```

删除文件前必须确认只删除本阶段新增的计划文档。

### Phase 1：P0-A schemas_v2 + report_v2

### 阶段目标

建立 V2 数据对象和 Markdown V2 渲染器，形成纯内存、无检索、无 LLM 的最小可测闭环。不接入 UI，不改 V1 generator。

### 涉及文件

- 新增：`app/schemas_v2.py`
- 新增：`app/report_v2.py`
- 新增：`tests/test_v2_report.py`
- 可选新增：`tests/test_v2_schemas.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `ui/styles.css`
- `tests/test_acceptance.py`
- `config.yaml`

### 实施步骤

1. 在 `schemas_v2.py` 定义 `CandidateChunk`、`SourceCitation`、`ClaimRecord`、`SynthesisResult`。
2. 为 schema 设置保守默认值，避免可变默认值共享问题。
3. 在 `report_v2.py` 实现 `generate_markdown_v2(result)`。
4. 在 `report_v2.py` 实现 V2 保存函数，文件名包含 `v2_synthesis`，输出目录默认复用 `output_dir`。
5. 编写 fixture 构造一个 `SynthesisResult`，覆盖 supported、partially_supported、unsupported。
6. 测试 Markdown 必须包含七个指定章节和 `[S1]` 证据摘录。

### 测试文件

- 新增：`tests/test_v2_report.py`
- 可选新增：`tests/test_v2_schemas.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- 可从 `app.schemas_v2` 导入四类核心 schema。
- `generate_markdown_v2` 输出包含：
  `# 查询结果`、`## 一、综合回答`、`## 二、关键结论与证据支持状态`、`## 三、结构化信息表`、`## 四、文献对比与分析`、`## 五、Agent 分析`、`## 六、不确定项`、`## 七、原文证据摘录`。
- `unsupported` claim 不进入综合回答主体。
- 保存函数能在临时目录生成包含 `v2_synthesis` 的 Markdown 文件。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_report.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/schemas_v2.py app/report_v2.py tests/test_v2_report.py tests/test_v2_schemas.py
```

如果这些文件未被 git 跟踪，删除本阶段新增文件：

```bash
rm app/schemas_v2.py app/report_v2.py tests/test_v2_report.py tests/test_v2_schemas.py
```

### Phase 2：P0-B context_builder

### 阶段目标

将已排序候选 chunk 转成带 `[S1]` 的上下文和 `SourceCitation` 列表，支持 metadata-aware context、同文献数量限制和粗略 token budget。不接入 LLM，不接入 UI。

### 涉及文件

- 新增：`app/context_builder.py`
- 修改：`app/schemas_v2.py`
- 新增：`tests/test_v2_context_builder.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `tests/test_acceptance.py`
- `config.yaml`

### 实施步骤

1. 实现 `build_retrieval_text(candidate)`，包含 title、DOI、paper、section、page、SI、text。
2. 实现 `build_v2_context(query, ranked_chunks, config)`。
3. 为进入上下文的 chunk 分配稳定 `S1`、`S2` 编号。
4. 同一 `chunk_id` 不重复分配 citation。
5. 执行 `max_chunks_per_paper` 限制。
6. 使用 `len(text) / 4` 的粗略 token 估算执行 `max_context_tokens` 截断。
7. 测试空候选、重复 chunk、预算截断、SI 标记和 metadata 输出。

### 测试文件

- 新增：`tests/test_v2_context_builder.py`
- 运行：`tests/test_v2_report.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- `build_v2_context` 返回 `(context_text, citations)`。
- `context_text` 中包含 `[S1]` 风格引用编号。
- `citations` 的 `citation_id` 与 context 中编号一致。
- 超过预算时低排序 chunk 不进入 context。
- 同一文献超过 `max_chunks_per_paper` 的 chunk 被跳过。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_context_builder.py -v
pytest tests/test_v2_report.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/context_builder.py app/schemas_v2.py tests/test_v2_context_builder.py
```

未跟踪文件使用：

```bash
rm app/context_builder.py tests/test_v2_context_builder.py
```

### Phase 3：P0-C hybrid_retrieve_candidates

### 阶段目标

在不改变 V1 `hybrid_retrieve` 默认行为的前提下，提供 V2 candidate parent chunks 接口。不实现强制 reranker 下载，不改 UI。

### 涉及文件

- 修改：`app/retriever.py`
- 修改：`app/schemas_v2.py`
- 新增：`app/reranker.py`
- 新增：`tests/test_v2_retriever_candidates.py`
- 新增：`tests/test_v2_reranker.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `tests/test_acceptance.py`

### 实施步骤

1. 在 `retriever.py` 新增 `hybrid_retrieve_candidates(query, index, llm_client, config)`。
2. 复用当前 BM25 + vector + RRF 逻辑，读取 `retrieval.candidate_top_k`。
3. 输出 `CandidateChunk` 列表，保留 `hit_child_ids`、`bm25_rank`、`vector_rank`、`rrf_score`。
4. 保证 `hybrid_retrieve` 原函数签名和默认返回不变。
5. 在 `reranker.py` 新增 `rerank_candidates`，P0 默认支持 `enabled=false` 或依赖缺失时按 RRF 顺序返回。
6. 实现 `max_chunks_per_paper` 和 `final_top_n` 的纯 Python 限制。
7. 使用 mock index 测试 child 命中扩展到 parent、同 parent 去重、V1 `hybrid_retrieve` 不受影响。

### 测试文件

- 新增：`tests/test_v2_retriever_candidates.py`
- 新增：`tests/test_v2_reranker.py`
- 运行：`tests/test_acceptance.py`

### 验收标准

- `hybrid_retrieve_candidates` 返回 `CandidateChunk` 实例或等价 Pydantic 对象列表。
- `retrieval.candidate_top_k` 生效。
- `hit_child_ids` 包含命中的 child chunk id。
- reranker 关闭、未安装或失败时不抛出模型下载错误，按 RRF 降级返回。
- `hybrid_retrieve` 原函数签名保持不变。
- `hybrid_retrieve` 原有 acceptance 测试继续通过。

### 验收命令

```bash
pytest tests/test_v2_retriever_candidates.py -v
pytest tests/test_v2_reranker.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/retriever.py app/schemas_v2.py app/reranker.py tests/test_v2_retriever_candidates.py tests/test_v2_reranker.py
```

未跟踪文件使用：

```bash
rm app/reranker.py tests/test_v2_retriever_candidates.py tests/test_v2_reranker.py
```

### Phase 4：P0-D minimal synthesis pipeline

### 阶段目标

实现最小 V2 synthesis 链路：候选检索、可降级 rerank、context builder、LLM JSON 生成、ReportV2 输出和保存。不做 self-feedback，不做复杂 claim verifier，不接 UI。

### 涉及文件

- 新增：`app/synthesizer.py`
- 新增：`app/pipeline_v2.py`
- 修改：`app/report_v2.py`
- 修改：`app/schemas_v2.py`
- 修改：`config.yaml`
- 新增：`tests/test_v2_synthesizer.py`
- 新增：`tests/test_v2_pipeline.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `tests/test_acceptance.py`

### 实施步骤

1. 在 `synthesizer.py` 实现 `synthesize_with_citations(query, context_text, citations, llm_client, config)`。
2. Prompt 要求只使用 context、每个事实 claim 带 `citation_ids`、输出 JSON。
3. 实现 JSON 解析和 Pydantic 校验，失败时返回证据不足的保守 `SynthesisResult`。
4. 在 `pipeline_v2.py` 实现 `run_synthesis_pipeline(...)`，串联已有 V2 P0 组件。
5. 在 `config.yaml` 只追加最小 V2 配置段，不删除、不重命名、不覆盖 V1 现有配置。
6. P0 配置默认值必须保持保守：`external_metadata.enabled=false`、`self_feedback.enabled=false`、`self_feedback.allow_followup_retrieval=false`、`reranker.fallback_to_rrf=true`。
7. 只使用本地 index，不发起外部 metadata 请求。
8. 自动保存到 `data/output/` 或配置的 `output_dir`。
9. 用 fake LLM 和 fake index 测试完整链路；测试不得实例化真实 `LiteratureIndex`、真实 `LLMClient`、真实 ChromaDB 或真实远程 API。

### 测试文件

- 新增：`tests/test_v2_synthesizer.py`
- 新增：`tests/test_v2_pipeline.py`
- 运行：`tests/test_v2_context_builder.py`
- 运行：`tests/test_v2_report.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- fake LLM 返回 JSON 时能生成 `SynthesisResult`。
- LLM 返回非法 JSON 时不崩溃，输出证据不足或不确定项。
- pipeline 能把 Markdown 保存到临时 output 目录。
- `config.yaml` 只追加 V2 配置，V1 既有键和值不被删除或重命名。
- P0 配置中 self-feedback、follow-up retrieval、external metadata 默认关闭。
- pipeline 单元测试只使用 fake LLM 和 fake index，不访问真实 API 或真实索引。
- P0 不触发外部 metadata 请求。
- P0 不要求下载 reranker 模型。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_synthesizer.py -v
pytest tests/test_v2_pipeline.py -v
pytest tests/test_v2_context_builder.py tests/test_v2_report.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/synthesizer.py app/pipeline_v2.py app/report_v2.py app/schemas_v2.py config.yaml tests/test_v2_synthesizer.py tests/test_v2_pipeline.py
```

未跟踪文件使用：

```bash
rm app/synthesizer.py app/pipeline_v2.py tests/test_v2_synthesizer.py tests/test_v2_pipeline.py
```

### Phase 5：P0-E minimal claim_verifier

### 阶段目标

加入最小规则版 claim-level citation verification，保证无 citation、无效 citation、明显数值不匹配的 claim 被降级。不做复杂 LLM 判别，不做 self-feedback。

### 涉及文件

- 新增：`app/claim_verifier.py`
- 修改：`app/pipeline_v2.py`
- 修改：`app/report_v2.py`
- 修改：`app/schemas_v2.py`
- 新增：`tests/test_v2_claim_verifier.py`
- 修改：`tests/test_v2_pipeline.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `tests/test_acceptance.py`

### 实施步骤

1. 实现 `verify_claims(claims, citations, llm_client, config)`。
2. 规则预检：无 citation -> `unsupported`。
3. 规则预检：citation id 不存在 -> `unsupported`。
4. 规则预检：claim 中数字、单位、电位、FE、温度、时间不在 evidence 中 -> `partially_supported` 或 `unsupported`。
5. 保留 `is_agent_analysis=True` 的 claim，但不得当作文献明确结论。
6. 在 pipeline 中于 report 前执行 verifier。
7. 测试 supported、partially_supported、unsupported 三类输出和报告过滤。

### 测试文件

- 新增：`tests/test_v2_claim_verifier.py`
- 修改运行：`tests/test_v2_pipeline.py`
- 运行：`tests/test_v2_report.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- 无 citation 的 claim 被标为 `unsupported`。
- 不存在的 citation id 被标为 `unsupported`。
- 数值证据不匹配时不标为 `supported`。
- `unsupported` claim 不进入综合回答主体。
- verifier 失败时保守降级，不让未验证 claim 进入主结论。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_claim_verifier.py -v
pytest tests/test_v2_pipeline.py tests/test_v2_report.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/claim_verifier.py app/pipeline_v2.py app/report_v2.py app/schemas_v2.py tests/test_v2_claim_verifier.py tests/test_v2_pipeline.py
```

未跟踪文件使用：

```bash
rm app/claim_verifier.py tests/test_v2_claim_verifier.py
```

### Phase 6：query_router 接入

### 阶段目标

新增路由模块，让调用方可以在结构化抽取、文献综合、精读解释之间选择模式。不修改 UI，不改变 V1 默认结构化抽取路径。

### 涉及文件

- 新增：`app/query_router.py`
- 修改：`app/pipeline_v2.py`
- 新增：`tests/test_v2_router.py`
- 可选修改：`config.yaml`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `tests/test_acceptance.py`

### 实施步骤

1. 定义 `QueryMode`：`structured_extraction`、`synthesis`、`deep_reading`。
2. 实现 `detect_query_mode(query, explicit_mode=None, config=None)`。
3. 显式模式优先于自动规则。
4. 自动规则按 TDD 关键词区分结构化抽取、综合、精读。
5. `deep_reading` 在本阶段可返回未实现占位结果或复用 synthesis 的保守路径，但必须明确不影响 V1。
6. 测试中文和英文关键词路由。
7. 如改 `config.yaml`，只追加 `v2.default_mode`，不删除原配置。

### 测试文件

- 新增：`tests/test_v2_router.py`
- 运行：`tests/test_v2_pipeline.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- 显式选择 `structured_extraction` 时不进入 V2 pipeline。
- 显式选择 `synthesis` 时进入 V2 pipeline。
- 自动模式对“总结/对比/综合”返回 synthesis。
- 自动模式对“合成方法/测试条件/FE/表格/提取”返回 structured_extraction。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_router.py -v
pytest tests/test_v2_pipeline.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/query_router.py app/pipeline_v2.py tests/test_v2_router.py config.yaml
```

未跟踪文件使用：

```bash
rm app/query_router.py tests/test_v2_router.py
```

### Phase 7：Streamlit UI 模式选择

### 阶段目标

在 UI 中增加最小模式选择和 V2 查询状态，但保留 V1 原查询体验。用户未启用 V2 时，UI 行为应与当前 V1 一致。本阶段不做 UI 大改，不做高级设置面板的完整实现。

### 涉及文件

- 修改：`ui/streamlit_app.py`
- 可选修改：`config.yaml`
- 可选新增：`tests/test_v2_ui_mode.py`；如无 UI 测试框架，则只运行路由和 pipeline 测试

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/styles.css`
- `tests/test_acceptance.py`

### 实施步骤

1. 在 sidebar 或查询区新增最小查询模式选择：自动、结构化抽取、文献综合、精读解释。
2. 只读取既有配置中的 V2 开关；不在本阶段实现完整高级设置折叠区。
3. 当选择结构化抽取时，继续执行当前 V1 `[1/4]` 流程。
4. 当选择文献综合时，调用 `run_synthesis_pipeline`。
5. V2 状态显示使用 TDD 的 `[1/7]` 到 `[7/7]` 文案；P0 未实现的 self-feedback 显示“已跳过”。
6. `v2.mode_enabled=false` 时隐藏 V2 模式。
7. 高级设置面板、复杂样式调整和 UI 布局重构推迟到后续单独 Phase。
8. 手动检查 Streamlit 启动和基本查询页面不报错。

### 测试文件

- 运行：`tests/test_v2_router.py`
- 运行：`tests/test_v2_pipeline.py`
- 回归：`tests/test_acceptance.py`
- 可选新增：`tests/test_v2_ui_mode.py`

### 验收标准

- UI 能显示模式选择。
- 默认或结构化抽取模式仍走 V1 流程。
- 文献综合模式能调用 V2 pipeline 并显示 V2 Markdown。
- 本阶段不新增完整 V2 高级设置面板。
- 不修改 `ui/styles.css`。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_router.py tests/test_v2_pipeline.py -v
pytest tests/test_acceptance.py -v
streamlit run ui/streamlit_app.py
```

### 回滚方式

```bash
git restore ui/streamlit_app.py config.yaml tests/test_v2_ui_mode.py
```

未跟踪文件使用：

```bash
rm tests/test_v2_ui_mode.py
```

### Phase 8：P1 self-feedback

### 阶段目标

实现一轮自反馈检查，识别 unsupported claims、missing aspects、citation mismatch 和 mixed paper conditions。不做 follow-up retrieval。

### 涉及文件

- 新增：`app/feedback.py`
- 修改：`app/schemas_v2.py`
- 修改：`app/pipeline_v2.py`
- 修改：`app/report_v2.py`
- 新增：`tests/test_v2_feedback.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `tests/test_acceptance.py`

### 实施步骤

1. 定义 `FeedbackRecord` schema。
2. 实现 feedback prompt，输入 draft、claims、citations。
3. 限制 `self_feedback.max_iterations=1`。
4. 解析失败时返回空 feedback，不中断主流程。
5. 将 feedback 写入 `feedback_trace`。
6. 根据 feedback 做最小修订提示或标记，不自动删除已 supported claim。
7. 使用 fake LLM 测试 feedback JSON 和解析失败。

### 测试文件

- 新增：`tests/test_v2_feedback.py`
- 运行：`tests/test_v2_pipeline.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- 能解析 feedback JSON。
- `max_iterations=1` 生效。
- feedback 失败不影响 P0 最小闭环输出。
- `feedback_trace` 出现在 `SynthesisResult` 或保存 trace 中。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_feedback.py -v
pytest tests/test_v2_pipeline.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/feedback.py app/schemas_v2.py app/pipeline_v2.py app/report_v2.py tests/test_v2_feedback.py
```

未跟踪文件使用：

```bash
rm app/feedback.py tests/test_v2_feedback.py
```

### Phase 9：P1 follow-up retrieval

### 阶段目标

基于 feedback 的证据缺口执行本地二次检索，合并候选并重新构建 context。不联网，不使用外部 metadata。

### 涉及文件

- 新增：`app/followup_retriever.py`
- 修改：`app/pipeline_v2.py`
- 修改：`app/context_builder.py`
- 新增：`tests/test_v2_followup_retriever.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `tests/test_acceptance.py`
- `ui/streamlit_app.py`，除非 Phase 7 已完成且本阶段仅更新状态文案。

### 实施步骤

1. 实现 `run_followup_retrieval(feedback, index, llm_client, config)`。
2. 每条 follow-up query 复用 `hybrid_retrieve_candidates` 和 `rerank_candidates`。
3. 去重已在上下文中的 chunk。
4. 限制 `max_followup_queries`。
5. 合并后重新执行 context budget。
6. 在 pipeline 中仅当 `need_followup_retrieval=true` 且配置允许时触发。
7. 用 fake index 测试去重、最大查询数和不联网约束。

### 测试文件

- 新增：`tests/test_v2_followup_retriever.py`
- 运行：`tests/test_v2_feedback.py`
- 运行：`tests/test_v2_pipeline.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- follow-up retrieval 只使用本地 index。
- 重复 chunk 不重复进入 context。
- `max_followup_queries` 生效。
- 关闭 `allow_followup_retrieval` 时不触发二次检索。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_followup_retriever.py -v
pytest tests/test_v2_feedback.py tests/test_v2_pipeline.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/followup_retriever.py app/pipeline_v2.py app/context_builder.py tests/test_v2_followup_retriever.py
```

未跟踪文件使用：

```bash
rm app/followup_retriever.py tests/test_v2_followup_retriever.py
```

### Phase 10：P2 eval_bench

### 阶段目标

建立小型 CO2RR-RAG-Bench 评测入口，用 fixture 或 JSONL gold data 评估检索命中和引用支持。不做高级评测面板。

### 涉及文件

- 新增：`app/eval_bench.py`
- 新增：`tests/test_v2_eval_bench.py`
- 可选新增：`data/eval/co2rr_rag_bench_sample.jsonl`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`
- `tests/test_acceptance.py`

### 实施步骤

1. 定义 JSONL 样例格式：question、mode、gold_evidence、expected_answer_points。
2. 实现加载 eval data 的纯函数。
3. 实现 Recall@K、Evidence Hit Rate 的可测试计算。
4. 实现 Unsupported Claim Rate 的统计函数。
5. 不调用真实 LLM，不依赖真实 ChromaDB。
6. 用小 fixture 测试指标边界。

### 测试文件

- 新增：`tests/test_v2_eval_bench.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- 能读取 JSONL 样例。
- 能计算至少 Recall@K、Evidence Hit Rate、Unsupported Claim Rate。
- 空输入和无命中输入不崩溃。
- 不需要启动 UI 或调用外部 API。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_eval_bench.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/eval_bench.py tests/test_v2_eval_bench.py data/eval/co2rr_rag_bench_sample.jsonl
```

未跟踪文件使用：

```bash
rm app/eval_bench.py tests/test_v2_eval_bench.py data/eval/co2rr_rag_bench_sample.jsonl
```

### Phase 11：P3 external_metadata

### 阶段目标

实现可选外部 metadata 增强，只补充标题、作者、年份、期刊、摘要、引用数等元数据。默认关闭；不下载外部全文；不把外部摘要作为本地 evidence。

### 涉及文件

- 新增：`app/metadata_enricher.py`
- 修改：`app/context_builder.py`
- 修改：`config.yaml`
- 新增：`tests/test_v2_metadata_enricher.py`

### 禁止修改文件

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `tests/test_acceptance.py`
- `ui/streamlit_app.py`，除非只增加明确关闭状态提示。

### 实施步骤

1. 在 `config.yaml` 中确认 `external_metadata.enabled=false` 默认关闭。
2. 实现 cache key：`doi:{doi}` 或 `title:{normalized_title}`。
3. 实现 Crossref / Semantic Scholar metadata 客户端的可 mock 接口。
4. 严禁上传本地全文；请求参数只允许 DOI 或 title。
5. metadata 只补充缺失字段，不覆盖本地 DOI 或标题。
6. `context_builder` 可在 retrieval_text 中展示 metadata，但 report evidence 仍只引用本地 chunk。
7. 用 mock HTTP 测试缓存、默认关闭、不覆盖本地字段。

### 测试文件

- 新增：`tests/test_v2_metadata_enricher.py`
- 运行：`tests/test_v2_context_builder.py`
- 回归：`tests/test_acceptance.py`

### 验收标准

- 默认配置下不发起任何外部请求。
- 开启后只用 DOI 或 title 查询 metadata。
- 不下载全文。
- 不把外部摘要写入 `SourceCitation.evidence_text`。
- metadata cache 可读写。
- V1 回归测试通过。

### 验收命令

```bash
pytest tests/test_v2_metadata_enricher.py -v
pytest tests/test_v2_context_builder.py -v
pytest tests/test_acceptance.py -v
```

### 回滚方式

```bash
git restore app/metadata_enricher.py app/context_builder.py config.yaml tests/test_v2_metadata_enricher.py
```

未跟踪文件使用：

```bash
rm app/metadata_enricher.py tests/test_v2_metadata_enricher.py
```

## 4. Codex 执行规则

- Codex 每次只能执行一个 Phase。
- 每次开始前必须说明计划。
- 每次修改前必须检查 git status。
- 每次修改后必须显示 git diff 摘要。
- 每次修改后必须运行对应 pytest。
- 测试失败时不得继续下一个 Phase。
- 不允许一次性修改超过 5 个业务文件。
- 不允许删除文件，除非我明确确认。
- 不允许修改无关 UI / 样式 / 配置。
- 不允许一次性实现整个 V2。
- 不允许删除 V1 现有模块。
- 不允许重构无关代码。
- P0 阶段不启用外部 metadata。
- P0 阶段不强制依赖 reranker 模型下载。
- P0 阶段允许追加最小 V2 配置，但必须保持 self-feedback、follow-up retrieval、external metadata 默认关闭。
- 如果需要修改 V1 文件，必须说明为什么无法通过新增 V2 文件完成，并保证 V1 默认行为不变。
- 每个 Phase 完成后必须汇报：修改文件、测试命令、测试结果、未解决风险。

## 5. 推荐提交粒度

每个 Phase 一个 commit。

推荐提交信息：

- `chore: add V2 implementation plan`
- `feat: add V2 schemas and report renderer`
- `feat: add V2 context builder`
- `feat: add V2 retriever candidate interface`
- `feat: add minimal V2 synthesis pipeline`
- `feat: add minimal claim verifier`
- `feat: add V2 query router`
- `feat: add Streamlit mode selection for V2`
- `feat: add V2 self feedback`
- `feat: add V2 follow-up retrieval`
- `test: add CO2RR RAG eval bench`
- `feat: add optional external metadata enrichment`

## 6. 最小可用闭环定义

P0 最小可用闭环必须是：

本地检索
-> 构建带 `[S1]` 的上下文
-> LLM 生成带 `citation_ids` 的 JSON
-> `claim_verifier` 做最小规则校验
-> `report_v2` 输出中文 Markdown
-> 自动保存到 `data/output/`

P0 的具体边界：

- 检索只使用本地 ChromaDB + BM25 + RRF。
- reranker 可存在接口，但必须允许关闭或失败降级。
- P0 可追加最小 V2 配置；配置必须保守，且不得删除或重命名 V1 既有配置。
- P0 中 `self_feedback.enabled=false`、`self_feedback.allow_followup_retrieval=false`、`external_metadata.enabled=false`。
- context 中的 citation id 只在本次回答内有效。
- LLM 输出必须经过 JSON 解析和 schema 校验。
- claim verifier 至少处理无 citation、无效 citation、明显数字证据不匹配。
- unsupported claim 不得进入综合回答主体。
- 输出报告必须包含七个 V2 指定章节。
- 自动保存路径默认使用 `config.yaml` 的 `output_dir`，当前为 `./data/output`。

## 7. 推迟到后续阶段的功能

以下功能推迟，不放进 P0：

- 外部 Semantic Scholar / Crossref metadata。
- 自训练 retriever。
- OpenScholar-8B。
- 多轮对话。
- 复杂 self-feedback。
- 自动联网检索全文。
- 高级评测面板。
- 外部摘要作为 evidence。
- 自动下载或训练 reranker 模型。
- V1/V2 大规模 UI 重构。
- 基于真实远程 API 的端到端测试。
