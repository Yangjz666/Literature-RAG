# Feature 002 开发进度：检索调试 Debug Trace

## Feature 基本信息

- Feature：`002-retrieval-debug-trace`
- 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 第二批任务
- 当前完成到：T001-T028 已完成
- 本轮完成任务：Phase 4，接入现有 V2 RAG 查询流程
- Feature 状态：Debug Trace 核心数据结构、TraceChunk/TraceCitation 标准化、V2 synthesis pipeline 旁路 trace 记录已实现并测试通过；尚未实现 Streamlit 面板和 session_state 当前 trace

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
| implement Phase 4 | 接入现有 RAG 查询流程 | 已完成 | T019-T028 |
| implement Phase 5-8 | UI、降级、文档、最终验收 | 未完成 | T029-T050 |

## 本轮完成内容

- T019：分析现有 RAG 查询入口。
  - 文献综合入口调用 `run_synthesis_pipeline()`。
  - V2 synthesis 调用链为 `hybrid_retrieve_candidates()` → `rerank_candidates()` → `build_v2_context()` → `synthesize_with_citations()`。
  - 普通结构化抽取路径仍走 `hybrid_retrieve()`，本批未接入 UI 或结构化抽取入口。
- T020：在 `run_synthesis_pipeline()` 中创建每次查询独立的 `debug_trace`。
- T021：未新增 query rewrite，`rewritten_query` 保持 `not_available`。
- T022：在 `hybrid_retrieve_candidates()` 中记录 BM25 results。
- T023：在 `hybrid_retrieve_candidates()` 中记录 vector results；检索异常时记录 `vector_search_failed` 并保持原异常行为。
- T024：在候选融合后记录 RRF results，不重写 fusion 架构。
- T025：在 pipeline reranker 后记录 reranker results。
- T026：根据 context citations 记录实际进入 final context 的 chunks。
- T027：记录 final answer；LLM 阶段异常标记为 `llm_failed`。
- T028：成功或失败时尽量记录 `elapsed_ms`。
- 新增测试验证 metadata debug trace、连续查询 trace 不混淆、LLM 失败 trace 脱敏与阶段记录。
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T019-T028 标记为 `[X]`。

## 修改文件

- `app/debug_trace.py`
- `app/retriever.py`
- `app/pipeline_v2.py`
- `tests/test_debug_trace.py`
- `tests/test_v2_pipeline.py`
- `specs/002-retrieval-debug-trace/tasks.md`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | 通过 | `tasks.md` 被 SpecKit 识别 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | checklist 统计 | 通过 | `requirements.md` 16/16 完成 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m py_compile app/debug_trace.py app/pipeline_v2.py app/retriever.py app/context_builder.py app/synthesizer.py` | 通过 | 语法检查通过 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest tests/test_debug_trace.py -q` | 通过 | 13 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest` | 通过 | 165 passed |

## Streamlit 手动验证

- 未完成。本轮只实现 T019-T028，未修改 Streamlit UI，也未实现 Debug Trace 面板。

## 未完成任务

- T029-T036：Streamlit Debug Trace 面板和 Raw JSON 展示。
- T037-T040：错误处理降级和 `session_state` 当前 trace。
- T041-T044：用户文档和进度文档后续更新。
- T045-T050：最终语法检查、相关测试、完整 pytest、Streamlit smoke test、Git 安全检查和最终验收记录。

## 风险与注意事项

- 当前 trace 已挂载到 V2 synthesis `SynthesisResult.metadata["debug_trace"]`，但 UI 尚未展示。
- 结构化抽取路径仍未挂载 debug trace；本批按用户范围只做 T019-T028 的最小接入。
- `rewritten_query` 当前为 `not_available`，未新增 query rewrite。
- 本阶段仍不做真假判断、claim-level verification 或完整 citation verification。
- 后续实现不得引入数据库，不得重写 V1/V2/V3 主流程，不得改变 ChromaDB、BM25 或 parent store 的现有存储格式。

## 下一步计划

1. 完成本轮提交、合并到 `V3-DEV`、合并后测试。
2. 不执行 push，由用户手动 push `V3-DEV`。
3. 后续新一批 implement 再执行 T029-T036，增加 Streamlit Debug Trace 面板。

## Git 状态

- 是否执行 git commit：待执行。
- 是否执行 merge：待执行。
- 是否执行 git push：否，本轮明确不 push。
- 当前分支：`feature/002-retrieval-debug-trace`。
- 合并目标：`V3-DEV`。
