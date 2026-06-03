# Feature 001 开发进度：文献库管理与索引透明化

## Feature 基本信息

- Feature：`001-library-index-transparency`
- 名称：文献库管理与索引透明化
- 当前分支：`feature/001-library-index-transparency-us4`
- 当前阶段：Phase 6 / US4 删除文献及关联记录
- 当前完成到：T001-T060
- 本轮完成任务：T050-T060
- 剩余任务：Polish T061-T068
- 本轮限制：不执行 git commit，不执行 merge，不执行 git push，由用户手动提交、合并和 push

## 总体目标

本 Feature 为 CO2RR Literature RAG Agent 增加文献库管理与索引透明化能力：

- 查看本地 PDF/SI 文献库列表；
- 聚合 manifest、parse_report 和 index_status；
- 查看单篇详情、parse_report、chunk preview、索引阶段和失败原因；
- 支持单篇重新解析；
- 支持单篇重建索引；
- 支持全量重建索引；
- 支持删除文献关联记录，默认不删除原始 PDF。

本 Feature 不引入数据库、FastAPI、Docker、完整 Debug Trace、citation verification 或联网下载能力。

## 阶段进度

| Phase | User Story | Tasks | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| Phase 1 | Setup | T001-T004 | 已完成 | 开发范围、分支、路径和安全边界已确认 |
| Phase 2 | Foundational | T005-T015 | 已完成 | parse_report、index_status、operation summary 基础能力已实现 |
| Phase 3 | US1 | T016-T027 | 已完成 | 文献库列表、筛选和 V1/V2 入口兼容已实现 |
| Phase 4 | US2 | T028-T036 | 已完成 | 单篇详情、parse_report、chunk preview、failure_stage / failure_reason 展示已实现 |
| Phase 5 | US3 | T037-T049 | 已完成 | 单篇重新解析、单篇重建索引、全量重建索引和操作摘要已实现 |
| Phase 6 | US4 | T050-T060 | 已完成 | 删除文献关联记录、逐项清理摘要、UI 确认和测试已完成 |
| Phase 7 | Polish | T061-T068 | 未完成 | 用户文档、README、完整回归和最终验收仍待完成 |

## 本轮完成内容

- T050：补充删除操作结果形状和 partial failure 测试。
- T051：覆盖 index_status cleanup 与 delete operation summary 持久化。
- T052：覆盖 manifest / parse_report 清理和删除后文献库状态回落。
- T053：复用 `delete_parse_report()` 删除单篇 parse_report，不删除 PDF。
- T054：复用 `remove_manifest_entry()` 按 `document_id` / filename 删除 manifest 记录。
- T055：复用 `LiteratureIndex.remove_document_records()` 删除 ChromaDB vector records。
- T056：删除后重建 BM25，并返回 `keyword_index` 清理摘要。
- T057：按 `document_id` / filename 清理 parent store。
- T058：增强 `delete_document_records()`，按项返回 `success` / `failed` / `skipped` 和 `reason`，并新增 `chunks` 分项。
- T059：文献详情页删除入口要求输入文件名确认，提示不会删除原始 PDF，并提示主文献 / SI 关联影响。
- T060：删除操作默认不删除原始 PDF，测试覆盖 `pdf.exists()`。

## 修改文件

- `app/document_library.py`
- `ui/streamlit_app.py`
- `tests/test_document_library.py`
- `tests/test_indexer_delete.py`
- `CURRENT_TASK.md`
- `specs/001-library-index-transparency/PROGRESS.md`

## 未完成任务

- Polish T061-T068：
  - 用户文档和 README 同步；
  - V3 规划文档同步；
  - 最终回归和安全检查；
  - 完整交付总结。

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-03 | `feature/001-library-index-transparency-us4` | `.venv/bin/python -m py_compile app/indexer.py app/document_library.py app/index_status.py app/parse_report.py ui/streamlit_app.py` | 通过，无输出 | US4 相关模块语法检查 |
| 2026-06-03 | `feature/001-library-index-transparency-us4` | `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py tests/test_indexer_delete.py -q` | 32 passed in 0.69s | US4 相关测试和基础状态测试 |
| 2026-06-03 | `feature/001-library-index-transparency-us4` | `.venv/bin/python -m pytest` | 149 passed in 1.01s | 完整回归测试 |
| 2026-06-03 | `feature/001-library-index-transparency-us4` | `timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8501` | 启动成功，timeout 停止 | Streamlit Local URL 显示为 `http://localhost:8501`，未做浏览器内手动点击 |

## Streamlit Smoke Test

- 自动启动 smoke：已完成。
- 浏览器内手动点击删除按钮：未完成。
- 需要用户后续手动检查：
  - 文献库管理页可打开；
  - 单篇详情页删除区提示不会删除原始 PDF；
  - 删除前必须输入文件名确认；
  - 删除后逐项显示 manifest、parse_report、chunks、vector_index、keyword_index、parent_store、index_status 的结果；
  - 部分失败时显示失败项和原因；
  - 删除后的文献不再通过旧索引参与检索。

## Git 状态

- 是否执行 git commit：否，按用户要求不执行。
- 是否执行 merge：否，按用户要求不执行。
- 是否执行 git push：否，按用户要求不执行。

## 风险与注意事项

- 自动测试不依赖真实 API Key、真实 PDF 库或真实 ChromaDB，因此不能替代真实数据上的 UI 删除验收。
- 原始 PDF 默认保留，因此删除关联记录后继续扫描本地文件夹时，该 PDF 会以未解析/未索引状态重新出现在文献库列表中。
- 如果 ChromaDB、BM25 或 parent store 某项清理失败，summary 会返回 partial，用户需要根据失败原因重试或手动修复。
- 本轮未开发 Debug Trace、citation verification、FastAPI、Docker、数据库或联网下载功能。

## 下一步计划

1. 用户手动检查 `git diff`。
2. 用户手动提交当前 US4 改动。
3. 用户手动合并回 `v2-dev` 并 push。
4. 后续进入 Polish T061-T068。
