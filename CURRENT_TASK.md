# CURRENT_TASK.md

## 当前任务

继续完成 `Feature 001：文献库管理与索引透明化` 中 MVP 之后的剩余任务，范围限定为 `specs/001-library-index-transparency/tasks.md` 的 US2、US3、US4 和 Polish。

明确未做：完整 Debug Trace、citation verification、FastAPI、Docker、数据库、联网下载文献、删除原始 PDF、V1/V2 主流程重写。

## 本次完成内容

- US2 文献详情页：支持从文献库列表选择单篇文献，展示 parse_report 摘要、原始 JSON、index_status、失败阶段、失败原因、最近一次操作和 chunk 预览。
- US3 重新解析与重建索引：支持单篇重新解析、单篇重建索引和全量重建索引；单篇重新解析与单篇重建索引为独立操作；单篇操作不调用全库重建路径。
- US3 失败保护：重新解析失败时保留旧 parse_report；单篇重建索引失败时保留旧 `indexed` 状态，并记录失败阶段和原因。
- US4 删除关联记录：支持删除 manifest、parse_report、ChromaDB、BM25、parent store、index_status 的关联记录，逐项显示 `success` / `failed` / `skipped` 和原因；默认不删除原始 PDF。
- Polish：新增 `README.md`、`docs/document_library.md`，更新 `CO2RR_RAG_Agent_PRD_V3.md` 和 `specs/001-library-index-transparency/tasks.md`。

## 测试结果

```bash
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_index_status.py tests/test_document_library.py -q
```

功能分支结果：`27 passed in 1.04s`

合并到 `v2-dev` 后结果：`27 passed in 1.14s`

```bash
.venv/bin/python -m py_compile app/parse_report.py app/index_status.py app/document_library.py app/ingest.py app/indexer.py ui/streamlit_app.py
```

功能分支与合并后结果：通过。

```bash
.venv/bin/python -m pytest tests/test_acceptance.py::TestChunker tests/test_v2_router.py tests/test_v2_pipeline.py -q
```

功能分支结果：`23 passed in 0.17s`

合并到 `v2-dev` 后结果：`23 passed in 0.24s`

```bash
timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8502
```

普通沙箱结果：因本地 socket 权限限制失败，`PermissionError: [Errno 1] Operation not permitted`。

提升权限后结果：Streamlit 成功启动，显示 `Local URL: http://localhost:8502`，20 秒超时退出为 smoke test 预期结束。

合并到 `v2-dev` 后再次提升权限 smoke test：Streamlit 成功启动，显示 `Local URL: http://localhost:8502`，20 秒超时退出为预期结束。

## Git 与基线检查

- 当前功能分支：`feature/001-library-index-transparency-complete`。
- 开发基线分支：`v2-dev`。
- 开发前 `git status`：干净。
- 本地 `feature/001-library-index-transparency-complete`、`v2-dev`、`origin/v2-dev` 均指向 `5466f50`。
- `git merge-base --is-ancestor v2-dev HEAD`：通过。
- `git fetch origin v2-dev`：在受限网络环境中长时间无响应，未完成实时远端确认；本次基于本地 `origin/v2-dev` 判断。

## 安全与范围核对

- 未引入数据库、FastAPI、Docker、完整 Debug Trace 或 citation verification。
- 未联网下载文献。
- 未删除原始 PDF 文件。
- 未改写 V1/V2 查询主流程、结构化抽取入口或文献综合入口。
- `.gitignore` 已覆盖 `.env`、`data/chroma_db/`、BM25/parent store、`data/index_manifest.json`、`data/index_status.json`、`data/parse_reports/`、`data/output/`、缓存和本地评测数据。

## 已知风险

- 文献库详情页的 chunk 预览依赖现有 `LiteratureIndex` 初始化；如果本机 Embedding 配置缺失，页面会显示状态和 parse_report，但 chunk 预览和索引操作受限。
- 单篇重建索引已调整为先写新 chunk，成功后清理 stale chunk，以降低失败破坏旧索引的风险；真实 ChromaDB 端到端删除/重建仍建议用小型本地样本手动验收。
- 全量重建仍复用现有 `load_folder()` 和索引存储格式，未做新的并发或事务层。

## 标准交付检查清单

```text
当前功能：Feature 001 文献库管理与索引透明化剩余任务
开发基线分支：v2-dev
功能分支：feature/001-library-index-transparency-complete
开发前 git status 是否干净：是
是否从正确基线分支创建：本地验证 feature 基于 v2-dev；实时 fetch 未完成
功能分支测试是否通过：是
测试命令：.venv/bin/python -m pytest tests/test_parse_report.py tests/test_index_status.py tests/test_document_library.py -q
手动 smoke test 是否完成：已完成 Streamlit 启动 smoke；未用真实 PDF/Embedding 做手动索引流程
是否已提交功能分支：是，467fd2f feat: complete library index transparency
是否已合并回开发基线分支：是，合并到 v2-dev
合并后测试是否通过：是
合并后测试命令：.venv/bin/python -m pytest tests/test_parse_report.py tests/test_index_status.py tests/test_document_library.py -q；.venv/bin/python -m pytest tests/test_acceptance.py::TestChunker tests/test_v2_router.py tests/test_v2_pipeline.py -q；Streamlit smoke test
是否已 push：未完成；`git push origin v2-dev` 无输出阻塞，提升权限后 `timeout 60 git push origin v2-dev` 仍超时
未提交文件是否只包含可忽略本地数据：工作区干净，无未提交文件
已知风险：Embedding 配置缺失时 chunk 预览/索引操作受限；真实 ChromaDB 端到端需小样本复验
后续建议：合并后用一篇小 PDF 做文献详情、单篇重建和删除关联记录手工验收
```
