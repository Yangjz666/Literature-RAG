# Implementation Plan：Feature 002 检索调试 Debug Trace

## 1. Feature 基本信息

- Feature 编号：002
- Feature 名称：检索调试 Debug Trace
- Feature 目录：`specs/002-retrieval-debug-trace/`
- Spec 文件：`specs/002-retrieval-debug-trace/spec.md`
- 开发基线分支：`V3-DEV`
- 功能分支：`feature/002-retrieval-debug-trace`
- 当前阶段：plan refined after review
- 后续流程：如无新增澄清问题，tasks → analyze → implement；如 tasks 前发现需求冲突，返回 clarify

## 2. 技术目标

本功能目标是在不重写现有 RAG 主流程的前提下，为每次 RAG 查询生成可展示的 `debug_trace`，并在 Streamlit 页面中提供可展开的「检索调试 Debug Trace」面板。

完成后，用户可以看到：

1. 原始问题；
2. 改写后问题；
3. BM25 检索结果；
4. 向量检索结果；
5. RRF 融合结果，如当前项目支持；
6. reranker 排序结果，如当前项目支持；
7. final context chunks；
8. 最终回答使用的 citation / evidence；
9. 查询耗时；
10. warning / error / failed_stage。

本阶段只做 Debug Trace MVP 和基础证据追溯。citation 只做 citation/evidence 到 final context chunk 的基础映射、`matched` / `unmatched` / `not_available` 标记和来源展示，不做真假判断、claim-level verification 或完整 citation verification。

## 3. 不做范围

本 Feature 不实现以下内容：

1. 不做完整 citation verification；
2. 不做 claim-level citation verification；
3. 不做自动判断回答真假；
4. 不引入 FastAPI；
5. 不引入 Docker；
6. 不引入数据库；
7. 不做多用户系统；
8. 不联网下载文献；
9. 不做 GraphRAG；
10. 不重写现有检索架构；
11. 不重写 V1 / V2 主流程；
12. 不改变 ChromaDB、BM25、parent store 的现有存储格式。

## 4. 当前项目结构理解

当前项目已有核心结构大致如下：

```text
app/
  retriever.py
  reranker.py
  context_builder.py
  synthesizer.py
  pipeline_v2.py
  query_router.py
  indexer.py
  document_library.py
  index_status.py
  parse_report.py

ui/
  streamlit_app.py

tests/
  test_*.py

specs/
  001-library-index-transparency/
  002-retrieval-debug-trace/
```

本 Feature 应优先复用现有模块，只新增 Debug Trace 的旁路记录能力，不改变已有主流程返回格式，除非通过兼容字段扩展实现。

## 5. 总体技术方案

采用“旁路记录 + UI 展示”的方案。

核心思路：

1. 新增 `app/debug_trace.py`，定义 Debug Trace 数据结构和工具函数；
2. 在现有 RAG 查询流程中，以可选方式收集中间结果；
3. 对缺失阶段统一使用 `not_available`；
4. 查询失败时记录 `failed_stage` 和用户可读错误；
5. Streamlit 使用 `st.expander` 展示 Debug Trace；
6. 默认将 trace 保存在 `st.session_state`，不落盘；
7. 如后续 Feature 需要落盘，只允许保存到 `data/debug_traces/`，必须加入 `.gitignore`，并确保不提交 Git。

兼容性原则：

1. 不改变 `hybrid_retrieve()`、`hybrid_retrieve_candidates()`、`run_synthesis_pipeline()` 等现有调用方默认返回值；
2. 如需收集中间结果，优先使用可选 `debug_trace` / `trace_recorder` 参数、轻量 callback 或在 V2 `SynthesisResult.metadata` 中挂载 `debug_trace`，默认参数为 `None`；
3. 旧调用方不传 trace 参数时行为必须与当前版本一致；
4. trace 记录逻辑失败时只写入 warning 或忽略，不得中断原有查询；
5. Streamlit 页面只读取当前查询生成的 trace，不从旧 session trace 推断本轮结果。

## 6. 预计新增文件

```text
app/debug_trace.py
tests/test_debug_trace.py
docs/retrieval_debug.md
specs/002-retrieval-debug-trace/PROGRESS.md
```

## 7. 预计修改文件

```text
ui/streamlit_app.py
app/retriever.py
app/context_builder.py
app/pipeline_v2.py
app/synthesizer.py
CURRENT_TASK.md
README.md
.gitignore（仅后续明确启用 `data/debug_traces/` 落盘时）
```

说明：

* `app/debug_trace.py`：新增 trace 数据结构和 helper；
* `ui/streamlit_app.py`：新增 Debug Trace 展示面板；
* `app/retriever.py`：尽量记录 BM25 / vector / fusion / reranker 阶段结果；
* `app/context_builder.py`：记录 final context chunks；
* `app/pipeline_v2.py`：如当前查询入口经过该模块，则在此汇总 trace；
* `app/synthesizer.py`：如可获取最终回答和 citation，则补充到 trace；
* `CURRENT_TASK.md`：更新当前 Feature 进度；
* `README.md` / `docs/retrieval_debug.md`：补充使用说明；
* `.gitignore`：本阶段默认不落盘；仅当后续明确启用 `data/debug_traces/` 时才修改，并必须加入忽略规则。

## 8. Debug Trace 数据结构设计

新增 `DebugTrace` 数据结构，建议使用 `dataclass` 或普通 dict。

字段如下：

```python
DebugTrace = {
    "trace_id": str,
    "created_at": str,
    "user_query": str,
    "original_query": str,
    "rewritten_query": str | list[str] | "not_available",
    "query_mode": str,
    "bm25_results": list[TraceChunk] | "not_available",
    "vector_results": list[TraceChunk] | "not_available",
    "rrf_results": list[TraceChunk] | "not_available",
    "reranker_results": list[TraceChunk] | "not_available",
    "final_context_chunks": list[TraceChunk],
    "final_answer": str | None,
    "citations_used": list[TraceCitation],
    "elapsed_ms": int | None,
    "warning": list[str],
    "error": str | None,
    "failed_stage": str | None,
}
```

## 9. TraceChunk 数据结构

每个检索结果 chunk 统一转换为 `TraceChunk`。

```python
TraceChunk = {
    "document_id": str | None,
    "filename": str | None,
    "page": int | None,
    "section": str | None,
    "chunk_id": str | None,
    "parent_chunk_id": str | None,
    "score": float | None,
    "source_stage": str,
    "text_preview": str,
}
```

`source_stage` 可选值：

```text
bm25
vector
rrf
reranker
final_context
not_available
```

`text_preview` 截断长度建议：

```text
300–500 字符
```

避免 UI 展示过长全文。

## 10. TraceCitation 数据结构

基础 citation / evidence 追溯结构如下：

```python
TraceCitation = {
    "citation_id": str | None,
    "document_id": str | None,
    "filename": str | None,
    "page": int | None,
    "section": str | None,
    "chunk_id": str | None,
    "evidence_text_preview": str,
    "matched_final_context": bool,
    "match_status": "matched" | "unmatched" | "not_available",
}
```

本阶段只做 citation/evidence 到 final context chunk 的映射，不判断 claim 是否被证据充分支持，不声称 citation 已通过完整验证。无法匹配到 final context chunk 时必须标记 `unmatched`，不得伪造匹配关系。

## 11. 核心模块设计

### 11.1 `app/debug_trace.py`

负责：

1. 创建空 trace；
2. 标准化 chunk；
3. 标准化 citation；
4. 标记阶段 not_available；
5. 记录 warning；
6. 记录 error 和 failed_stage；
7. 截断 text_preview；
8. 将 trace 转为 JSON-safe dict。

建议函数：

```python
create_debug_trace(user_query: str, query_mode: str | None = None) -> dict

normalize_trace_chunk(raw_chunk: Any, source_stage: str) -> dict

normalize_trace_chunks(raw_chunks: list[Any], source_stage: str) -> list[dict]

mark_stage_not_available(trace: dict, stage: str, reason: str | None = None) -> None

record_stage_results(trace: dict, stage: str, results: list[Any]) -> None

record_final_context(trace: dict, chunks: list[Any]) -> None

record_final_answer(trace: dict, answer: str) -> None

record_citations(trace: dict, citations: list[Any]) -> None

record_error(trace: dict, failed_stage: str, error: Exception | str) -> None

to_json_safe(trace: dict) -> dict
```

### 11.2 检索流程集成

在现有查询流程中尽量记录以下阶段：

1. 查询开始时创建 trace；
2. query rewrite 后记录 rewritten_query；
3. BM25 检索后记录 bm25_results；
4. vector search 后记录 vector_results；
5. RRF 融合后记录 rrf_results；
6. reranker 后记录 reranker_results；
7. context builder 后记录 final_context_chunks；
8. LLM 生成后记录 final_answer；
9. citation 解析后记录 citations_used；
10. 异常时记录 failed_stage 和 error。

如果当前项目没有某阶段，不新增复杂架构，只标记：

```text
not_available
```

### 11.2.1 兼容现有函数返回的接入方式

本 Feature 不改变现有主流程函数的默认返回契约：

1. `hybrid_retrieve(query, index, llm_client, config)` 默认仍返回 `list[dict]`；
2. `hybrid_retrieve_candidates(query, index, llm_client, config)` 默认仍返回 `list[CandidateChunk]`；
3. `run_synthesis_pipeline(query, index, llm_client, config)` 默认仍返回 `SynthesisResult`；
4. `build_v2_context()`、`synthesize_with_citations()` 等函数默认返回值不因 Debug Trace 改变。

实现时优先采用以下兼容扩展方式之一：

1. 为检索、rerank、context、synthesis 函数增加默认值为 `None` 的可选 trace 参数，例如 `debug_trace: dict | None = None`；
2. 或增加默认值为 `None` 的轻量 trace callback / recorder，用于记录阶段结果；
3. 对 V2 synthesis 路径，可将最终 trace 放入 `SynthesisResult.metadata["debug_trace"]`，但不得替换现有 metadata 字段；
4. 对结构化抽取路径，可由 Streamlit 查询入口创建本轮 trace，并在调用 `hybrid_retrieve()`、抽取、证据校验和最终回答生成后逐步补充；
5. 对未能直接暴露的内部阶段，只记录已能安全获取的数据，其余阶段显示 `not_available`。

tasks 阶段必须分别覆盖：

1. 结构化抽取查询路径的 Debug Trace；
2. V2 synthesis 查询路径的 Debug Trace；
3. 查询失败路径的 partial trace；
4. 旧调用方不传 trace 参数时的兼容性。

### 11.3 Streamlit UI 展示

在 `ui/streamlit_app.py` 的回答区域下方新增：

```text
st.expander("检索调试 Debug Trace", expanded=False)
```

展示内容：

1. trace 基本信息；
2. query 信息；
3. 各阶段检索结果；
4. final context chunks；
5. citation / evidence；
6. warning / error；
7. 原始 JSON。

建议 UI 结构：

```text
检索调试 Debug Trace
  - 查询信息
  - BM25 结果
  - 向量检索结果
  - RRF 融合结果
  - Reranker 结果
  - Final Context Chunks
  - Citation / Evidence
  - Raw JSON
```

每个阶段用 `st.dataframe` 或 `st.table` 展示，不要只堆 JSON。

## 12. 失败处理策略

Debug Trace 不能反向破坏主查询流程。

原则：

1. trace 记录失败，不应导致 RAG 查询失败；
2. 查询失败时，尽量保留已经产生的阶段结果；
3. 对用户显示用户可读错误；
4. 原始异常可放入 debug trace，但不要直接把完整 traceback 展示给普通用户；
5. 缺失阶段统一显示 `not_available`。

失败阶段枚举：

```text
query_rewrite_failed
bm25_failed
vector_search_failed
rrf_failed
reranker_failed
context_builder_failed
llm_failed
citation_parse_failed
unknown_failed
```

## 13. 持久化策略

默认策略：

```text
只存在 Streamlit session_state 中。
```

原因：

1. MVP 阶段简单；
2. 不引入数据库；
3. 避免产生大量本地运行产物；
4. 避免 Git 提交风险。

可选策略：

```text
data/debug_traces/
```

如果实现落盘，必须：

1. 写入 `.gitignore`；
2. 文档说明这是本地运行产物；
3. 不提交任何 trace JSON；
4. 不记录 API Key 或敏感环境变量。

本阶段默认优先使用 Streamlit `st.session_state`，不落盘，不新增数据库，不新增长期审计存储。

## 14. 测试方案

### 14.1 单元测试

新增：

```text
tests/test_debug_trace.py
```

测试内容：

1. `create_debug_trace` 能生成基础结构；
2. 缺失阶段能标记为 `not_available`；
3. raw chunk 能标准化为 `TraceChunk`；
4. text_preview 能正确截断；
5. error 能记录 failed_stage；
6. citation 能根据 chunk_id 标记 matched / unmatched；
7. trace 能转为 JSON-safe dict。

### 14.2 集成测试

根据现有项目测试结构，补充或复用：

```text
tests/test_v2_pipeline.py
tests/test_v2_retriever_candidates.py
tests/test_v2_context_builder.py
tests/test_v2_synthesizer.py
```

测试内容：

1. mock 检索结果可以进入 trace；
2. final_context_chunks 可以进入 trace；
3. 某阶段为空时不崩溃；
4. trace 不影响原有 answer 输出；
5. V2 synthesis 路径可以在 `SynthesisResult.metadata` 或等价兼容位置取得本轮 trace；
6. 旧调用方不传 trace 参数时，现有返回值和测试仍通过；
7. 原有 V1 / V2 流程测试仍通过。

### 14.3 UI 数据测试

如果 Streamlit 渲染不方便直接测，可抽出 UI helper：

```python
prepare_debug_trace_table(trace: dict, stage: str) -> list[dict]
```

测试：

1. 空阶段显示 not_available；
2. chunk 表格字段完整；
3. citation 表格字段完整；
4. 原始 JSON 可序列化；
5. 连续两次查询时，页面只展示当前查询 trace，不混淆上一轮 trace；
6. 当前页面没有本轮 trace 时，不展示上一轮 trace 作为本轮结果。

## 15. 测试命令

实现完成后至少运行：

```bash
.venv/bin/python -m py_compile app/debug_trace.py ui/streamlit_app.py
```

```bash
.venv/bin/python -m pytest tests/test_debug_trace.py -q
```

```bash
.venv/bin/python -m pytest
```

如修改 Streamlit 页面：

```bash
.venv/bin/python -m streamlit run ui/streamlit_app.py
```

手动检查：

1. 文献查询入口正常；
2. 提问后能看到回答；
3. 回答下方有 Debug Trace 面板；
4. 展开面板能看到检索阶段结果；
5. 缺失阶段显示 not_available；
6. V2 文献综合路径完成后能看到本轮 Debug Trace；
7. 连续执行两次不同查询时，Debug Trace 中的 original_query、trace_id 和阶段结果对应当前查询；
8. 原有文献库管理页面正常。

## 16. 验收标准

本 Feature 完成后应满足：

1. 用户完成一次 RAG 查询后，可以看到「检索调试 Debug Trace」展开面板；
2. 面板中能看到 original query；
3. 面板中能看到 rewritten query，缺失时显示 not_available；
4. 面板中能看到 BM25 检索结果，缺失时显示 not_available；
5. 面板中能看到向量检索结果，缺失时显示 not_available；
6. 面板中能看到 RRF / reranker 结果，缺失时显示 not_available；
7. 面板中能看到 final context chunks；
8. 每个 chunk 至少展示 filename、page、section、chunk_id、score、text_preview；
9. 能看到最终回答使用的 citation / evidence；
10. citation 无法匹配时标记 unmatched，且不声称已完成真假判断、claim-level verification 或完整 citation verification；
11. 查询失败时能显示 failed_stage 和 error；
12. Debug Trace 记录失败不影响正常查询；
13. 结构化抽取路径和 V2 synthesis 路径都能生成本轮 trace；
14. 连续两次查询时，页面只展示当前查询的 trace，不混淆上一轮 trace；
15. 原有文献查询入口仍然可用；
16. Feature 001 文献库管理页面仍然可用；
17. 相关 pytest 通过；
18. Streamlit 能正常启动；
19. CURRENT_TASK.md 和 specs/002-retrieval-debug-trace/PROGRESS.md 被更新。

## 17. 风险与应对

### 风险 1：现有 RAG 流程中间结果没有统一返回

应对：

* 不强行重写主流程；
* 能记录多少记录多少；
* 缺失阶段显示 not_available；
* 后续 Feature 再逐步增强。

### 风险 2：不同模块 chunk 数据格式不一致

应对：

* 在 `app/debug_trace.py` 中集中做 normalize；
* 对缺失字段填 None；
* UI 不直接依赖原始 chunk 对象。

### 风险 3：Debug Trace 影响正常问答

应对：

* trace 逻辑使用 try/except 包裹；
* trace 失败只记录 warning；
* 不让 trace 异常中断主查询。

### 风险 4：UI 展示过长内容

应对：

* text_preview 截断；
* 原始 JSON 默认折叠；
* 表格优先展示关键字段。

### 风险 5：本地 trace 文件被提交

应对：

* MVP 默认不落盘；
* 如使用 `data/debug_traces/`，必须加入 `.gitignore`；
* 文档明确该目录是本地运行产物。

### 风险 6：为记录 trace 破坏现有函数返回契约

应对：

* 只使用可选参数、callback 或 metadata 挂载；
* 默认不传 trace 参数时保持现有行为；
* 增加兼容性测试，确认旧调用方返回值不变。

### 风险 7：连续查询展示旧 trace

应对：

* 每次查询开始时创建新的 `trace_id`；
* Streamlit session_state 只将本轮 trace 绑定到本轮查询结果；
* UI 验收检查 original_query 和 trace_id 是否对应当前查询。

## 18. 文档更新计划

新增或更新：

```text
docs/retrieval_debug.md
CURRENT_TASK.md
specs/002-retrieval-debug-trace/PROGRESS.md
```

文档说明：

1. Debug Trace 面板入口；
2. 每个检索阶段含义；
3. not_available 的含义；
4. 本功能与 citation verification 的区别；
5. 当前限制；
6. 后续升级方向。

## 19. 实施顺序建议

建议后续 `/tasks` 按以下顺序拆分：

1. 新增 `app/debug_trace.py` 数据结构和工具函数；
2. 增加 `tests/test_debug_trace.py`；
3. 增加兼容扩展测试，确认旧调用方不传 trace 参数时返回值不变；
4. 接入结构化抽取查询入口，创建本轮 trace；
5. 接入 BM25 / vector / RRF / final context 记录；
6. 接入 V2 synthesis 路径，并将本轮 trace 兼容挂载到结果 metadata 或等价位置；
7. 接入 citation / evidence 到 chunk 的基础映射和 unmatched 标记；
8. Streamlit 新增 Debug Trace 面板；
9. 增加错误阶段记录和连续查询不混淆测试；
10. 更新文档和进度；
11. 跑测试和 smoke test。

## 20. Constitution Check

本方案符合当前项目约束：

* Evidence-first：通过展示 final context 和 citation/evidence 增强证据可追溯；
* Verifiable RAG traces：本 Feature 直接服务于可验证检索链路；
* P0 stability：采用旁路记录，不破坏主流程；
* Modular backend boundaries：新增 `app/debug_trace.py`，避免逻辑散落；
* Configuration and secret safety：不记录 API Key，不提交 data；
* Branch-driven workflow：基于 `V3-DEV` 创建 `feature/002-retrieval-debug-trace`；
* Testable acceptance：明确 pytest 和 Streamlit smoke test；
* Research data protection：不提交本地 trace、PDF、索引产物；
* Documentation synchronization：更新 CURRENT_TASK.md 和 PROGRESS.md；
* AI coding-agent constraints：后续实现必须小步修改、优先复用现有模块、不提交本地数据或密钥、不绕过 embedding/config 校验、不在测试失败时声称完成、不执行未获授权的 commit / merge / push。

## 21. 是否可进入 tasks

结论：可以进入 `/tasks`。

理由：

1. plan 覆盖 spec 中的核心需求；
2. 不做范围明确；
3. 技术路径采用旁路记录，风险可控；
4. 数据结构清楚；
5. 测试方案可执行；
6. 不违反 AGENTS.md 和 constitution；
7. 可自然拆解为独立 tasks。
