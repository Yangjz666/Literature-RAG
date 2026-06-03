# Feature 001 开发进度：文献库管理与索引透明化

## Feature 基本信息

- Feature：`001-library-index-transparency`
- 名称：文献库管理与索引透明化
- 当前分支：`v2-dev`
- 当前状态：US3 merge 收尾中
- 本轮限制：只处理 merge 冲突、测试、进度文档同步和 `git add`；不执行 git commit，不执行 git push
- 当前完成到：Phase 5 / US3，T001-T049
- 剩余任务：US4 T050-T060；Polish T061-T068

## 总体目标

本 Feature 为 CO2RR Literature RAG Agent 增加文献库管理与索引透明化能力：

- 查看本地 PDF/SI 文献库列表；
- 聚合 manifest、parse_report 和 index_status；
- 查看单篇详情、parse_report、chunk preview、索引阶段和失败原因；
- 支持单篇重新解析；
- 支持单篇重建索引；
- 支持全量重建索引；
- 后续支持删除文献关联记录但默认不删除原始 PDF。

本 Feature 不引入数据库、FastAPI、Docker、完整 Debug Trace、citation verification 或联网下载能力。

## 阶段进度

| Phase | User Story | Tasks | 状态 | 说明 |
| --- | --- | --- | --- | --- |
| Phase 1 | Setup | T001-T004 | 已完成 | 开发范围、分支、路径和安全边界已确认 |
| Phase 2 | Foundational | T005-T015 | 已完成 | parse_report、index_status、operation summary 基础能力已实现 |
| Phase 3 | US1 | T016-T027 | 已完成 | 文献库列表、筛选和 V1/V2 入口兼容已实现 |
| Phase 4 | US2 | T028-T036 | 已完成 | 单篇详情、parse_report、chunk preview、failure_stage / failure_reason 展示已实现 |
| Phase 5 | US3 | T037-T049 | 已完成 | 单篇重新解析、单篇重建索引、全量重建索引和操作摘要已合入 |
| Phase 6 | US4 | T050-T060 | 未完成 | 删除文献关联记录仍待继续实现/验收 |
| Phase 7 | Polish | T061-T068 | 未完成 | 用户文档、README、完整回归和最终验收仍待完成 |

## 本轮 Merge 冲突处理

本轮正在将 001-library-index-transparency / US3 改动合并到 `v2-dev`，目标是保留 `v2-dev` 上已有 US1/US2 能力，同时合入 US3 能力。

冲突文件：

- `CURRENT_TASK.md`
- `app/document_library.py`
- `app/index_status.py`
- `app/indexer.py`
- `specs/001-library-index-transparency/PROGRESS.md`
- `tests/test_index_status.py`
- `tests/test_parse_report.py`
- `ui/streamlit_app.py`

合并原则：

- 不简单选择 current 或 incoming；
- 后端按模块边界合并，保留列表、详情、chunk preview、删除辅助和 US3 reparse/rebuild 能力；
- 测试保留旧测试并合入 US3 新测试；
- UI 保留文献查询入口、文献库管理、单篇详情，同时展示单篇重新解析、单篇重建索引、全量重建索引和 operation summary；
- 不删除原始 PDF，不修改 `.env`，不修改 `data/`。

## 已完成内容

- T001-T015：基础 Speckit、parse_report、index_status、operation summary 能力。
- T016-T027：文献库列表 MVP、筛选、manifest 兼容、V1/V2 入口保留。
- T028-T036：单篇详情、parse_report detail、chunk preview、failure_stage / failure_reason 展示。
- T037-T049：单篇重新解析、单篇重建索引、全量重建索引、操作结果摘要、失败阶段/原因记录，且单篇操作不调用全库重建路径。

## 未完成任务

- US4 T050-T060：删除文献关联记录、manifest/parse_report/index_status/ChromaDB/BM25/parent store 清理、UI 确认与逐项结果展示。
- Polish T061-T068：用户文档、README/V3 文档同步、完整回归测试记录、安全检查和最终交付总结。

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-03 | `v2-dev` | `.venv/bin/python -m py_compile app/ingest.py app/indexer.py app/document_library.py app/index_status.py ui/streamlit_app.py` | 通过，无输出 | 冲突解决后的语法检查 |
| 2026-06-03 | `v2-dev` | `.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q` | 30 passed in 0.81s | parse_report、document_library、index_status 相关测试 |
| 2026-06-03 | `v2-dev` | `.venv/bin/python -m pytest` | 147 passed in 1.06s | 完整测试 |

## 手动 Smoke Test

- Streamlit 浏览器内手动点击验证：未完成。
- 本轮只运行自动化测试，不声称 UI 已完成手动验证。
- 需要用户后续手动检查文献查询入口、文献库管理、单篇详情、chunk preview、US3 三个按钮和 operation summary 展示。

## Git 状态

- 是否执行 git commit：否，按用户临时要求不执行。
- 是否执行 git push：否，按用户临时要求不执行。
- 是否已完成 merge commit：否，待用户手动提交。
- 是否已合并回开发基线：当前处于 `v2-dev` MERGING 状态，待冲突解决和用户手动 merge commit。

## 风险与注意事项

- 自动测试不依赖真实 API Key、真实 PDF 库或真实 ChromaDB，因此不能替代本地真实数据上的 UI 操作验收。
- 单篇重建索引需要读取目标 PDF 以生成 chunk，但该路径不写 parse_report，不触发全量重建。
- 全量重建必须用户明确点击按钮才会触发。
- 后续 US4 删除关联记录必须继续保证默认不删除原始 PDF。
- 不得提交 `.env`、API Key、`data/` 运行产物、ChromaDB、BM25 pickle 或 parent store。

## 下一步计划

1. `git add` 标记冲突已解决，不执行 commit/push。
2. 用户手动完成 merge commit 和 push。
3. 手动打开 Streamlit，检查文献查询入口、文献库管理页、单篇详情和 US3 三个操作入口。
4. 后续继续 US4 T050-T060，再做 Polish T061-T068。
