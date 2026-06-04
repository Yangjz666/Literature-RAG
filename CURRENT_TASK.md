# CURRENT_TASK.md

## 当前任务：后续功能路线图整理

- 当前分支：`v2-dev`
- 当前任务类型：规划文档整理
- 本轮新增文档：`specs/所有task.md`
- 本轮限制：只新增/更新文档，不修改业务代码，不执行 git commit，不 merge，不 push

## Feature 001 状态

Feature 001「文献库管理与索引透明化」已完成：

- 文献库列表；
- 单篇文献详情；
- parse_report；
- index_status；
- chunk preview；
- 单篇重新解析；
- 单篇重建索引；
- 全量重建索引；
- 删除文献关联记录；
- 文档、测试、验收收尾。

当前状态：

- 已完成 T001-T068；
- 已合并到 `v2-dev`；
- 已 push 到 `origin/v2-dev`；
- 后续只做维护和 bug 修复。

## 后续总需求整理

后续 5 个核心 Feature 已整理到：

```text
specs/所有task.md
```

包含：

1. Feature 001：文献库管理与索引透明化，已完成；
2. Feature 002：检索调试 Debug Trace，待开发，下一步优先做；
3. Feature 003：结果追溯与 Citation Evidence，待开发；
4. Feature 004：评测、日志、Token、耗时和成本统计，待开发；
5. Feature 005：部署与项目展示闭环，待开发，最后做。

## 下一步建议

建议下一步开始 Feature 002：检索调试 Debug Trace。

建议新建分支：

```bash
git switch v2-dev
git pull
git switch -c feature/002-retrieval-debug-trace
```

Feature 002 应单独走 Speckit / AGENTS.md 流程：

1. specify；
2. clarify；
3. plan；
4. tasks；
5. analyze；
6. implement；
7. test；
8. document sync；
9. 提交、合并、合并后测试、push。

## 范围和安全要求

后续每个 Feature 都应单独开发，不混入无关功能。

继续禁止提交：

- `.env`；
- API Key；
- `data/` 运行产物；
- ChromaDB 本地索引；
- BM25 / parent store 本地运行产物；
- 本地 PDF 文献库；
- `.venv/`；
- `__pycache__/`；
- `.pytest_cache/`。

Feature 002 不应引入：

- 完整 citation verification；
- FastAPI；
- Docker；
- 数据库；
- 联网下载；
- V1/V2 主流程重写。

## 本轮修改文件

- `specs/所有task.md`
- `CURRENT_TASK.md`

## 本轮测试

未运行自动化测试。本轮只新增/更新规划文档，不修改 `app/`、`ui/` 或 `tests/` 业务代码。

## Git 操作状态

- 是否执行 git commit：否
- 是否执行 merge：否
- 是否执行 push：否

## 后续记录规则

每个新 Feature 开始后，都必须维护：

- `CURRENT_TASK.md`
- `specs/<feature-name>/PROGRESS.md`
- 对应 Speckit `spec.md`、`plan.md`、`tasks.md`

每次完成一个需求、阶段、User Story 或 task 后，必须记录完成内容、修改文件、测试命令、测试结果、风险、下一步建议以及提交/合并/push 状态。
