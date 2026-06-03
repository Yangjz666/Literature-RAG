# Feature 001 开发进度：文献库管理与索引透明化

## Feature 基本信息

- Feature：`001-library-index-transparency`
- 名称：文献库管理与索引透明化
- 当前分支：`feature/001-library-index-transparency-polish`
- 当前阶段：Phase 7 / Polish
- 当前完成到：T001-T068
- 本轮完成任务：T061-T068
- Feature 状态：完整完成，测试通过，等待用户手动提交、合并、push
- 本轮限制：不执行 git commit，不执行 merge，不执行 git push

## 总体目标

本 Feature 为 CO2RR Literature RAG Agent 增加文献库管理与索引透明化能力：

- 查看本地 PDF/SI 文献库列表；
- 聚合 manifest、parse_report 和 index_status；
- 查看单篇详情、parse_report、chunk preview、索引阶段和失败原因；
- 支持单篇重新解析；
- 支持单篇重建索引；
- 支持全量重建索引；
- 支持删除文献关联记录，默认不删除原始 PDF；
- 提供用户文档、README、进度记录、测试记录和范围/安全检查记录。

本 Feature 不引入数据库、FastAPI、Docker、完整 Debug Trace、citation verification、联网下载、多用户系统或 V1/V2 主流程重写。

## 阶段进度

| Phase | User Story | Tasks | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| Phase 1 | Setup | T001-T004 | 已完成 | 开发范围、分支、路径和安全边界已确认 |
| Phase 2 | Foundational | T005-T015 | 已完成 | parse_report、index_status、operation summary 基础能力已实现 |
| Phase 3 | US1 | T016-T027 | 已完成 | 文献库列表、筛选和 V1/V2 入口兼容已实现 |
| Phase 4 | US2 | T028-T036 | 已完成 | 单篇详情、parse_report、chunk preview、failure_stage / failure_reason 展示已实现 |
| Phase 5 | US3 | T037-T049 | 已完成 | 单篇重新解析、单篇重建索引、全量重建索引和操作摘要已实现 |
| Phase 6 | US4 | T050-T060 | 已完成 | 删除文献关联记录、逐项清理摘要、UI 确认和测试已完成 |
| Phase 7 | Polish | T061-T068 | 已完成 | README、用户文档、V3 PRD、测试、范围检查、安全检查和总结已完成 |

## 本轮完成内容

- T061：更新 `docs/document_library.md`，说明页面使用、字段、状态、重建操作、删除行为和限制。
- T062：更新 `README.md`，说明 Feature 001 完整能力、运行方式、测试方式和已知限制。
- T063：更新 `CO2RR_RAG_Agent_PRD_V3.md`，同步已实现范围、验收状态和排除范围。
- T064：运行 parse_report、document_library、index_status、indexer_delete 相关测试并记录结果。
- T065：运行完整 pytest 和 Streamlit 启动 smoke test，作为 V1/V2 入口回归和应用启动检查。
- T066：确认没有新增完整 Debug Trace、citation verification、FastAPI、Docker、数据库、联网下载或 V1/V2 主流程重写。
- T067：确认本轮不提交 `.env`、`data/`、`.venv`、缓存、本地索引、本地 PDF 或 API Key。
- T068：在 `CURRENT_TASK.md` 和本文件中汇总修改文件、测试、风险和后续建议。

## 修改文件

- `README.md`
- `docs/document_library.md`
- `CO2RR_RAG_Agent_PRD_V3.md`
- `CURRENT_TASK.md`
- `specs/001-library-index-transparency/PROGRESS.md`
- `specs/001-library-index-transparency/tasks.md`

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-03 | `feature/001-library-index-transparency-polish` | `.venv/bin/python -m py_compile app/indexer.py app/document_library.py app/index_status.py app/parse_report.py ui/streamlit_app.py` | 通过，无输出 | Feature 001 相关模块语法检查 |
| 2026-06-03 | `feature/001-library-index-transparency-polish` | `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py tests/test_indexer_delete.py -q` | 32 passed in 0.83s | Feature 001 相关测试 |
| 2026-06-03 | `feature/001-library-index-transparency-polish` | `.venv/bin/python -m pytest` | 149 passed in 1.19s | 完整回归测试 |
| 2026-06-03 | `feature/001-library-index-transparency-polish` | `timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8501` | 启动成功，timeout 停止 | Streamlit 显示 Local URL `http://localhost:8501`，未做浏览器内手动点击 |

## Streamlit 手动验证建议

自动 smoke test 只能确认服务启动。浏览器内仍建议用户手动检查：

- 文献查询入口；
- 文献库管理页面；
- 单篇文献详情页；
- 单篇重新解析按钮；
- 单篇重建索引按钮；
- 全量重建索引入口；
- 删除文献关联记录入口；
- 删除操作不会删除原始 PDF 的提示和确认机制。

## 安全与范围检查

- 本轮未修改 `.env`。
- 本轮未修改 `data/`。
- 本轮未修改 `.venv/`、缓存、本地索引或本地 PDF。
- 本轮未新增 Debug Trace、citation verification、FastAPI、Docker、数据库、联网下载、多用户系统或 V1/V2 主流程重写。
- `git status --ignored --short` 显示本地存在被 ignore 的 `.env`、`.venv`、缓存、`data/chroma_db` 和本地 PDF 产物；它们不在普通 `git status` 待提交区，本轮不建议提交。
- `git ls-files` 显示历史上已有 `data/test_literature/README.md` 和一个 Zone.Identifier 文件被跟踪；本轮未修改它们，建议后续单独评估是否移出 Git 跟踪。

## 已知风险

- 自动测试不依赖真实 API Key、真实 PDF 库或真实 ChromaDB，因此不能替代真实数据上的 UI 操作验收。
- 真实 Embedding 配置缺失时，索引对象可能无法初始化，索引重建和 chunk preview 会受限。
- 删除关联记录默认保留原始 PDF；如果本地 PDF 仍在目录中，重新扫描时会以未解析/未索引状态重新出现在文献库列表中。
- Streamlit 启动 smoke 不等于浏览器内真实点击验收。

## 下一步计划

1. 用户手动检查 `git diff`。
2. 用户手动提交当前 Polish 改动。
3. 用户手动合并回 `v2-dev` 并 push。
4. 使用小型测试文献夹做浏览器内手动验收。

## Git 状态

- 是否执行 git commit：否，按用户要求不执行。
- 是否执行 merge：否，按用户要求不执行。
- 是否执行 git push：否，按用户要求不执行。
