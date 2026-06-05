# Feature 002 开发进度：检索调试 Debug Trace

## Feature 基本信息

- Feature：`002-retrieval-debug-trace`
- 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：specify
- 当前完成到：已生成需求规格草案和规格质量 checklist
- 本轮完成任务：`/speckit-specify`
- Feature 状态：需求规格已生成，等待后续 `/speckit-clarify` 或 `/speckit-plan`
- 本轮限制：只生成规格与进度文档，不进入 clarify、plan、tasks、analyze 或 implement；不修改业务代码，不执行 git commit，不 merge，不 push

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
| clarify | 需求澄清 | 未开始 | 本轮按用户要求不进入 |
| plan | 技术方案 | 未开始 | 本轮按用户要求不进入 |
| tasks | 任务拆解 | 未开始 | 本轮按用户要求不进入 |
| analyze | 一致性分析 | 未开始 | 本轮按用户要求不进入 |
| implement | 实现 | 未开始 | 本轮按用户要求不进入 |

## 本轮完成内容

- 确认当前功能属于 V3。
- 确认当前分支为 `V3-DEV`，开发前 `git status --short` 为空。
- 同步 `V3-DEV`，结果为 `Already up to date.`。
- 执行 SpecKit before_specify git feature hook，创建并切换到 `feature/002-retrieval-debug-trace`。
- 创建 `specs/002-retrieval-debug-trace/spec.md`。
- 创建 `specs/002-retrieval-debug-trace/checklists/requirements.md`。
- 更新 `.specify/feature.json` 指向当前 Feature 目录。
- 更新 `CURRENT_TASK.md` 记录当前 Feature 002 状态。

## 修改文件

- `.specify/feature.json`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/spec.md`
- `specs/002-retrieval-debug-trace/checklists/requirements.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `V3-DEV` | `git status --short` | 通过，无输出 | 开发前工作区干净 |
| 2026-06-05 | `V3-DEV` | `timeout 60 git pull` | 通过，`Already up to date.` | 基线分支已同步 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `/speckit-specify` 文档生成与规格质量检查 | 通过 | 本轮只生成规格文档 |

## Streamlit 手动验证

- 未完成。本轮只执行 `/speckit-specify`，未修改应用代码，未启动 Streamlit。

## 未完成任务

- `/speckit-clarify`
- `/speckit-plan`
- `/speckit-tasks`
- `/speckit-analyze`
- `/speckit-implement`
- 相关 pytest
- Streamlit smoke test
- 功能分支提交、合并、合并后测试、push

## 风险与注意事项

- 当前只是需求规格阶段，尚未验证现有 RAG 查询链路是否已经暴露所有中间阶段数据。
- 后续 plan 阶段需要确认哪些阶段已实现，哪些阶段只能显示 `not_available`。
- 后续实现不得引入数据库，不得重写 V1/V2/V3 主流程，不得改变 ChromaDB、BM25 或 parent store 的现有存储格式。
- Debug Trace 只做基础追溯，不等同于 claim-level citation verification。
- 自动测试后续必须使用 mock 或 fixture，不依赖真实 LLM、真实 Embedding API 或真实 PDF 文献库。

## 下一步计划

1. 进入 `/speckit-clarify` 或直接 `/speckit-plan`，由用户决定。
2. plan 阶段更新 AGENTS.md 中 SPECKIT 块的当前 plan 路径。
3. tasks 阶段拆分 Debug Trace 数据结构、记录逻辑、UI 展示、失败阶段记录、citation 基础匹配、测试和文档同步任务。

## Git 状态

- 是否执行 git commit：否，本轮用户要求只执行 `/specify`。
- 是否执行 merge：否。
- 是否执行 git push：否。
- 当前分支：`feature/002-retrieval-debug-trace`。
- 合并目标：`V3-DEV`，待后续完整流程完成并测试通过后执行。
