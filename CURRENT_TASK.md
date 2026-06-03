# CURRENT_TASK.md

## 当前 Feature：001-library-index-transparency

- Feature 名称：文献库管理与索引透明化
- Feature 目录：`specs/001-library-index-transparency/`
- 当前分支：`v2-dev`
- 当前状态：正在将 001-library-index-transparency / US3 改动合并到 `v2-dev`，本轮只处理 merge 冲突、测试和进度文档同步
- 当前完成范围：Phase 1 至 Phase 5 / US3，T001-T049
- 剩余任务：
  - US4：T050-T060
  - Polish：T061-T068
- 本轮临时限制：不执行 git commit，不执行 git push，最后由用户手动提交和 push

## 本次收尾目标

解决当前 merge 冲突，保留 `v2-dev` 已有 US1/US2 能力，并合入 US3「重新解析与重建索引」能力：

- 文献库列表、单篇详情、chunk preview、index_status 展示继续保留；
- 单篇重新解析、单篇重建索引、全量重建索引入口继续保留；
- operation summary、failure_stage、failure_reason 继续记录和展示；
- 不删除原始 PDF；
- 不修改 `.env`；
- 不修改 `data/`；
- 不引入数据库、FastAPI、Docker、Debug Trace 或 citation verification。

## 已完成任务

- Phase 1：Setup，T001-T004
- Phase 2：Foundational，T005-T015
- Phase 3：US1 文献库列表 MVP，T016-T027
- Phase 4：US2 单篇文献详情页，T028-T036
- Phase 5：US3 重新解析与重建索引，T037-T049

## 本轮冲突处理记录

- 冲突文件：
  - `CURRENT_TASK.md`
  - `app/document_library.py`
  - `app/index_status.py`
  - `app/indexer.py`
  - `specs/001-library-index-transparency/PROGRESS.md`
  - `tests/test_index_status.py`
  - `tests/test_parse_report.py`
  - `ui/streamlit_app.py`
- 已暂存但仍需纳入最终 merge resolution：
  - `app/ingest.py`
- 处理原则：
  - 代码文件按函数职责合并，不简单选择 current 或 incoming；
  - 测试文件保留旧测试并合入 US3 新测试；
  - UI 保留文献查询入口、文献库管理、单篇详情和 US3 操作入口；
  - 文档整理为 T001-T049 已完成，US4/Polish 未完成。

## 测试记录

```bash
.venv/bin/python -m py_compile app/ingest.py app/indexer.py app/document_library.py app/index_status.py ui/streamlit_app.py
```

结果：通过，无输出

```bash
.venv/bin/python -m pytest tests/test_parse_report.py tests/test_document_library.py tests/test_index_status.py -q
```

结果：30 passed in 0.81s

```bash
.venv/bin/python -m pytest
```

结果：147 passed in 1.06s

## 手动 Smoke Test

- Streamlit 浏览器内手动点击验证：未完成。本轮未启动浏览器进行人工点击，不会声称 UI 已手动验证。
- 建议检查：
  - 文献查询入口仍可访问；
  - 文献库管理页面能打开；
  - 单篇详情、chunk preview、failure_stage / failure_reason 可见；
  - 单篇重新解析、单篇重建索引、全量重建索引按钮存在且操作摘要可见。

## Git 状态

- 是否执行 git commit：否，本轮按用户要求不执行
- 是否执行 git push：否，本轮按用户要求不执行
- 是否合并完成：冲突已解决且测试通过；待 `git add` 后由用户手动完成 merge commit

## 已知风险

- UI 操作涉及真实 PDF、embedding 配置和 ChromaDB，本轮自动测试不能替代浏览器内真实点击验证；
- 单篇重建索引会重新读取目标 PDF 以生成 chunk，但不会触发全库重建；
- 全量重建只有用户明确点击“全量重建索引”才会触发；
- 后续 US4 删除关联记录仍需继续遵守“不删除原始 PDF”默认行为。

## 下一步建议

1. 完成本轮测试并确认 `git status` 只剩待提交的 merge resolution。
2. 用户手动执行 merge commit。
3. 用户手动 push `v2-dev`。
4. 后续继续 US4 T050-T060，再做 Polish T061-T068。

## 强制更新规则

每次完成一个需求、阶段、User Story 或 task 后，必须同步更新 `CURRENT_TASK.md` 和 `specs/001-library-index-transparency/PROGRESS.md`，记录完成 task、测试命令、测试结果、风险、下一步建议以及提交/合并/push 状态。
