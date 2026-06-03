# CURRENT_TASK.md

## 当前 Feature：001-library-index-transparency

- Feature 名称：文献库管理与索引透明化
- Feature 目录：`specs/001-library-index-transparency/`
- 当前状态：US2 已完成并通过本轮验证，完整 Feature 未完成
- 当前进度：已完成 Phase 1、Phase 2、US1、US2，T001-T036
- 下一阶段：US3 重新解析与重建索引，T037-T049
- 未完成任务：
  - US3：T037-T049
  - US4：T050-T060
  - Polish：T061-T068
- 测试状态：
  - MVP 相关测试记录：15 passed；
  - manifest 兼容测试记录：1 passed，38 deselected；
  - chunker 兼容测试记录：4 passed；
  - 语法编译检查通过；
  - US2 本轮测试：`.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q`，27 passed in 1.01s；
  - US2 语法检查：`.venv/bin/python -m py_compile app/parse_report.py app/indexer.py app/document_library.py ui/streamlit_app.py`，通过；
  - Streamlit smoke test：成功启动到 `http://localhost:8502`，20 秒超时退出为预期结束。
- 已知风险：
  - US3 和 US4 会涉及索引重建和删除关联记录，风险高于 MVP；
  - 需要确保不删除原始 PDF；
  - 需要确保不提交 `data/` 本地运行数据；
  - 需要保持 V1 结构化抽取入口和 V2 文献综合入口不被破坏。
- 下一步建议：
  - 明确是否继续 US3：T037-T049；
  - US3 开始前确认当前代码与 tasks.md 状态是否需要回退、拆分或继续；
  - 完成后运行 pytest 和 Streamlit smoke test；
  - 更新 `specs/001-library-index-transparency/PROGRESS.md` 和 `CURRENT_TASK.md`。

## Feature 001 当前完成范围

已完成：

- Phase 1：Setup，T001-T004；
- Phase 2：Foundational，T005-T015；
- Phase 3：US1 文献库列表 MVP，T016-T027。
- Phase 4：US2 单篇文献详情页，T028-T036。

未完成：

- Phase 5：US3 重新解析与重建索引，T037-T049；
- Phase 6：US4 删除文献关联记录，T050-T060；
- Phase 7：Polish 文档、测试、验收、安全检查，T061-T068。

当前已完成 MVP 和 US2，完整 Feature 尚未完成。

## 最近进度记录

### 2026-06-03：完成并验证 US2 单篇文献详情页

- 完成 task：T028-T036
- 当前 Phase / User Story：Phase 4 / US2
- 完成内容：
  - parse_report detail loading 测试和读取接口；
  - document detail item 测试，包括 chunk preview 和 index failure 字段；
  - 单篇文献 chunk preview 查询；
  - 单篇文献详情聚合；
  - Streamlit 文献选择和详情面板；
  - parse_report 摘要、原始 JSON、chunk preview、index stage、failure stage、failure reason、latest operation 展示。
- 修改文件：
  - 本轮未修改业务代码，验证当前代码中已有 US2 实现；
  - `specs/001-library-index-transparency/PROGRESS.md`
  - `CURRENT_TASK.md`
- 测试命令：
  - `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q`
  - `.venv/bin/python -m py_compile app/parse_report.py app/indexer.py app/document_library.py ui/streamlit_app.py`
  - `.venv/bin/python -m streamlit run ui/streamlit_app.py`
- 测试结果：
  - 27 passed in 1.01s；
  - 语法检查通过；
  - Streamlit 成功启动到 `http://localhost:8502`，20 秒超时退出为预期结束。
- 手动 smoke test：已完成启动 smoke；未使用真实 PDF/Embedding 做详情页人工点击验收。
- 是否提交：否，本轮按要求不执行 git commit
- 是否合并：否，本轮未合并
- 是否 push：否，本轮按要求不执行 git push
- 尚未完成 task：
  - US3：T037-T049
  - US4：T050-T060
  - Polish：T061-T068
- 已知风险：
  - 当前仓库代码中已存在 US3/US4 相关实现痕迹，但本轮未新增、未修改、未验证 US3/US4；
  - chunk preview 依赖本地 ChromaDB / parent store 和 embedding 配置可用；
  - 未用真实文献库手动点击验证详情页。
- 下一步建议：
  - 明确是否继续 US3：T037-T049；
  - US3 开始前确认当前代码与 tasks.md 状态是否需要回退、拆分或继续。

### 2026-06-03：初始化 Feature 001 进度文档

- 完成 task：文档维护任务；不改变 `tasks.md` 任务完成状态
- 完成内容：
  - 新增 `specs/001-library-index-transparency/PROGRESS.md`；
  - 更新根目录 `CURRENT_TASK.md`；
  - 明确当前按 MVP 状态记录：T001-T027 已完成，T028-T068 未完成；
  - 加入后续 task 完成后的强制进度更新规则。
- 修改文件：
  - `specs/001-library-index-transparency/PROGRESS.md`
  - `CURRENT_TASK.md`
- 测试命令：未运行，文档更新无业务代码改动
- 测试结果：待重新运行
- 手动 smoke test：未运行
- 是否提交：否，本次按要求不执行 git commit
- 是否合并：否，本次按要求不执行合并
- 是否 push：否，本次按要求不执行 git push
- 已知风险：
  - 当前仍需实现 US2、US3、US4 和 Polish；
  - 后续 US3/US4 触及索引重建和删除关联记录，需要小步实现和测试。
- 下一步建议：
  - 从 `v2-dev` 创建 `feature/001-library-index-transparency-complete`；
  - 先实现 US2：T028-T036 单篇文献详情页；
  - 每完成 task 后同步更新 `PROGRESS.md` 和 `CURRENT_TASK.md`。

## 强制更新规则

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
