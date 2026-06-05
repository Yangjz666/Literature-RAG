# CURRENT_TASK.md

## 当前任务：Feature 002 检索调试 Debug Trace

- 当前 Feature：`002-retrieval-debug-trace`
- Feature 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 收尾
- 当前任务类型：完成 T037-T050，执行错误降级、session_state 当前 trace、文档收尾、最终测试和验收
- Feature 状态：T001-T050 已完成实现与测试；等待本轮提交、合并回 `V3-DEV`；本轮不执行 push

## 本轮完成内容

- 完成 T037：新增 Debug Trace 失败降级测试，确认 trace 记录失败只转为 warning，不影响主回答输出。
- 完成 T038：新增 `safe_trace_call()` 和 `record_warning()`，并在 V2 pipeline、retriever candidate 路径和 Streamlit 查询入口使用安全包装。
- 完成 T039：新增连续两次查询 trace 不混淆测试，确认 `trace_id`、`final_context_chunks` 和 `citations_used` 分离。
- 完成 T040：Streamlit 使用 `st.session_state["current_debug_trace"]` 保存当前 trace；每次新查询先清空，再覆盖为本轮 trace；默认不落盘。
- 完成 T041：新增 `docs/retrieval_debug.md`。
- 完成 T042：更新 `README.md`，补充 Debug Trace 面板入口和注意事项。
- 完成 T043-T044：同步更新 `CURRENT_TASK.md` 和 `specs/002-retrieval-debug-trace/PROGRESS.md`。
- 完成 T045-T048：已运行语法检查、Debug Trace 单测、完整 pytest 和 Streamlit smoke test。
- 完成 T049：Git 安全检查确认 `.env`、`data/`、`.venv/`、缓存和本地运行产物未进入待提交列表；已将 `data/debug_traces/` 加入 `.gitignore`。
- 完成 T050：记录最终验收状态。
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T037-T050 标记为 `[X]`。

## Feature 002 目标

本 Feature 为 CO2RR Literature RAG Agent V3 增加检索调试 Debug Trace 能力，让每次 RAG 查询的检索链路可观察、可调试、可展示。

核心目标：

- 用户可以看到一次查询中系统检索到了哪些文献片段；
- 开发者可以看到关键词检索、向量检索、融合排序、重排序和 final context 的中间结果；
- 用户可以判断最终回答是否基于真实检索上下文；
- RAG 出错时，可以定位失败发生在哪个阶段；
- Debug Trace 失败不影响正常 RAG 查询；
- 不重写现有 RAG 主流程，只做旁路记录和 UI 展示。

## 修改文件

- `.gitignore`
- `README.md`
- `app/debug_trace.py`
- `app/pipeline_v2.py`
- `app/retriever.py`
- `docs/retrieval_debug.md`
- `tests/test_debug_trace.py`
- `ui/streamlit_app.py`
- `specs/002-retrieval-debug-trace/tasks.md`
- `CURRENT_TASK.md`
- `specs/002-retrieval-debug-trace/PROGRESS.md`

## 测试记录

| 日期 | 分支 | 命令 | 结果 | 说明 |
| --- | --- | --- | --- | --- |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` | 通过 | `tasks.md` 被 SpecKit 识别 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | checklist 统计 | 通过 | `requirements.md` 16/16 完成 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m py_compile app/debug_trace.py app/retriever.py app/pipeline_v2.py ui/streamlit_app.py` | 通过 | 语法检查通过 |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest tests/test_debug_trace.py -q` | 通过 | 20 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `.venv/bin/python -m pytest` | 通过 | 172 passed |
| 2026-06-05 | `feature/002-retrieval-debug-trace` | `timeout 20 .venv/bin/python -m streamlit run ui/streamlit_app.py` | 通过启动，超时停止 | Streamlit 启动到 `http://localhost:8501`，未做浏览器点击验证 |

## Streamlit Smoke Test

- 自动 smoke test：通过，服务成功启动。
- 浏览器内点击验证：未自动完成，需要用户手动验证。
- 手动验证项：
  - 文献查询入口正常；
  - 提问后能看到回答；
  - 回答下方有 Debug Trace 面板；
  - 面板默认折叠；
  - 展开能看到 query 信息；
  - 能看到 BM25 / vector / final context；
  - 缺失阶段显示 `not_available`；
  - 结构化抽取入口不被破坏；
  - 文献综合入口不被破坏；
  - Feature 001 文献库管理页面正常；
  - 没有红色 traceback。

## 风险与注意事项

- Debug Trace 是检索链路可观察能力，不是 citation verification，也不做 claim-level verification 或自动判断回答真假。
- 结构化抽取路径为了保持旧 `hybrid_retrieve()` 签名兼容，仅在 UI 侧记录当前 trace 和 final context；BM25/vector 细节仍主要由 V2 candidate 路径记录。
- Streamlit 浏览器内点击验证未自动完成。
- `git pull` 在开发前尝试同步 `V3-DEV` 时 60 秒超时，无输出；本轮基于本地 `V3-DEV` 继续完成。

## Git 操作状态

- 开发前 git status 是否干净：是。
- 是否从正确基线分支创建/进入功能分支：是，当前使用 `feature/002-retrieval-debug-trace`，基线为 `V3-DEV`。
- 功能分支测试是否通过：是。
- 是否建议提交功能分支：是。
- 是否建议合并回开发基线分支：是。
- 是否已 push：否，本轮按用户要求不执行 push。
- 不应提交文件检查：通过，`.env`、`data/`、`.venv/`、缓存和本地索引产物未进入待提交列表。

## 下一步建议

1. Codex 在功能分支提交本轮改动。
2. Codex 合并 `feature/002-retrieval-debug-trace` 到 `V3-DEV`。
3. Codex 在 `V3-DEV` 合并后重新运行测试。
4. 用户手动执行 `git push origin V3-DEV`。
