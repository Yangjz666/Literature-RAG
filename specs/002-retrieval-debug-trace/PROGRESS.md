# Feature 002 开发进度：检索调试 Debug Trace

## Feature 基本信息

- Feature：`002-retrieval-debug-trace`
- 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 第三批任务
- 当前完成到：T001-T036 已完成
- 本轮完成任务：Phase 5，Streamlit Debug Trace 面板和 Raw JSON 展示
- Feature 状态：Debug Trace 核心、V2 synthesis pipeline 旁路 trace、Streamlit 展示面板已实现并测试通过；尚未实现 `session_state` 当前 trace、后续文档和最终验收

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
| implement Phase 5 | Streamlit Debug Trace 面板 | 已完成 | T029-T036 |
| implement Phase 6-8 | 降级、文档、最终验收 | 未完成 | T037-T050 |

## 本轮完成内容

- T029：新增 Debug Trace 表格数据 helper，并在 `ui/streamlit_app.py` 暴露 `prepare_debug_trace_table()` 包装。
- T030：新增 helper 单元测试，覆盖 `not_available`、chunk 表格、citation 表格和 Raw JSON 序列化。
- T031：在文献综合回答区域下方新增默认折叠的「检索调试 Debug Trace」面板。
- T032：展示 Query 信息：`trace_id`、`created_at`、`user_query`、`original_query`、`rewritten_query`、`query_mode`、`elapsed_ms`。
- T033：展示 BM25、Vector、RRF、Reranker 和 Final context chunks 表格，缺失阶段显示 `not_available`。
- T034：展示 Citation / Evidence 表格，并明确本阶段不做真假判断或 claim-level citation verification。
- T035：展示 warning、error 和 failed_stage。
- T036：提供默认隐藏的 Raw JSON 显示入口，使用 JSON-safe trace。
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T029-T036 标记为 `[X]`。

## 修改文件

- `app/debug_trace.py`
- `ui/streamlit_app.py`
- `tests/test_debug_trace.py`
- `specs/002-retrieval-debug-trace/tasks.md`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | 通过 | `tasks.md` 被 SpecKit 识别 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | checklist 统计 | 通过 | `requirements.md` 16/16 完成 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m py_compile ui/streamlit_app.py app/debug_trace.py` | 通过 | 语法检查通过 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest tests/test_debug_trace.py -q` | 通过 | 17 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest` | 通过 | 169 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py` | 通过启动，超时停止 | Streamlit 启动到 `http://localhost:8501`，未做浏览器点击验证 |

## Streamlit 手动验证

- 服务器启动成功，但未完成浏览器内点击验证。
- 需要用户手动验证：文献综合完成后 Debug Trace 面板默认折叠、展开后表格显示、Citation / Evidence 展示、Raw JSON checkbox 展示。

## 未完成任务

- T037-T040：错误处理降级和 `session_state` 当前 trace。
- T041-T044：用户文档和进度文档后续更新。
- T045-T050：最终语法检查、相关测试、完整 pytest、Streamlit smoke test、Git 安全检查和最终验收记录。

## 风险与注意事项

- Debug Trace 面板当前展示文献综合路径的 `SynthesisResult.metadata["debug_trace"]`，结构化抽取路径仍未挂载 debug trace。
- T037-T040 尚未完成，当前还没有专门的 session 当前 trace 管理。
- 本阶段仍不做真假判断、claim-level verification 或完整 citation verification。
- 后续实现不得引入数据库，不得重写 V1/V2/V3 主流程，不得改变 ChromaDB、BM25 或 parent store 的现有存储格式。

## 下一步计划

1. 完成本轮提交、合并到 `V3-DEV`、合并后测试。
2. 不执行 push，由用户手动 push `V3-DEV`。
3. 后续新一批 implement 再执行 T037-T040，补充错误降级和 `session_state` 当前 trace。

## Git 状态

- 是否执行 git commit：待执行。
- 是否执行 merge：待执行。
- 是否执行 git push：否，本轮明确不 push。
- 当前分支：`feature/002-retrieval-debug-trace`。
- 合并目标：`V3-DEV`。
