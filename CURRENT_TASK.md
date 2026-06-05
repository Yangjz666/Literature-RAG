# CURRENT_TASK.md

## 当前任务：Feature 002 检索调试 Debug Trace

- 当前 Feature：`002-retrieval-debug-trace`
- Feature 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 第二批任务
- 当前任务类型：实现 T019-T028，将 Debug Trace 旁路接入现有 V2 RAG 查询流程
- 本轮修改文件：`app/debug_trace.py`、`app/retriever.py`、`app/pipeline_v2.py`、`tests/test_debug_trace.py`、`tests/test_v2_pipeline.py`、`specs/002-retrieval-debug-trace/tasks.md`、`CURRENT_TASK.md`、`specs/002-retrieval-debug-trace/PROGRESS.md`
- 本轮限制：只实现 T019-T028；不实现 Streamlit Debug Trace 面板；不实现 `session_state` 当前 trace；不做 T041-T050 文档收尾和最终验收；不做 citation verification、claim-level verification、FastAPI、Docker、数据库、多用户、联网下载、GraphRAG 或主流程重写

## 本轮完成内容

- 完成 T019：分析现有查询入口。
  - Streamlit 文献综合入口调用 `run_synthesis_pipeline()`。
  - V2 synthesis 调用链为 `hybrid_retrieve_candidates()` → `rerank_candidates()` → `build_v2_context()` → `synthesize_with_citations()`。
  - 结构化抽取路径仍走 `hybrid_retrieve()`，本批未接入；后续 UI/入口任务再处理。
- 完成 T020：`run_synthesis_pipeline()` 每次调用创建独立 `debug_trace`，写入 `user_query`、`original_query`、`query_mode` 和开始时间。
- 完成 T021：当前未新增复杂 query rewrite，`rewritten_query` 保持 `not_available`。
- 完成 T022-T024：`hybrid_retrieve_candidates()` 以可选 `debug_trace` 旁路记录 BM25、vector 和 RRF results。
- 完成 T025：pipeline 记录 reranker results。
- 完成 T026：pipeline 基于 context citations 记录实际 final context chunks。
- 完成 T027：pipeline 记录 final answer；LLM 阶段异常标记 `llm_failed` 并保留原异常抛出。
- 完成 T028：pipeline 成功或失败时尽量写入 `elapsed_ms`。
- Debug Trace 被写入 `SynthesisResult.metadata["debug_trace"]`，旧调用方不传 trace 时仍可正常调用。
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T019-T028 标记为 `[X]`。

## Feature 002 目标

本 Feature 为 CO2RR Literature RAG Agent V3 增加检索调试 Debug Trace 能力，让每次 RAG 查询的检索链路可观察、可调试、可展示。

核心目标：

- 用户可以看到一次查询中系统检索到了哪些文献片段；
- 开发者可以看到关键词检索、向量检索、融合排序、重排序和 final context 的中间结果；
- 用户可以判断最终回答是否基于真实检索上下文；
- RAG 出错时，可以定位失败发生在哪个阶段；
- 不重写现有 RAG 主流程，只做旁路记录和 UI 展示。

## 当前未完成任务

- T029-T036：Streamlit Debug Trace 面板和 Raw JSON 展示。
- T037-T040：错误处理降级和 `session_state` 当前 trace。
- T041-T044：用户文档和进度文档后续更新。
- T045-T050：最终语法检查、相关测试、完整 pytest、Streamlit smoke test、Git 安全检查和最终验收记录。
- Streamlit smoke test：未执行，本轮未修改 UI。

## 修改文件

- `app/debug_trace.py`
- `app/retriever.py`
- `app/pipeline_v2.py`
- `tests/test_debug_trace.py`
- `tests/test_v2_pipeline.py`
- `specs/002-retrieval-debug-trace/tasks.md`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 本轮测试

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | 通过 | `tasks.md` 被 SpecKit 识别 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | checklist 统计 | 通过 | `requirements.md` 16/16 完成 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m py_compile app/debug_trace.py app/pipeline_v2.py app/retriever.py app/context_builder.py app/synthesizer.py` | 通过 | 语法检查通过 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest tests/test_debug_trace.py -q` | 通过 | 13 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest` | 通过 | 165 passed |

## 风险与注意事项

- 本批只接入 V2 synthesis pipeline 的 metadata trace，尚未实现 Streamlit 面板展示。
- 结构化抽取路径仍走 `hybrid_retrieve()`，本批未改 UI 或结构化抽取入口。
- `rewritten_query` 当前仍为 `not_available`，因为本批不新增复杂 query rewrite。
- Debug Trace 失败不应影响正常查询；后续 T037-T040 仍需补充 session/current-trace 降级验证。

## Git 操作状态

- 开发前 git status 是否干净：是。
- 当前功能分支：`feature/002-retrieval-debug-trace`。
- 是否执行 git commit：待执行。
- 是否执行 merge：待执行。
- 是否执行 push：否，本轮明确不 push。

## 下一步建议

按用户要求执行标准收尾流程：

1. 在功能分支提交本批 T019-T028。
2. 合并 `feature/002-retrieval-debug-trace` 到 `V3-DEV`。
3. 合并后重新运行测试。
4. 不执行 push，由用户手动 push `V3-DEV`。
