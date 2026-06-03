# CURRENT_TASK.md

## 当前 Feature：001-library-index-transparency

- Feature 名称：文献库管理与索引透明化
- Feature 目录：`specs/001-library-index-transparency/`
- 当前分支：`feature/001-library-index-transparency-us4`
- 当前阶段：Phase 6 / US4 删除文献及关联记录
- 当前完成范围：T001-T060
- 本轮完成任务：T050-T060
- 剩余任务：Polish T061-T068
- 本轮限制：不执行 git commit，不执行 merge，不执行 git push，由用户手动提交、合并和 push

## 本次完成内容

- 实现删除文献关联记录的逐项摘要增强：
  - `manifest`
  - `parse_report`
  - `chunks`
  - `vector_index`
  - `keyword_index`
  - `parent_store`
  - `index_status`
- 删除操作默认不删除原始 PDF 文件。
- 删除操作失败时按项返回 `success` / `failed` / `skipped` 和 `reason`，不会因为单项失败导致整个流程崩溃。
- 删除后保存 delete operation summary。
- 删除后文献库状态会回落为本地 PDF 的未解析/未索引状态，旧 `document_id`、manifest、parse_report 和 index_status 记录被清理。
- UI 删除区继续要求输入文件名确认，并新增主文献 / Supporting Information 关联影响提示。
- 新增索引层删除测试，覆盖按 `document_id` 删除 ChromaDB 记录、BM25 重建和 parent store 清理。

## 修改文件

- `app/document_library.py`
- `ui/streamlit_app.py`
- `tests/test_document_library.py`
- `tests/test_indexer_delete.py`
- `CURRENT_TASK.md`
- `specs/001-library-index-transparency/PROGRESS.md`

## 已完成任务

- Phase 1：Setup，T001-T004
- Phase 2：Foundational，T005-T015
- Phase 3：US1 文献库列表 MVP，T016-T027
- Phase 4：US2 单篇文献详情页，T028-T036
- Phase 5：US3 重新解析与重建索引，T037-T049
- Phase 6：US4 删除文献及关联记录，T050-T060

## 未完成任务

- Polish T061-T068：
  - 用户文档和 README 同步；
  - V3 规划文档同步；
  - 最终回归和安全检查；
  - 完整交付总结。

## 测试记录

```bash
.venv/bin/python -m py_compile app/indexer.py app/document_library.py app/index_status.py app/parse_report.py ui/streamlit_app.py
```

结果：通过，无输出

```bash
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py tests/test_indexer_delete.py -q
```

结果：32 passed in 0.69s

```bash
.venv/bin/python -m pytest
```

结果：149 passed in 1.01s

```bash
timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8501
```

结果：Streamlit 启动成功，显示 Local URL `http://localhost:8501`，20 秒 timeout 后正常停止；未进行浏览器内手动点击验证。

## Streamlit Smoke Test

- 自动启动 smoke：已完成。
- 浏览器内手动点击删除按钮：未完成，需要用户后续验证。
- 建议手动检查：
  - 文献库管理页面能打开；
  - 单篇详情页删除区显示“不会删除原始 PDF”的提示；
  - 删除前必须输入文件名确认；
  - 删除后逐项显示 manifest、parse_report、chunks、vector_index、keyword_index、parent_store、index_status 的结果；
  - 部分失败时能看到失败项和原因；
  - 删除后的文献不再通过旧索引参与检索。

## Git 状态

- 是否执行 git commit：否，本轮按用户要求不执行
- 是否执行 merge：否，本轮按用户要求不执行
- 是否执行 git push：否，本轮按用户要求不执行

## 已知风险

- 自动测试使用 fake collection / 临时文件，不会触碰真实 ChromaDB、真实 PDF 库或真实 API Key。
- 真实删除操作仍建议先在小型测试文献夹验证。
- 如果 ChromaDB、BM25 或 parent store 某项清理失败，系统会报告 partial，但用户需要根据失败原因决定是否重试或手动修复。
- 原始 PDF 默认保留，因此删除关联记录后如果继续扫描本地文件夹，该 PDF 会以未解析/未索引状态重新出现在文献库列表中。

## 下一步建议

1. 用户手动检查 `git diff`。
2. 用户手动提交当前 US4 改动。
3. 用户手动合并回 `v2-dev` 并 push。
4. 后续进入 Polish T061-T068。

## 强制更新规则

每次完成一个需求、阶段、User Story 或 task 后，必须同步更新 `CURRENT_TASK.md` 和 `specs/001-library-index-transparency/PROGRESS.md`，记录完成 task、测试命令、测试结果、风险、下一步建议以及提交/合并/push 状态。
