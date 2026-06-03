# Feature 001 开发进度：文献库管理与索引透明化

## 1. Feature 基本信息

- Feature 名称：文献库管理与索引透明化
- Feature 目录：`specs/001-library-index-transparency/`
- 当前开发分支：`feature/001-library-index-transparency-us2`
- 开发基线分支：`v2-dev`
- 当前状态：US2 已完成并通过本轮验证，完整 Feature 尚未完成
- 当前完成范围：Phase 1、Phase 2、Phase 3 / US1、Phase 4 / US2，T001-T036
- 当前未完成范围：Phase 5 / US3、Phase 6 / US4、Phase 7 / Polish，T037-T068
- 最近更新时间：2026-06-03

## 2. 总体目标

本 Feature 的目标是为 CO2RR RAG Agent 提供文献库管理与索引透明化能力：

- 文献可管理；
- 索引可观察；
- 支持文献库列表；
- 支持单篇文献详情；
- 支持单篇重新解析；
- 支持单篇重建索引；
- 支持删除文献关联记录；
- 支持文档、测试和验收记录。

当前已完成 MVP 和 US2，完整 Feature 尚未完成。

## 3. tasks.md 阶段进度

| Phase | User Story | Task 编号 | 内容 | 当前状态 | 备注 |
|---|---|---|---|---|---|
| Phase 1 | Setup | T001-T004 | 准备工作 | 已完成 | 已完成开发前范围确认、入口审查、配置路径确认和敏感信息检查 |
| Phase 2 | Foundational | T005-T015 | parse_report、index_status 基础能力 | 已完成 | 已完成基础 JSON 状态、校验、读写和测试 |
| Phase 3 | US1 | T016-T027 | 文献库列表 MVP | 已完成 | MVP 已完成并合并到 `v2-dev` |
| Phase 4 | US2 | T028-T036 | 单篇文献详情页 | 已完成 | 本轮完成并验证 parse_report detail、document detail、chunk preview 和失败字段展示 |
| Phase 5 | US3 | T037-T049 | 重新解析与重建索引 | 未完成 | 本轮未实现；涉及单篇解析、索引重建和全量重建，风险高于 MVP |
| Phase 6 | US4 | T050-T060 | 删除文献关联记录 | 未完成 | 必须确保默认不删除原始 PDF |
| Phase 7 | Polish | T061-T068 | 文档、测试、验收、安全检查 | 未完成 | 需随 US2-US4 完成后补齐 |

## 4. 已完成内容

### 2026-06-03：US2 单篇文献详情页

- 完成 task：T028-T036
- 完成内容：
  - T028：补充 parse_report detail loading 和 failed-report display data 测试；
  - T029：补充 document detail item 测试，覆盖 chunk preview 和 index failure 字段；
  - T030：实现通过 `document_id` 读取 parse_report detail；
  - T031：实现单篇文献 chunk preview 查询；
  - T032：实现单篇文献详情聚合；
  - T033：在 Streamlit 文献库管理页添加文献选择和详情面板；
  - T034：展示 parse_report 摘要和原始 JSON；
  - T035：展示 chunk preview 表格；
  - T036：展示 index stage、failure stage、failure reason 和 latest operation。
- 修改文件：
  - 本轮未修改业务代码；当前代码中已存在并验证 US2 相关实现；
  - 本轮同步更新 `specs/001-library-index-transparency/PROGRESS.md`；
  - 本轮同步更新根目录 `CURRENT_TASK.md`。
- 验证文件：
  - `app/parse_report.py`
  - `app/indexer.py`
  - `app/document_library.py`
  - `ui/streamlit_app.py`
  - `tests/test_parse_report.py`
  - `tests/test_document_library.py`
  - `tests/test_index_status.py`
- 测试命令：
  - `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q`
  - `.venv/bin/python -m py_compile app/parse_report.py app/indexer.py app/document_library.py ui/streamlit_app.py`
  - `.venv/bin/python -m streamlit run ui/streamlit_app.py`
- 测试结果：
  - US2 相关 pytest：27 passed in 1.01s；
  - 语法检查：通过；
  - Streamlit smoke test：成功启动到 `http://localhost:8502`，20 秒超时退出为预期结束。
- 手动 smoke test：已完成启动 smoke；未使用真实 PDF/Embedding 做详情页人工点击验收。
- 是否提交：否，本轮按要求不执行 git commit
- 是否合并：否，本轮未合并
- 是否 push：否，本轮按要求不执行 git push
- 已知风险：
  - 当前仓库代码中已存在 US3/US4 相关实现痕迹，但本轮未新增、未修改、未验证 US3/US4；
  - chunk preview 依赖本地 ChromaDB / parent store 和 embedding 配置可用；
  - 未用真实文献库手动点击验证详情页。
- 下一步建议：
  - 明确是否继续 US3：T037-T049；
  - 若继续 US3，应先确认当前代码与 tasks.md 状态是否需要回退或拆分；
  - 继续保持每完成 task 后同步更新 `PROGRESS.md` 和 `CURRENT_TASK.md`。

### 2026-06-03：MVP 阶段

- 完成 task：T001-T027
- 完成内容：
  - Phase 1：Setup，T001-T004；
  - Phase 2：Foundational，T005-T015；
  - Phase 3：US1 文献库列表 MVP，T016-T027；
  - 已完成 parse_report / index_status 基础能力和文献库列表展示。
- 修改文件：
  - `app/parse_report.py`
  - `app/index_status.py`
  - `app/document_library.py`
  - `app/chunker.py`
  - `app/indexer.py`
  - `ui/streamlit_app.py`
  - `tests/test_parse_report.py`
  - `tests/test_index_status.py`
  - `tests/test_document_library.py`
  - `config.yaml`
  - `CURRENT_TASK.md`
- 测试命令：
  - `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_index_status.py tests/test_document_library.py -q`
  - `PYTHONPATH=. .venv/bin/pytest tests/test_acceptance.py -k "changed_files or manifest_saved" -q`
  - `PYTHONPATH=. .venv/bin/pytest tests/test_acceptance.py::TestChunker -q`
  - `python3 -m py_compile app/parse_report.py app/index_status.py app/document_library.py app/chunker.py app/indexer.py ui/streamlit_app.py`
- 测试结果：
  - MVP 相关测试记录：15 passed；
  - manifest 兼容测试记录：1 passed，38 deselected；
  - chunker 兼容测试记录：4 passed；
  - 语法编译检查通过。
- 手动 smoke test：待重新运行
- 是否提交：已提交 MVP
- 是否合并：已合并到 `v2-dev`
- 已知风险：
  - US2、US3、US4 尚未实现；
  - 后续 US3 和 US4 涉及索引重建和删除关联记录，风险高于 MVP；
  - 必须确保不删除原始 PDF，不提交 `data/` 本地运行数据。
- 下一步建议：
  - 从 `v2-dev` 创建 `feature/001-library-index-transparency-complete`；
  - 先实现 US2：T028-T036 单篇文献详情页；
  - 完成后运行 pytest 和 Streamlit smoke test；
  - 同步更新 `PROGRESS.md` 和 `CURRENT_TASK.md`。

## 5. 当前未完成任务

- 未完成 Phase：
  - Phase 5：US3；
  - Phase 6：US4；
  - Phase 7：Polish。
- 未完成 User Story：
  - US3 重新解析与重建索引；
  - US4 删除文献关联记录。
- 未完成 Task 编号：
  - US3：T037-T049；
  - US4：T050-T060；
  - Polish：T061-T068。
- 未完成原因：
  - 本轮范围仅限 US2；
  - 单篇重新解析、单篇重建索引、全量重建索引、删除关联记录和最终文档验收不在本轮范围内。
- 建议下一步：
  - 明确是否继续实现 US3：T037-T049；
  - US3 开始前再次确认分支、工作区和当前 tasks.md 状态；
  - 每完成一个 task 或阶段后同步更新本文件和根目录 `CURRENT_TASK.md`。

## 6. 测试记录

| 日期 | 分支 | 测试命令 | 测试结果 | 备注 |
|---|---|---|---|---|
| 2026-06-03 | MVP 功能分支 / `v2-dev` | `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_index_status.py tests/test_document_library.py -q` | 15 passed | MVP 阶段记录 |
| 2026-06-03 | MVP 功能分支 / `v2-dev` | `PYTHONPATH=. .venv/bin/pytest tests/test_acceptance.py -k "changed_files or manifest_saved" -q` | 1 passed, 38 deselected | manifest 兼容检查 |
| 2026-06-03 | MVP 功能分支 / `v2-dev` | `PYTHONPATH=. .venv/bin/pytest tests/test_acceptance.py::TestChunker -q` | 4 passed | chunker 兼容检查 |
| 2026-06-03 | MVP 功能分支 / `v2-dev` | `python3 -m py_compile app/parse_report.py app/index_status.py app/document_library.py app/chunker.py app/indexer.py ui/streamlit_app.py` | 通过 | 语法检查 |
| 2026-06-03 | `v2-dev` | `.venv/bin/python -m streamlit run ui/streamlit_app.py` | 待重新运行 | US2 开始前建议重新做 smoke test |
| 2026-06-03 | `feature/001-library-index-transparency-us2` | `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q` | 27 passed in 1.01s | US2 详情、chunk preview、失败字段相关测试通过 |
| 2026-06-03 | `feature/001-library-index-transparency-us2` | `.venv/bin/python -m py_compile app/parse_report.py app/indexer.py app/document_library.py ui/streamlit_app.py` | 通过 | US2 相关模块语法检查 |
| 2026-06-03 | `feature/001-library-index-transparency-us2` | `.venv/bin/python -m streamlit run ui/streamlit_app.py` | 成功启动，20 秒超时退出 | Streamlit smoke test，Local URL: `http://localhost:8502` |

## 7. 风险与注意事项

- 是否引入数据库：否，当前 MVP 未引入数据库；后续也禁止引入数据库。
- 是否修改 V1/V2 主流程：当前 MVP 未重写 V1/V2 主流程；后续必须继续保持。
- 是否影响已有文献查询入口：当前 MVP 保留已有文献查询入口；后续 UI 改动需回归验证。
- 是否影响文献综合入口：当前 MVP 保留 V2 文献综合入口；后续不得改变默认入口、参数和输出格式。
- 是否涉及 ChromaDB、BM25、parent store：MVP 已涉及索引状态展示和 manifest 兼容；US3、US4 将直接涉及索引重建和清理，风险更高。
- 是否涉及删除文献记录：MVP 未实现删除；US4 将涉及删除关联记录，必须逐项报告并默认不删除原始 PDF。
- 是否有未完成的测试：US2 相关 pytest 和启动 smoke 已完成；US3、US4、Polish 测试尚未在本轮验证。
- 是否有未提交或不应提交的 data 文件：当前记录未发现需要提交的 `data/` 文件；后续必须继续避免提交 `.env`、`data/chroma_db/`、BM25、parent store、manifest、parse_reports、output 和缓存。

## 8. 下一步计划

- 下一步如继续 Feature 001，应进入 US3：T037-T049 重新解析与重建索引；
- US3 开始前需要确认是否保留当前代码中已有的 US3/US4 实现痕迹，或按任务范围重新拆分；
- US3 开始前建议运行：
  - `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q`
  - `.venv/bin/python -m streamlit run ui/streamlit_app.py`
- 每完成一个需求、阶段、User Story 或 task 后，必须同步更新 `specs/001-library-index-transparency/PROGRESS.md` 和根目录 `CURRENT_TASK.md`。

## 9. 强制更新规则

每次完成一个需求、阶段、User Story 或 task 后，必须同步更新进度文档。

更新内容至少包括：

1. 本次完成了哪些 task 编号；
2. 当前进行到 tasks.md 的哪个 Phase / User Story；
3. 还有哪些 task 没完成；
4. 修改了哪些文件；
5. 执行了哪些测试命令；
6. 测试是否通过；
7. 是否做了 Streamlit 手动 smoke test；
8. 是否存在风险；
9. 下一步建议；
10. 是否已经提交、合并、push。

如果只完成部分任务，不得声称整个 Feature 已完成。
