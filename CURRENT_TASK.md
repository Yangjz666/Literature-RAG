# CURRENT_TASK.md

## 当前任务：Feature 002 检索调试 Debug Trace

- 当前 Feature：`002-retrieval-debug-trace`
- Feature 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：plan review refinement
- 当前任务类型：根据 Plan 审核报告修订 Speckit plan 文档
- 本轮修改文档：`AGENTS.md`、`specs/002-retrieval-debug-trace/plan.md`、`CURRENT_TASK.md`、`specs/002-retrieval-debug-trace/PROGRESS.md`
- 本轮限制：只修改文档，不进入 tasks、analyze 或 implement；不修改业务代码，不执行 git commit，不 merge，不 push

## 本轮完成内容

- 根据 `speckit-plan-review` 审核报告修订 `specs/002-retrieval-debug-trace/plan.md`。
- 更新 `AGENTS.md` SPECKIT 块，将当前 plan 路径指向 `specs/002-retrieval-debug-trace/plan.md`。
- 明确 Debug Trace 对 `hybrid_retrieve()`、`hybrid_retrieve_candidates()`、`run_synthesis_pipeline()` 等现有调用方的兼容接入方式。
- 修正 plan 中误导性的测试文件名，改为现有 V2 测试文件或明确新增测试文件。
- 补充 V2 synthesis 路径、连续两次查询不混淆 trace、citation 只做 chunk 映射和 unmatched 标记、`data/debug_traces/` 后续落盘安全规则、AI coding-agent constraints。
- 使用 `speckit-specify` 生成 Feature 002 需求规格。
- 确认功能属于 V3，开发基线为 `V3-DEV`。
- 开发前确认 `git status --short` 为空。
- 在 `V3-DEV` 执行同步，结果为 `Already up to date.`。
- 执行 SpecKit before_specify git feature hook，创建并切换到 `feature/002-retrieval-debug-trace`。
- 创建当前 Feature 目录：`specs/002-retrieval-debug-trace/`。
- 创建规格质量 checklist：`specs/002-retrieval-debug-trace/checklists/requirements.md`。
- 更新 `.specify/feature.json` 指向当前 Feature 目录。
- 建立本 Feature 进度文档：`specs/002-retrieval-debug-trace/PROGRESS.md`。

## Feature 002 目标

本 Feature 为 CO2RR Literature RAG Agent V3 增加检索调试 Debug Trace 能力，让每次 RAG 查询的检索链路可观察、可调试、可展示。

核心目标：

- 用户可以看到一次查询中系统检索到了哪些文献片段；
- 开发者可以看到关键词检索、向量检索、融合排序、重排序和 final context 的中间结果；
- 用户可以判断最终回答是否基于真实检索上下文；
- RAG 出错时，可以定位失败发生在哪个阶段；
- 不重写现有 RAG 主流程，只做旁路记录和 UI 展示。

## 当前未完成任务

- `/speckit-clarify`：未执行，本 Feature 当前未发现必须阻塞 plan 的需求冲突。
- `/speckit-plan`：已生成并根据审核报告完成小修。
- `/speckit-tasks`：未开始。
- `/speckit-analyze`：未开始。
- `/speckit-implement`：未开始。
- 相关 pytest：未运行，本轮只修改 Speckit 文档。
- Streamlit smoke test：未运行，本轮未修改应用代码。
- 功能分支提交：未完成。
- 合并回 `V3-DEV`：未完成。
- 合并后测试：未完成。
- push：未完成。

## 修改文件

- `AGENTS.md`
- `.specify/feature.json`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/plan.md`
- `specs/002-retrieval-debug-trace/spec.md`
- `specs/002-retrieval-debug-trace/checklists/requirements.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 本轮测试

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `V3-DEV` | `git status --short` | 通过，无输出 | 开发前工作区干净 |
| 2026-06-05 | `V3-DEV` | `timeout 60 git pull` | 通过，`Already up to date.` | 基线分支已同步 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `/speckit-specify` 文档生成与规格质量检查 | 通过 | 本轮只生成规格文档 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `speckit-plan-review` 审核建议文档修订 | 通过 | 只修改文档，未编码、未提交 |

## 风险与注意事项

- 当前已完成需求规格和 plan 小修，尚未进入 tasks。
- 后续 tasks 阶段必须把结构化抽取路径、V2 synthesis 路径、失败路径、连续查询不混淆和旧调用方兼容性拆成明确任务。
- 后续实现不得重写 V1/V2/V3 主流程，不得改变 ChromaDB、BM25 或 parent store 的现有存储格式。
- Debug Trace 本阶段只做基础追溯，不做完整 citation verification 或 claim-level citation verification。
- 后续测试不得依赖真实 LLM、真实 Embedding API 或真实 PDF 文献库。

## Git 操作状态

- 开发前 git status 是否干净：是。
- 是否从正确基线分支创建：是，从 `V3-DEV` 创建。
- 当前功能分支：`feature/002-retrieval-debug-trace`。
- 是否执行 git commit：否。
- 是否执行 merge：否。
- 是否执行 push：否。

## 下一步建议

下一步建议进入：

```text
/speckit-tasks
```

进入 tasks 前，建议再次确认 `git status` 只包含本 Feature 相关文档改动。
