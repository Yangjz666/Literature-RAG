# Tasks: Feature 002 检索调试 Debug Trace

## 0. Feature 信息

- Feature 编号：002
- Feature 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 功能分支：`feature/002-retrieval-debug-trace`
- 对应 spec：`specs/002-retrieval-debug-trace/spec.md`
- 对应 plan：`specs/002-retrieval-debug-trace/plan.md`
- 当前阶段：tasks
- 下一阶段：analyze → implement

## 1. 总体目标

本 Feature 目标是在不重写现有 RAG 主流程的前提下，为每次 RAG 查询生成可展示的 `debug_trace`，并在 Streamlit 页面中提供「检索调试 Debug Trace」面板。

完成后应支持：

- 查看 original query；
- 查看 rewritten query，缺失时显示 `not_available`；
- 查看 BM25 检索结果；
- 查看向量检索结果；
- 查看 RRF 融合结果，缺失时显示 `not_available`；
- 查看 reranker 结果，缺失时显示 `not_available`；
- 查看 final context chunks；
- 查看 citation/evidence 与 chunk 的基础映射；
- 查询失败时显示 `failed_stage` 和用户可读错误；
- Debug Trace 失败不影响正常 RAG 查询；
- 原有文献查询、文献库管理、结构化抽取入口不被破坏。

## 2. 不做范围

本 Feature 不做：

- 不做完整 citation verification；
- 不做 claim-level citation verification；
- 不做自动判断回答真假；
- 不引入 FastAPI；
- 不引入 Docker；
- 不引入数据库；
- 不做多用户系统；
- 不联网下载文献；
- 不做 GraphRAG；
- 不重写检索架构；
- 不重写 V1 / V2 主流程；
- 不改变 ChromaDB、BM25、parent store 的现有存储格式。

---

# Phase 1：准备与文档同步

## [X] T001 创建 Feature 进度文档

- 文件：`specs/002-retrieval-debug-trace/PROGRESS.md`
- 内容要求：
  - 记录 Feature 名称、目标、当前阶段；
  - 记录开发基线 `V3-DEV`；
  - 记录功能分支 `feature/002-retrieval-debug-trace`；
  - 记录当前待完成 task：T001-T050；
  - 记录风险：不重写主流程、Debug Trace 不影响正常查询。

## [X] T002 更新 CURRENT_TASK.md

- 文件：`CURRENT_TASK.md`
- 内容要求：
  - 当前 Feature：002 检索调试 Debug Trace；
  - 当前阶段：tasks；
  - 当前功能分支：`feature/002-retrieval-debug-trace`；
  - 下一步：执行 analyze；
  - 说明 Feature 001 已完成，当前开始 Feature 002。

## [X] T003 检查 AGENTS.md 与 Speckit 当前路径

- 文件：`AGENTS.md`
- 要求：
  - 检查 SPECKIT 块中当前 Feature 路径是否指向：
    - `specs/002-retrieval-debug-trace/spec.md`
    - `specs/002-retrieval-debug-trace/plan.md`
  - 不得删除已有项目规则；
  - 不得修改 Git 工作流规则。

---

# Phase 2：测试骨架与 Debug Trace 数据结构

## [X] T004 新增 Debug Trace 测试文件

- 文件：`tests/test_debug_trace.py`
- 任务：
  - 创建测试文件；
  - 先写基础测试骨架；
  - 不依赖真实 LLM；
  - 不依赖真实 Embedding；
  - 不依赖真实 PDF 文献库。

## [X] T005 测试 create_debug_trace 基础结构

- 文件：`tests/test_debug_trace.py`
- 测试要求：
  - `create_debug_trace()` 返回 dict；
  - 包含 `trace_id`；
  - 包含 `created_at`；
  - 包含 `user_query`；
  - 包含 `original_query`；
  - 包含 `query_mode`；
  - 包含 `warning`；
  - 包含 `error`；
  - 包含 `failed_stage`。

## [X] T006 新增 app/debug_trace.py

- 文件：`app/debug_trace.py`
- 任务：
  - 新增 Debug Trace 工具模块；
  - 不修改现有主流程；
  - 只提供可复用 helper；
  - 不引入数据库；
  - 不落盘保存 trace。

## [X] T007 实现 create_debug_trace()

- 文件：`app/debug_trace.py`
- 函数建议：

```python
create_debug_trace(user_query: str, query_mode: str | None = None) -> dict
```

* 要求：

  * 自动生成 `trace_id`；
  * 自动记录 `created_at`；
  * 初始化各阶段字段；
  * 缺失阶段默认 `not_available`；
  * 初始化 `warning` 为空列表；
  * 初始化 `error` 和 `failed_stage` 为 `None`。

## [X] T008 测试 TraceChunk 标准化

* 文件：`tests/test_debug_trace.py`
* 测试要求：

  * 原始 chunk 是 dict 时可以正常转换；
  * 原始 chunk 缺少字段时不会报错；
  * 缺失字段填 `None`；
  * `text_preview` 被截断；
  * `source_stage` 正确写入。

## [X] T009 实现 normalize_trace_chunk()

* 文件：`app/debug_trace.py`
* 函数建议：

```python
normalize_trace_chunk(raw_chunk: Any, source_stage: str) -> dict
```

* 输出字段：

  * `document_id`
  * `filename`
  * `page`
  * `section`
  * `chunk_id`
  * `parent_chunk_id`
  * `score`
  * `source_stage`
  * `text_preview`

## [X] T010 实现 normalize_trace_chunks()

* 文件：`app/debug_trace.py`
* 函数建议：

```python
normalize_trace_chunks(raw_chunks: list[Any], source_stage: str) -> list[dict]
```

* 要求：

  * 输入为空时返回空列表；
  * 单个 chunk 异常不导致整体失败；
  * 异常 chunk 可跳过或转为 warning。

## [X] T011 测试 not_available 阶段标记

* 文件：`tests/test_debug_trace.py`
* 测试要求：

  * 某阶段未启用时显示 `not_available`；
  * 可记录 reason；
  * 不影响其他阶段数据。

## [X] T012 实现 mark_stage_not_available()

* 文件：`app/debug_trace.py`
* 函数建议：

```python
mark_stage_not_available(trace: dict, stage: str, reason: str | None = None) -> None
```

* 要求：

  * 设置对应阶段为 `not_available`；
  * reason 写入 warning；
  * 不抛出致命异常。

## [X] T013 测试 failed_stage 与 error 记录

* 文件：`tests/test_debug_trace.py`
* 测试要求：

  * 能记录 `failed_stage`；
  * `failed_stage` 必须归一化为 spec 定义的阶段标签之一：`query_rewrite_failed`、`bm25_failed`、`vector_search_failed`、`rrf_failed`、`reranker_failed`、`context_builder_failed`、`llm_failed`、`citation_parse_failed` 或 `unknown_failed`；
  * 能记录用户可读 `error`；
  * 不直接暴露完整 traceback；
  * trace 仍然 JSON 可序列化。

## [X] T014 实现 record_error()

* 文件：`app/debug_trace.py`
* 函数建议：

```python
record_error(trace: dict, failed_stage: str, error: Exception | str) -> None
```

* 要求：

  * 写入 `failed_stage`；
  * 未识别的 failed_stage 统一归一化为 `unknown_failed`；
  * 写入用户可读 `error`；
  * 不把 API Key、环境变量、完整敏感路径写入 error。

## [X] T015 实现 to_json_safe()

* 文件：`app/debug_trace.py`
* 函数建议：

```python
to_json_safe(trace: dict) -> dict
```

* 要求：

  * 输出可被 `json.dumps()` 序列化；
  * 处理不可序列化对象；
  * 保留核心字段。

---

# Phase 3：Citation / Evidence 基础映射

## [X] T016 测试 citation matched / unmatched

* 文件：`tests/test_debug_trace.py`
* 测试要求：

  * citation 的 `chunk_id` 能匹配 final context；
  * 匹配成功标记 `matched`；
  * 匹配失败标记 `unmatched`；
  * 缺失 citation 时显示空列表或 `not_available`。

## [X] T017 实现 normalize_trace_citation()

* 文件：`app/debug_trace.py`
* 函数建议：

```python
normalize_trace_citation(raw_citation: Any, final_context_chunks: list[dict]) -> dict
```

* 输出字段：

  * `citation_id`
  * `document_id`
  * `filename`
  * `page`
  * `section`
  * `chunk_id`
  * `evidence_text_preview`
  * `matched_final_context`
  * `match_status`

## [X] T018 实现 record_citations()

* 文件：`app/debug_trace.py`
* 函数建议：

```python
record_citations(trace: dict, citations: list[Any]) -> None
```

* 要求：

  * 将 citations 写入 `citations_used`；
  * 能根据 `chunk_id` 与 `final_context_chunks` 匹配；
  * 无法匹配时标记 `unmatched`；
  * 不做真假判断；
  * 不做 claim-level verification。

---

# Phase 4：接入现有 RAG 查询流程

## [X] T019 分析现有 RAG 查询入口

* 文件：

  * `app/pipeline_v2.py`
  * `app/retriever.py`
  * `app/context_builder.py`
  * `app/synthesizer.py`
  * `ui/streamlit_app.py`
* 任务：

  * 找出当前 Streamlit 查询实际调用链；
  * 明确普通查询、文献综合、结构化抽取是否共用入口；
  * 记录哪些阶段可直接拿到结果；
  * 不能重写主流程。

## [X] T020 在查询入口创建 debug_trace

* 可能文件：

  * `app/pipeline_v2.py`
  * `ui/streamlit_app.py`
* 任务：

  * 每次用户发起查询时创建新的 trace；
  * 写入 `user_query`；
  * 写入 `original_query`；
  * 写入 `query_mode`；
  * 记录开始时间；
  * 确保连续两次查询不会混淆 trace。

## [X] T021 记录 rewritten_query

* 可能文件：

  * `app/query_router.py`
  * `app/pipeline_v2.py`
  * `ui/streamlit_app.py`
* 任务：

  * 如果当前项目已有 query rewrite，则记录改写结果；
  * 如果没有，则写入 `not_available`；
  * 不为了本 task 新增复杂 query rewrite。

## [X] T022 记录 BM25 results

* 可能文件：

  * `app/retriever.py`
  * `app/pipeline_v2.py`
* 任务：

  * 将 BM25 Top K 标准化为 TraceChunk；
  * 写入 `bm25_results`；
  * 如果 BM25 未启用，写入 `not_available`；
  * BM25 记录失败时写入 warning，不中断查询。

## [X] T023 记录 vector results

* 可能文件：

  * `app/retriever.py`
  * `app/pipeline_v2.py`
* 任务：

  * 将向量检索 Top K 标准化为 TraceChunk；
  * 写入 `vector_results`；
  * 如果向量检索未启用，写入 `not_available`；
  * 失败时记录 `vector_search_failed`。

## [X] T024 记录 RRF results

* 可能文件：

  * `app/retriever.py`
  * `app/pipeline_v2.py`
* 任务：

  * 如果已有 RRF 融合结果，则记录；
  * 如果当前项目没有 RRF，则显示 `not_available`；
  * 不为本 task 重写 fusion 架构。

## [X] T025 记录 reranker results

* 可能文件：

  * `app/reranker.py`
  * `app/pipeline_v2.py`
* 任务：

  * 如果已有 reranker 输出，则记录；
  * 如果未启用 reranker，则显示 `not_available`；
  * 失败时记录 `reranker_failed`；
  * 不影响原回答生成。

## [X] T026 记录 final_context_chunks

* 可能文件：

  * `app/context_builder.py`
  * `app/pipeline_v2.py`
* 任务：

  * 将最终送入 LLM 的上下文片段写入 `final_context_chunks`；
  * 每个 chunk 标准化为 TraceChunk；
  * 必须包含 filename、page、section、chunk_id、score、text_preview；
  * 如果缺少字段，用 `None`。

## [X] T027 记录 final_answer

* 可能文件：

  * `app/synthesizer.py`
  * `app/pipeline_v2.py`
  * `ui/streamlit_app.py`
* 任务：

  * LLM 生成完成后写入 `final_answer`；
  * 如果 LLM 失败，记录 `llm_failed`；
  * 不把完整 traceback 直接展示给普通用户。

## [X] T028 记录 elapsed_ms

* 可能文件：

  * `app/pipeline_v2.py`
  * `ui/streamlit_app.py`
* 任务：

  * 记录查询总耗时；
  * 写入 `elapsed_ms`；
  * 查询失败时也应尽量记录耗时。

---

# Phase 5：Streamlit Debug Trace 面板

## T029 新增 UI helper：准备阶段表格数据

* 文件：`ui/streamlit_app.py`
* 建议函数：

```python
prepare_debug_trace_table(trace: dict, stage: str) -> list[dict]
```

* 要求：

  * 支持 bm25/vector/rrf/reranker/final_context；
  * 空阶段返回 not_available；
  * 字段适合 `st.dataframe` 展示。

## T030 测试 UI helper 数据转换

* 文件：可新增或复用：

  * `tests/test_debug_trace.py`
* 测试要求：

  * not_available 阶段不报错；
  * chunk 表格字段完整；
  * citation 表格字段完整；
  * raw JSON 可序列化。

## T031 在回答区域增加 Debug Trace 折叠面板

* 文件：`ui/streamlit_app.py`
* 任务：

  * 在 RAG 回答下方增加：

    * `st.expander("检索调试 Debug Trace", expanded=False)`
  * 默认折叠；
  * 不影响普通用户阅读回答；
  * 查询失败时仍可展示已有 trace。

## T032 展示 Query 信息

* 文件：`ui/streamlit_app.py`
* 展示：

  * `trace_id`
  * `created_at`
  * `user_query`
  * `original_query`
  * `rewritten_query`
  * `query_mode`
  * `elapsed_ms`

## T033 展示检索阶段结果

* 文件：`ui/streamlit_app.py`
* 展示阶段：

  * BM25 results；
  * Vector results；
  * RRF results；
  * Reranker results；
  * Final context chunks。
* 要求：

  * 表格展示；
  * 缺失阶段显示 `not_available`；
  * 不直接展示过长全文。

## T034 展示 Citation / Evidence

* 文件：`ui/streamlit_app.py`
* 展示：

  * `citation_id`
  * `filename`
  * `page`
  * `section`
  * `chunk_id`
  * `evidence_text_preview`
  * `match_status`
* 要求：

  * matched / unmatched 清晰；
  * 明确本阶段不做真假判断。

## T035 展示 warning / error / failed_stage

* 文件：`ui/streamlit_app.py`
* 任务：

  * 如果有 warning，展示 warning；
  * 如果有 error，展示用户可读 error；
  * 如果有 failed_stage，展示失败阶段；
  * 不直接展示完整 traceback。

## T036 展示 Raw JSON

* 文件：`ui/streamlit_app.py`
* 任务：

  * 在 Debug Trace 面板底部提供 Raw JSON；
  * 默认折叠；
  * 使用 JSON-safe trace；
  * 方便开发者复制调试。

---

# Phase 6：错误处理与降级

## T037 测试 Debug Trace 不影响正常回答

* 文件：`tests/test_debug_trace.py`
* 测试要求：

  * trace 记录失败时，主回答结果仍返回；
  * trace 异常转为 warning；
  * 不影响 answer 输出；
  * 不引入额外 LLM / embedding / PDF 解析调用，避免明显增加普通查询延迟。

## T038 实现 trace 安全包装

* 文件：

  * `app/debug_trace.py`
  * 查询入口相关文件
* 任务：

  * trace 记录逻辑使用 try/except；
  * trace 失败只写 warning；
  * 不中断主流程。

## T039 测试连续两次查询 trace 不混淆

* 文件：`tests/test_debug_trace.py`
* 测试要求：

  * 第一次查询 trace_id 与第二次不同；
  * 第二次页面只展示当前 trace；
  * 不混入上一轮 final_context_chunks；
  * 不混入上一轮 citations_used。

## T040 处理 session_state 中的当前 trace

* 文件：`ui/streamlit_app.py`
* 任务：

  * 使用 `st.session_state` 保存当前 trace；
  * 每次新查询覆盖当前 trace；
  * 不默认落盘；
  * 不混淆历史 trace。

---

# Phase 7：文档与进度同步

## T041 新增 docs/retrieval_debug.md

* 文件：`docs/retrieval_debug.md`
* 内容：

  * Debug Trace 是什么；
  * 面板在哪里；
  * 每个阶段含义；
  * not_available 含义；
  * matched / unmatched 含义；
  * 本功能不是 citation verification；
  * 后续可升级方向。

## T042 更新 README.md

* 文件：`README.md`
* 内容：

  * 简要说明 Debug Trace 面板；
  * 添加使用入口；
  * 添加注意事项；
  * 不写过长技术细节。

## T043 更新 CURRENT_TASK.md

* 文件：`CURRENT_TASK.md`
* 内容：

  * 当前完成到 Feature 002；
  * 记录已完成 task；
  * 记录测试结果；
  * 记录风险；
  * 记录下一步建议。

## T044 更新 PROGRESS.md

* 文件：`specs/002-retrieval-debug-trace/PROGRESS.md`
* 内容：

  * 已完成 task 编号；
  * 当前阶段；
  * 修改文件；
  * 测试命令；
  * 测试结果；
  * Streamlit smoke test 结果或待手动验证；
  * 风险；
  * 下一步建议。

---

# Phase 8：最终测试与验收

## T045 运行语法检查

* 命令：

```bash
.venv/bin/python -m py_compile app/debug_trace.py ui/streamlit_app.py
```

如本 Feature 修改其他 app 文件，也加入对应文件。

## T046 运行 Debug Trace 相关测试

* 命令：

```bash
.venv/bin/python -m pytest tests/test_debug_trace.py -q
```

## T047 运行完整 pytest

* 命令：

```bash
.venv/bin/python -m pytest
```

* 要求：

  * 所有测试通过；
  * 如果失败，记录失败原因；
  * 不得声称 Feature 完成。

## T048 Streamlit smoke test

* 命令：

```bash
.venv/bin/python -m streamlit run ui/streamlit_app.py
```

* 手动检查：

  * 文献查询入口正常；
  * 提问后能看到回答；
  * 回答下方有 Debug Trace 面板；
  * 面板默认折叠；
  * 展开能看到 query 信息；
  * 能看到 BM25/vector/final context；
  * 缺失阶段显示 not_available；
  * 原有文献库管理页面正常；
  * 结构化抽取入口不被破坏；
  * 文献综合入口不被破坏；
  * Debug Trace 面板只展示当前查询生成的 trace；
  * 连续两次查询不混淆上一轮 trace；
  * 没有红色 traceback。

## T049 Git 安全检查

* 检查项：

  * `.env` 未提交；
  * API Key 未提交；
  * `data/` 未提交；
  * `.venv/` 未提交；
  * `__pycache__/` 未提交；
  * `.pytest_cache/` 未提交；
  * 本地 ChromaDB / BM25 / parent store 未提交；
  * 本地 PDF 文献库未提交；
  * 如存在 `data/debug_traces/`，必须被忽略。

## T050 最终验收记录

* 文件：

  * `CURRENT_TASK.md`
  * `specs/002-retrieval-debug-trace/PROGRESS.md`
* 内容：

  * Feature 002 是否完成；
  * 已完成 task：T001-T050；
  * 测试结果；
  * smoke test 结果；
  * 已知风险；
  * 后续建议；
  * 是否建议提交、合并、push。

---

# 3. 任务依赖关系

推荐顺序：

```text
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
```

不能跳过：

* 未完成 Debug Trace 数据结构前，不应做 UI 面板；
* 未完成 final_context_chunks 标准化前，不应做 citation 映射；
* 未完成测试前，不应声称 Feature 完成；
* 未更新 CURRENT_TASK.md 和 PROGRESS.md 前，不应进入最终提交。

---

# 4. 验收条件

Feature 002 完成时必须满足：

1. 用户查询后能看到「检索调试 Debug Trace」面板；
2. 面板默认折叠；
3. 面板能展示 original query；
4. 面板能展示 rewritten query 或 not_available；
5. 面板能展示 BM25 results 或 not_available；
6. 面板能展示 vector results 或 not_available；
7. 面板能展示 RRF results 或 not_available；
8. 面板能展示 reranker results 或 not_available；
9. 面板能展示 final_context_chunks；
10. 面板能展示 citation/evidence matched / unmatched；
11. 查询失败时能展示 failed_stage 和 error；
12. Debug Trace 失败不影响正常回答；
13. 连续两次查询不会混淆 trace；
14. 原有文献查询入口不被破坏；
15. Feature 001 文献库管理页面不被破坏；
16. 结构化抽取入口不被破坏；
17. 文献综合入口不被破坏；
18. `pytest` 通过；
19. Streamlit 能启动；
20. `CURRENT_TASK.md` 和 `PROGRESS.md` 已更新；
21. 没有提交 `.env`、`data/`、`.venv/` 或本地索引产物。

---

# 5. 建议提交信息

实现完成并测试通过后，建议 commit message：

```text
feat: add retrieval debug trace panel
```
