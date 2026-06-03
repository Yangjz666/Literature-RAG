# CURRENT_TASK.md

## 当前 Feature：001-library-index-transparency

- Feature 名称：文献库管理与索引透明化
- Feature 目录：`specs/001-library-index-transparency/`
- 当前分支：`feature/001-library-index-transparency-polish`
- 当前阶段：Phase 7 / Polish
- 当前完成范围：T001-T068
- 本轮完成任务：T061-T068
- Feature 状态：T001-T068 已完成，测试通过，等待用户手动提交
- 本轮限制：不执行 git commit，不执行 merge，不执行 git push，由用户手动提交、合并和 push

## Feature 001 已完成能力

- 文献库列表：聚合本地 PDF/SI、manifest、parse_report 和 index_status。
- 单篇文献详情：展示 parse_report 摘要、原始 JSON、index_status、failure_stage、failure_reason、latest operation 和 chunk preview。
- 单篇重新解析：只处理当前文献，失败时保留旧 parse_report。
- 单篇重建索引：只重建当前文献索引，不触发全库重建。
- 全量重建索引：用户明确点击后执行，显示进度和摘要。
- 删除文献关联记录：逐项清理 manifest、parse_report、chunks、ChromaDB、BM25、parent store 和 index_status。
- 删除保护：删除关联记录默认不会删除原始 PDF。
- 文档收尾：README、用户文档、V3 PRD、tasks、PROGRESS 和 CURRENT_TASK 已同步。

## 本轮完成内容

- T061：更新 `docs/document_library.md`，补齐页面用途、字段、状态、单篇重新解析、单篇重建索引、全量重建索引、删除行为和限制。
- T062：更新 `README.md`，增加 Feature 001 能力、运行、测试和限制说明。
- T063：更新 `CO2RR_RAG_Agent_PRD_V3.md`，同步 Feature 001 已实现范围和排除范围。
- T064：运行 Feature 001 相关 pytest 并记录结果。
- T065：运行完整 pytest 和 Streamlit 启动 smoke test，覆盖 V1/V2 入口的回归风险。
- T066：确认本 Feature 未新增完整 Debug Trace、citation verification、FastAPI、Docker、数据库、联网下载或 V1/V2 主流程重写。
- T067：检查不应提交内容，确认本轮普通 `git status` 未出现 `.env`、`data/`、`.venv`、缓存、本地索引或本地 PDF 待提交。
- T068：汇总修改文件、测试、风险和后续建议。

## 修改文件

- `README.md`
- `docs/document_library.md`
- `CO2RR_RAG_Agent_PRD_V3.md`
- `CURRENT_TASK.md`
- `specs/001-library-index-transparency/PROGRESS.md`
- `specs/001-library-index-transparency/tasks.md`

## 已完成任务

- Phase 1：Setup，T001-T004
- Phase 2：Foundational，T005-T015
- Phase 3：US1 文献库列表 MVP，T016-T027
- Phase 4：US2 单篇文献详情页，T028-T036
- Phase 5：US3 重新解析与重建索引，T037-T049
- Phase 6：US4 删除文献及关联记录，T050-T060
- Phase 7：Polish，T061-T068

## 未完成任务

- Feature 001 范围内无未完成 task。
- 浏览器内真实点击验证仍建议由用户手动执行。

## 测试记录

```bash
.venv/bin/python -m py_compile app/indexer.py app/document_library.py app/index_status.py app/parse_report.py ui/streamlit_app.py
```

结果：通过，无输出

```bash
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py tests/test_indexer_delete.py -q
```

结果：32 passed in 0.83s

```bash
.venv/bin/python -m pytest
```

结果：149 passed in 1.19s

```bash
timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8501
```

结果：Streamlit 成功启动并显示 Local URL `http://localhost:8501`，20 秒 timeout 后停止；未做浏览器内手动点击验证。

## Streamlit 手动验证建议

自动 smoke test 只能确认应用可启动。用户仍需手动打开页面检查：

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
- 安全检查发现仓库存在被 ignore 的本地 `.env`、`.venv`、缓存、`data/chroma_db` 和本地 PDF 产物；它们未进入普通 `git status` 待提交区，本轮不会建议提交。
- `git ls-files` 显示历史上已有 `data/test_literature/README.md` 和一个 Zone.Identifier 文件被跟踪；本轮未修改它们，建议后续单独评估是否移出 Git 跟踪。

## 已知风险

- 真实索引操作依赖 Embedding API 配置，自动测试不触碰真实 API Key。
- 真实 ChromaDB、BM25 和 parent store 清理建议先在小型测试文献夹中手动验证。
- 删除关联记录默认保留原始 PDF；如果本地 PDF 仍在目录中，重新扫描时会以未解析/未索引状态重新出现在列表中。
- Streamlit 自动启动 smoke 不等于浏览器内真实点击验收。

## 下一步建议

1. 用户手动检查 `git diff`。
2. 用户手动提交当前 Polish 改动。
3. 用户手动合并回 `v2-dev` 并 push。
4. 使用小型测试文献夹做浏览器内手动验收。

## Git 状态

- 是否执行 git commit：否，本轮按用户要求不执行
- 是否执行 merge：否，本轮按用户要求不执行
- 是否执行 git push：否，本轮按用户要求不执行

## 强制更新规则

每次完成一个需求、阶段、User Story 或 task 后，必须同步更新 `CURRENT_TASK.md` 和 `specs/001-library-index-transparency/PROGRESS.md`，记录完成 task、测试命令、测试结果、风险、下一步建议以及提交/合并/push 状态。
