# CURRENT_TASK.md

## 当前任务：Feature 002 检索调试 Debug Trace

- 当前 Feature：`002-retrieval-debug-trace`
- Feature 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 第三批任务
- 当前任务类型：实现 T029-T036，增加 Streamlit Debug Trace 面板和 Raw JSON 展示
- 本轮修改文件：`app/debug_trace.py`、`ui/streamlit_app.py`、`tests/test_debug_trace.py`、`specs/002-retrieval-debug-trace/tasks.md`、`CURRENT_TASK.md`、`specs/002-retrieval-debug-trace/PROGRESS.md`
- 本轮限制：只实现 T029-T036；不实现 T037-T040 `session_state` 当前 trace；不做 T041-T050 文档收尾、最终 smoke test 和最终验收；不做 citation verification、claim-level verification、FastAPI、Docker、数据库、多用户、联网下载、GraphRAG 或主流程重写

## 本轮完成内容

- 完成 T029：新增 Debug Trace 表格数据 helper，支持 BM25、Vector、RRF、Reranker、Final context 和 Citation / Evidence 表格数据。
- 完成 T030：新增 helper 测试，覆盖 `not_available` 阶段、chunk 表格字段、citation 表格字段和 Raw JSON 可序列化。
- 完成 T031：在文献综合回答区域下方新增默认折叠的「检索调试 Debug Trace」面板。
- 完成 T032：展示 `trace_id`、`created_at`、`user_query`、`original_query`、`rewritten_query`、`query_mode`、`elapsed_ms`。
- 完成 T033：以表格展示 BM25、Vector、RRF、Reranker、Final context chunks，缺失阶段显示 `not_available`，只展示 `text_preview`。
- 完成 T034：展示 Citation / Evidence 的 `citation_id`、`filename`、`page`、`section`、`chunk_id`、`evidence_text_preview`、`match_status`，并明确本阶段不做真假判断或 claim-level verification。
- 完成 T035：展示 warning、error 和 failed_stage，不直接展示完整 traceback。
- 完成 T036：在面板底部提供 Raw JSON，默认不展开，通过 JSON-safe trace 展示。
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T029-T036 标记为 `[X]`。

## Feature 002 目标

本 Feature 为 CO2RR Literature RAG Agent V3 增加检索调试 Debug Trace 能力，让每次 RAG 查询的检索链路可观察、可调试、可展示。

核心目标：

- 用户可以看到一次查询中系统检索到了哪些文献片段；
- 开发者可以看到关键词检索、向量检索、融合排序、重排序和 final context 的中间结果；
- 用户可以判断最终回答是否基于真实检索上下文；
- RAG 出错时，可以定位失败发生在哪个阶段；
- 不重写现有 RAG 主流程，只做旁路记录和 UI 展示。

## 当前未完成任务

- T037-T040：错误处理降级和 `session_state` 当前 trace。
- T041-T044：用户文档和进度文档后续更新。
- T045-T050：最终语法检查、相关测试、完整 pytest、Streamlit smoke test、Git 安全检查和最终验收记录。
- 浏览器内手动点击验证：未完成，需要用户手动检查。

## 修改文件

- `app/debug_trace.py`
- `ui/streamlit_app.py`
- `tests/test_debug_trace.py`
- `specs/002-retrieval-debug-trace/tasks.md`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 本轮测试

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | 通过 | `tasks.md` 被 SpecKit 识别 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | checklist 统计 | 通过 | `requirements.md` 16/16 完成 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m py_compile ui/streamlit_app.py app/debug_trace.py` | 通过 | 语法检查通过 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest tests/test_debug_trace.py -q` | 通过 | 17 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest` | 通过 | 169 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py` | 通过启动，超时停止 | Streamlit 启动到 `http://localhost:8501`，未做浏览器点击验证 |

## 风险与注意事项

- Debug Trace 面板已展示文献综合路径的 `metadata["debug_trace"]`；结构化抽取路径仍未挂载 debug trace。
- T037-T040 尚未完成，当前还没有专门的 `session_state` 当前 trace 管理。
- Raw JSON 使用 checkbox 默认隐藏，避免在普通阅读流中打断用户。
- 浏览器内交互验证未完成，需要用户手动检查面板展开、表格显示和 Raw JSON。

## Git 操作状态

- 开发前 git status 是否干净：是。
- 当前功能分支：`feature/002-retrieval-debug-trace`。
- 是否执行 git commit：待执行。
- 是否执行 merge：待执行。
- 是否执行 push：否，本轮明确不 push。

## 下一步建议

按用户要求执行标准收尾流程：

1. 在功能分支提交本批 T029-T036。
2. 合并 `feature/002-retrieval-debug-trace` 到 `V3-DEV`。
3. 合并后重新运行测试。
4. 不执行 push，由用户手动 push `V3-DEV`。
