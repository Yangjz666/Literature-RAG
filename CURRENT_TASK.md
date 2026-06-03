# CURRENT_TASK.md

## 1. 当前任务

继续实现 Feature 001「文献库管理与索引透明化」的 Phase 5 / US3：重建解析与索引。

本次实现范围：

- T037-T039：补充单篇重新解析失败保留旧 parse_report、单篇索引状态边界、全量重建 summary 统计测试。
- T040-T042：新增单文件解析 wrapper、parse_report 写入能力、`reparse_document()` 单篇重新解析编排。
- T043-T046：新增单篇 chunk/index helper、单篇索引重建、index_status 阶段流转、全量重建逐篇 summary。
- T047-T049：在 Streamlit 文献库管理页增加单篇重新解析、单篇重建当前索引、全量重建索引三个独立入口。

本次明确不做：

- US4 删除文献及关联记录 T050-T060。
- Polish T061-T068。
- 新的 Debug Trace、citation verification、FastAPI、Docker、数据库或联网下载功能。
- git commit、merge、push。

## 2. 当前阶段

- 当前 Feature：`001-library-index-transparency`
- 当前进行到：Phase 5 / US3
- 已完成：MVP、US2、T001-T049
- 剩余任务：US4 T050-T060、Polish T061-T068

## 3. 本次完成内容

- `app/ingest.py` 新增 `parse_single_pdf()`，只解析单个 PDF，返回 pages、metadata、warnings、report、paper，且 `load_folder()` 默认行为保持不变。
- `app/document_library.py` 新增 `reparse_document()`，失败时保留旧 parse_report，并记录 failure_stage/failure_reason 和 diff summary。
- `app/index_status.py` 新增 operation summary 保存、reparse/rebuild 阶段记录、full rebuild 统计 summary helper。
- `app/indexer.py` 新增单篇 chunk helper、单篇索引重建、单文献旧 chunk 清理、全量逐篇重建 summary。
- `ui/streamlit_app.py` 在文献库管理页增加三个分开的操作入口，并展示操作结果 JSON summary。
- `specs/001-library-index-transparency/tasks.md` 勾选 T037-T049。

## 4. 修改文件

- `app/ingest.py`
- `app/document_library.py`
- `app/index_status.py`
- `app/indexer.py`
- `ui/streamlit_app.py`
- `tests/test_parse_report.py`
- `tests/test_index_status.py`
- `specs/001-library-index-transparency/tasks.md`
- `specs/001-library-index-transparency/PROGRESS.md`
- `CURRENT_TASK.md`

## 5. 测试记录

```bash
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q
```

结果：18 passed。

```bash
.venv/bin/python -m py_compile app/ingest.py app/indexer.py app/document_library.py app/index_status.py ui/streamlit_app.py
```

结果：通过，无输出。

```bash
timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8501
```

结果：Streamlit 成功启动并显示 Local URL `http://localhost:8501`，随后被 timeout 正常停止；未进行浏览器内手动点击验证。

## 6. 验收状态

- 单篇重新解析失败时，旧 parse_report 保留：已通过测试覆盖。
- 单篇重建索引状态只影响当前文献：已通过测试覆盖。
- 全量重建返回 success / failed / skipped 摘要：已通过测试覆盖。
- UI 三个操作入口分开：已实现并通过 Streamlit 启动 smoke test。
- 失败时展示 failure_stage 和 failure_reason：已在 operation summary 和 index_status 中记录，UI 以 JSON summary 展示。
- 不删除原始 PDF：本次未实现删除逻辑。
- 不破坏 US1/US2 和 V1/V2 查询入口：未改写查询入口；已做编译和启动 smoke test，仍建议手动点击回归。

## 7. 已知风险

- 单篇重建当前索引需要重新读取目标 PDF 以获得页面文本，但不会写 parse_report，也不会触发全库重建。
- Streamlit smoke test 只验证启动成功，未执行真实按钮点击；真实 embedding 配置、PDF 内容和 ChromaDB 状态仍需本地手动验证。
- 全量重建会按 `load_folder()` 读取当前文件夹内 PDF，用户必须明确点击“全量重建索引”按钮才会触发。

## 8. 下一步建议

1. 手动打开文献库管理页，选择一篇测试 PDF，分别点击“单篇重新解析”和“单篇重建当前索引”，确认 summary 中的 failure_stage/failure_reason 或 success 结果符合预期。
2. 使用小型测试文献夹点击“全量重建索引”，确认 success / failed / skipped 数量展示正确。
3. 继续实现 US4 T050-T060，删除关联记录仍必须保持“不删除原始 PDF”默认行为。
4. 最后再做 Polish T061-T068，包括用户文档、README 同步和完整回归记录。

## 9. Git 状态

- 本次未执行 git commit。
- 本次未执行 merge。
- 本次未执行 push。
