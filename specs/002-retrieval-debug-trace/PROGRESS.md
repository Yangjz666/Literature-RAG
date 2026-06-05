# Feature 002 开发进度：检索调试 Debug Trace

## Feature 基本信息

- Feature：`002-retrieval-debug-trace`
- 名称：检索调试 Debug Trace
- 开发基线分支：`V3-DEV`
- 当前分支：`feature/002-retrieval-debug-trace`
- 当前阶段：implement 收尾
- 当前完成到：T001-T050 已完成实现与测试
- Feature 状态：已完成，等待本轮提交并合并回 `V3-DEV`；本轮不执行 push

## 总体目标

本 Feature 为 CO2RR Literature RAG Agent V3 增加检索调试 Debug Trace 能力，让每次 RAG 查询的检索链路可观察、可调试、可展示。

目标包括：

- 用户能看到一次查询检索到了哪些文献片段；
- 开发者能看到关键词检索、向量检索、融合排序、重排序和 final context 的中间结果；
- 用户能判断最终回答是否基于真实检索上下文；
- 查询失败时能定位失败阶段；
- Debug Trace 记录失败不影响正常查询；
- 只做旁路记录和展示，不重写现有 RAG 主流程。

## 阶段进度

| Phase | 内容 | 状态 | 说明 |
| --- | --- | --- | --- |
| specify | 需求规格 | 已完成 | 已生成 `spec.md` 和 `checklists/requirements.md` |
| clarify | 需求澄清 | 已完成/无需新增问题 | 当前未发现阻塞 plan 的需求冲突 |
| plan | 技术方案 | 已完成 | 已生成并审核修订 `plan.md` |
| tasks | 任务拆解 | 已完成 | 已生成标准 `tasks.md` |
| analyze | 一致性分析 | 已完成 | 前置检查通过，未发现阻塞实现的问题 |
| implement Phase 1 | 准备与文档同步 | 已完成 | T001-T003 |
| implement Phase 2 | 测试骨架与 Debug Trace 数据结构 | 已完成 | T004-T015 |
| implement Phase 3 | Citation / Evidence 基础映射 | 已完成 | T016-T018 |
| implement Phase 4 | 接入现有 RAG 查询流程 | 已完成 | T019-T028 |
| implement Phase 5 | Streamlit Debug Trace 面板 | 已完成 | T029-T036 |
| implement Phase 6 | 错误处理与降级 | 已完成 | T037-T040 |
| implement Phase 7 | 文档与进度同步 | 已完成 | T041-T044 |
| implement Phase 8 | 最终测试与验收 | 已完成 | T045-T050 |

## 本轮完成内容

- T037：补充 Debug Trace 失败不影响主回答的测试。
- T038：新增 `safe_trace_call()` 和 `record_warning()`，trace 记录异常只进入 warning，不中断主流程。
- T039：补充连续两次查询 trace 不混淆测试。
- T040：Streamlit 使用 `st.session_state["current_debug_trace"]` 管理当前 trace，每次新查询覆盖，不默认落盘。
- T041：新增 `docs/retrieval_debug.md`，说明面板入口、阶段含义、`not_available`、`matched` / `unmatched`、非 citation verification 和后续升级方向。
- T042：更新 `README.md`，简要说明 Debug Trace 面板、使用入口和注意事项。
- T043：更新 `CURRENT_TASK.md`。
- T044：更新本 `PROGRESS.md`。
- T045：运行语法检查。
- T046：运行 Debug Trace 相关测试。
- T047：运行完整 pytest。
- T048：运行 Streamlit smoke test。
- T049：完成 Git 安全检查，并将 `data/debug_traces/` 加入 `.gitignore`。
- T050：记录最终验收状态。
- 已将 `specs/002-retrieval-debug-trace/tasks.md` 中 T037-T050 标记为 `[X]`。

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

## Streamlit 手动验证

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

- Debug Trace 只做检索链路可观察和 citation/evidence 基础映射，不做 claim-level verification、自动真假判断或完整 citation verification。
- 结构化抽取路径为了保持旧 `hybrid_retrieve()` 签名兼容，仅在 UI 侧记录当前 trace 和 final context；BM25/vector 细节仍主要由 V2 candidate 路径记录。
- Streamlit 浏览器内点击验证未自动完成。
- 开发前尝试 `timeout 60 git pull` 同步 `V3-DEV` 时超时，无输出；本轮基于本地 `V3-DEV` 继续完成。

## Git 安全检查

- `.env`：ignored，未进入待提交列表。
- `data/`：ignored，未进入待提交列表。
- `.venv/`：ignored，未进入待提交列表。
- `__pycache__/` / `.pytest_cache/`：ignored，未进入待提交列表。
- 本地 ChromaDB、BM25、parent store、PDF 文献库：未进入待提交列表。
- `data/debug_traces/`：已加入 `.gitignore`。

## Git 状态

- 开发前 git status 是否干净：是。
- 是否从正确基线分支创建/进入功能分支：是。
- 功能分支测试是否通过：是。
- 是否建议提交功能分支：是。
- 是否建议合并回 `V3-DEV`：是。
- 是否执行 push：否，本轮按用户要求不执行 push。

## 下一步计划

1. 在 `feature/002-retrieval-debug-trace` 提交本轮改动，建议提交信息：`feat: finalize retrieval debug trace workflow`。
2. 合并 `feature/002-retrieval-debug-trace` 到 `V3-DEV`。
3. 合并后在 `V3-DEV` 重新运行语法检查、Debug Trace 单测、完整 pytest 和 Streamlit smoke test。
4. 用户手动执行 `git push origin V3-DEV`。
