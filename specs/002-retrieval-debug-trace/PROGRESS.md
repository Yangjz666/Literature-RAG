# Feature 002 开发进度：检索调试 Debug Trace

## Feature 基本信息

- Feature：`002-retrieval-debug-trace`
- 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 第一批任务
- 当前完成到：T001-T018 已完成
- 本轮完成任务：Phase 1、Phase 2、Phase 3
- Feature 状态：Debug Trace 核心数据结构、chunk 标准化、citation 基础映射已实现并测试通过；尚未接入 RAG 查询流程或 UI

## 总体目标

本 Feature 为 CO2RR Literature RAG Agent V3 增加检索调试 Debug Trace 能力，让每次 RAG 查询的检索链路可观察、可调试、可展示。

目标包括：

- 用户能看到一次查询检索到了哪些文献片段；
- 开发者能看到关键词检索、向量检索、融合排序、重排序和 final context 的中间结果；
- 用户能判断最终回答是否基于真实检索上下文；
- 查询失败时能定位失败阶段；
- 只做旁路记录和展示，不重写现有 RAG 主流程。

## 阶段进度

| Phase | 内容 | 状态 | 说明 |
| --- | --- | --- | --- |
| specify | 需求规格 | 已完成 | 已生成 `spec.md` 和 `checklists/requirements.md` |
| clarify | 需求澄清 | 已完成/无需新增问题 | 当前未发现阻塞 plan 的需求冲突 |
| plan | 技术方案 | 已完成 | 已生成并审核修订 `plan.md` |
| tasks | 任务拆解 | 已完成 | 已生成标准 `tasks.md` |
| analyze | 一致性分析 | 已完成 | 前置检查通过，未发现阻塞实现的问题 |
| implement Phase 1 | 准备与文档同步 | 已完成 | T001-T003 |
| implement Phase 2 | 测试骨架与 Debug Trace 数据结构 | 已完成 | T004-T015 |
| implement Phase 3 | Citation / Evidence 基础映射 | 已完成 | T016-T018 |
| implement Phase 4-8 | 查询流程接入、UI、降级、文档、最终验收 | 未完成 | T019-T050 |

## 本轮完成内容

- T001：更新 Feature 进度文档，记录当前阶段和风险。
- T002：更新 `CURRENT_TASK.md`。
- T003：检查 `AGENTS.md` SPECKIT 块，当前路径指向 Feature 002 plan。
- T004-T005：新增 `tests/test_debug_trace.py`，覆盖 `create_debug_trace()` 基础结构。
- T006-T007：新增 `app/debug_trace.py`，实现 `create_debug_trace()`。
- T008-T010：实现并测试 `TraceChunk` 标准化、缺失字段处理、`text_preview` 截断和批量标准化。
- T011-T012：实现并测试 `not_available` 阶段标记。
- T013-T014：实现并测试 `failed_stage` 归一化、用户可读 error 和敏感信息脱敏。
- T015：实现并测试 `to_json_safe()`。
- T016-T018：实现并测试 citation/evidence 与 final context chunk 的 `chunk_id` 基础映射，支持 matched / unmatched。
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T001-T018 标记为 `[X]`。
- 本轮未修改现有 RAG 主流程，未修改 Streamlit UI，未引入真实 LLM、Embedding API 或 PDF 文献库依赖。

## 修改文件

- `app/debug_trace.py`
- `tests/test_debug_trace.py`
- `specs/002-retrieval-debug-trace/tasks.md`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | 通过 | `tasks.md` 被 SpecKit 识别 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | checklist 统计 | 通过 | `requirements.md` 16/16 完成 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m py_compile app/debug_trace.py` | 通过 | 语法检查通过 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest tests/test_debug_trace.py -q` | 通过 | 11 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest` | 通过 | 160 passed |

## Streamlit 手动验证

- 未完成。本轮只实现 T001-T018，未修改 Streamlit UI，也未接入查询流程。

## 未完成任务

- T019-T028：接入现有 RAG 查询流程，记录 rewritten query、BM25/vector/RRF/reranker/final context/final answer/elapsed_ms。
- T029-T036：Streamlit Debug Trace 面板和 Raw JSON 展示。
- T037-T040：错误处理降级和 `session_state` 当前 trace。
- T041-T044：用户文档和进度文档后续更新。
- T045-T050：最终语法检查、相关测试、完整 pytest、Streamlit smoke test、Git 安全检查和最终验收记录。

## 风险与注意事项

- 当前核心 helper 已可独立测试，但尚未接入真实 RAG 查询链路。
- 本阶段 citation/evidence 只按 `chunk_id` 做基础 matched / unmatched 映射，不做真假判断、claim-level verification 或完整 citation verification。
- 后续实现不得引入数据库，不得重写 V1/V2/V3 主流程，不得改变 ChromaDB、BM25 或 parent store 的现有存储格式。
- 后续测试仍应使用 mock 或 fixture，不依赖真实 LLM、真实 Embedding API 或真实 PDF 文献库。

## 下一步计划

1. 完成本轮提交、合并到 `V3-DEV`、合并后测试和 push。
2. 后续新一批 implement 再执行 T019-T028，接入现有 RAG 查询流程。
3. UI 和 Streamlit smoke test 留到 T029 之后执行。

## Git 状态

- 是否执行 git commit：待执行。
- 是否执行 merge：待执行。
- 是否执行 git push：待执行。
- 当前分支：`feature/002-retrieval-debug-trace`。
- 合并目标：`V3-DEV`。
