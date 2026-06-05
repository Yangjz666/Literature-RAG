# CURRENT_TASK.md

## 当前任务：Feature 002 检索调试 Debug Trace

- 当前 Feature：`002-retrieval-debug-trace`
- Feature 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 第一批任务
- 当前任务类型：实现 T001-T018，完成 Debug Trace 核心数据结构、chunk 标准化和 citation 基础映射
- 本轮修改文件：`app/debug_trace.py`、`tests/test_debug_trace.py`、`specs/002-retrieval-debug-trace/tasks.md`、`CURRENT_TASK.md`、`specs/002-retrieval-debug-trace/PROGRESS.md`
- 本轮限制：只实现 T001-T018；不接入 RAG 查询流程；不修改 `ui/streamlit_app.py`；不实现 T019-T050；不做 citation verification、claim-level verification、FastAPI、Docker、数据库、多用户、联网下载、GraphRAG 或主流程重写

## 本轮完成内容

- 完成 T001-T003：同步 Feature 进度文档、更新 CURRENT_TASK、检查 AGENTS.md 的 Feature 002 plan 路径。
- 完成 T004-T015：新增 `tests/test_debug_trace.py` 和 `app/debug_trace.py`，实现并测试：
  - `create_debug_trace()`
  - `normalize_trace_chunk()`
  - `normalize_trace_chunks()`
  - `mark_stage_not_available()`
  - `record_error()`
  - `to_json_safe()`
- 完成 T016-T018：实现并测试 citation/evidence 到 `final_context_chunks` 的 `chunk_id` 基础映射：
  - `normalize_trace_citation()`
  - `record_citations()`
  - matched / unmatched 标记
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T001-T018 标记为 `[X]`。
- 本阶段未修改现有 RAG 主流程，未修改 Streamlit UI，未引入真实 LLM、Embedding API 或 PDF 文献库依赖。

## Feature 002 目标

本 Feature 为 CO2RR Literature RAG Agent V3 增加检索调试 Debug Trace 能力，让每次 RAG 查询的检索链路可观察、可调试、可展示。

核心目标：

- 用户可以看到一次查询中系统检索到了哪些文献片段；
- 开发者可以看到关键词检索、向量检索、融合排序、重排序和 final context 的中间结果；
- 用户可以判断最终回答是否基于真实检索上下文；
- RAG 出错时，可以定位失败发生在哪个阶段；
- 不重写现有 RAG 主流程，只做旁路记录和 UI 展示。

## 当前未完成任务

- T019-T028：接入现有 RAG 查询流程，记录 rewritten query、BM25/vector/RRF/reranker/final context/final answer/elapsed_ms。
- T029-T036：Streamlit Debug Trace 面板和 Raw JSON 展示。
- T037-T040：错误处理降级和 `session_state` 当前 trace。
- T041-T044：用户文档和进度文档后续更新。
- T045-T050：最终语法检查、相关测试、完整 pytest、Streamlit smoke test、Git 安全检查和最终验收记录。
- Streamlit smoke test：未执行，本轮未修改 UI。

## 修改文件

- `app/debug_trace.py`
- `tests/test_debug_trace.py`
- `specs/002-retrieval-debug-trace/tasks.md`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 本轮测试

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | 通过 | `tasks.md` 被 SpecKit 识别 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | checklist 统计 | 通过 | `requirements.md` 16/16 完成 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m py_compile app/debug_trace.py` | 通过 | 语法检查通过 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest tests/test_debug_trace.py -q` | 通过 | 11 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest` | 通过 | 160 passed |

## 风险与注意事项

- 当前只完成 Debug Trace 核心 helper 和单元测试，尚未接入 RAG 查询流程。
- `citations_used` 只做 citation/evidence 与 final context chunk 的 `chunk_id` 映射，不做真假判断、claim-level verification 或完整 citation verification。
- 后续接入阶段必须保持旧调用方兼容，不得改变 ChromaDB、BM25、parent store 的现有存储格式。
- 后续 UI 阶段必须保证连续两次查询不混淆上一轮 trace。

## Git 操作状态

- 开发前 git status 是否干净：是。
- 是否从正确基线分支创建：是，从 `V3-DEV` 创建。
- 当前功能分支：`feature/002-retrieval-debug-trace`。
- 是否执行 git commit：待执行。
- 是否执行 merge：待执行。
- 是否执行 push：待执行。

## 下一步建议

按用户要求执行标准收尾流程：

1. 提交当前功能分支。
2. 合并 `feature/002-retrieval-debug-trace` 到 `V3-DEV`。
3. 合并后重新运行相关测试。
4. 测试通过后 push `V3-DEV`。
