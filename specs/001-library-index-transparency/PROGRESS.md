# Feature 001 Progress: 文献库管理与索引透明化

## Feature 基本信息

- Feature：`001-library-index-transparency`
- 当前阶段：Phase 5 / US3 重建解析与索引
- 当前状态：T001-T049 已完成；Feature 尚未完整完成
- 本次范围：仅实现 T037-T049
- 明确排除：US4 删除文献、Polish、新 Debug Trace、citation verification、FastAPI、Docker、数据库、联网下载

## 总体目标

在不重写现有 RAG 查询链路、不引入数据库的前提下，提供文献库管理、解析报告可见、索引状态透明、单篇重解析、单篇重建索引、全量重建索引等本地管理能力。

## 阶段进度

- Phase 1 Setup：T001-T004 已完成
- Phase 2 Foundational：T005-T015 已完成
- Phase 3 US1 文献库状态列表：T016-T027 已完成
- Phase 4 US2 单篇详情：T028-T036 按当前进度说明已完成
- Phase 5 US3 重建解析与索引：T037-T049 已完成
- Phase 6 US4 删除文献及关联记录：T050-T060 未完成
- Phase 7 Polish：T061-T068 未完成

## 本次完成 Task

- T037：新增单篇重新解析失败时保留旧 parse_report 的测试。
- T038：新增单篇重建索引只更新目标 document_id 状态的测试。
- T039：新增全量重建 operation summary success / failed / skipped 统计测试。
- T040：新增 `parse_single_pdf()` 单文件解析 wrapper。
- T041：新增 success / partial / failed parse_report 写入能力。
- T042：实现 `reparse_document()`，失败时保留旧报告并返回 diff summary。
- T043：新增单篇文献 chunk helper。
- T044：实现单篇索引重建，复用 `chunk_paper()` 和 `LiteratureIndex.add_chunks()`。
- T045：新增 reparse/rebuild index_status 阶段流转和失败记录。
- T046：实现全量重建逐篇 progress summary。
- T047：文献库管理 UI 增加三个重建操作入口。
- T048：单篇重新解析和单篇重建索引为两个独立按钮。
- T049：单篇操作不调用全库重建路径。

## 修改文件

- `app/ingest.py`
- `app/document_library.py`
- `app/index_status.py`
- `app/indexer.py`
- `ui/streamlit_app.py`
- `tests/test_parse_report.py`
- `tests/test_index_status.py`
- `specs/001-library-index-transparency/tasks.md`
- `CURRENT_TASK.md`
- `specs/001-library-index-transparency/PROGRESS.md`

## 测试记录

```bash
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q
```

结果：18 passed。

```bash
.venv/bin/python -m py_compile app/ingest.py app/indexer.py app/document_library.py app/index_status.py ui/streamlit_app.py
```

结果：通过。

```bash
timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py --server.headless true --server.port 8501
```

结果：Streamlit 成功启动并显示 Local URL `http://localhost:8501`，随后被 timeout 停止。未做浏览器内手动点击验证。

## 风险与注意事项

- 单篇重建当前索引为了生成 chunk，需要读取目标 PDF 的页面文本；该路径不会写 parse_report，也不会触发全量重建。
- 单篇重新解析失败时不会覆盖旧 parse_report，失败详情记录在 operation summary 和 index_status。
- 真实按钮点击仍依赖本地 PDF、embedding 配置和 ChromaDB 状态，建议用户手动验证。
- 本次没有实现删除关联记录，因此不会删除原始 PDF。

## 剩余任务

- US4 T050-T060：删除文献及关联记录，要求默认不删除原始 PDF。
- Polish T061-T068：文档、README、V1/V2 回归记录、范围与安全检查。

## 下一步计划

1. 手动验证文献库管理页三个按钮的真实交互。
2. 使用小型测试文献夹验证全量重建 summary。
3. 继续实现 US4 删除关联记录。
4. 最后完成 Polish 文档和回归。

## 提交状态

- 未执行 git commit。
- 未执行 merge。
- 未执行 push。
