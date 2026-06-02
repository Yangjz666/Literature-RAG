# CURRENT_TASK.md

## 1. 当前任务

生成或更新项目上下文说明文件，让新的 GPT / Codex / Claude 能快速理解 CO2RR Literature RAG Agent 当前状态。

本次任务只允许新增或更新：

- `PROJECT_CONTEXT.md`
- `CURRENT_TASK.md`

本次任务不修改业务代码。

## 2. 当前审计结论

项目不是纯需求阶段，也不是完整 V3 成品阶段。更准确的判断是：

- **V1 基础 RAG + 结构化抽取闭环已经实现。**
- **V2 文献综合 pipeline 已部分实现并接入 UI，但部分能力默认关闭或保守降级。**
- **V3 主要是 PRD 中的工程化规划，尚未完整实现。**

## 3. 已经实现

- PDF / SI 解析、OCR 降级、DOI 提取、去重。
- 父子 chunk 切分。
- ChromaDB 向量索引、BM25 索引、parent chunk store。
- 增量索引 manifest。
- V1 混合检索：BM25 + vector + RRF。
- V1 三类结构化抽取：合成、测试条件、机理。
- Evidence sentence 原文回查。
- V1 Markdown 输出和保存。
- Streamlit UI 的索引与查询流程。
- V2 schema、候选召回、上下文构建、rerank 降级、citation-aware synthesis、claim verifier、feedback、follow-up retrieval、Markdown V2、pipeline、query router、eval bench、metadata enricher。
- UI 中已接入查询模式选择，文献综合模式会调用 `run_synthesis_pipeline()`。

## 4. 部分完成

- V2 文献综合：代码路径存在，但未在当前环境完成真实端到端验证。
- Reranker：默认关闭；启用需要额外依赖 `sentence-transformers` 和模型下载。
- Self-feedback：默认关闭，目前主要记录反馈和 follow-up 意图。
- Follow-up retrieval：默认关闭，且还不是完整“二次检索后重新修订答案”的成熟闭环。
- Claim-level verification：规则保守，但还不是强语义校验。
- 精读解释模式：已有路由和 UI 入口，但功能未完整实现。

## 5. 需求中有但尚未完整实现

- V3 文献库管理页。
- 检索 Debug Trace 面板。
- 查询历史页。
- Token、耗时、成本统计。
- 一键评测数据集和报告。
- 完整部署说明。
- 主项目 `README.md`。
- `.env.example`。
- Docker / compose 部署文件。
- 完整 self-feedback 修订闭环。
- 默认可运行的 cross-encoder reranker 环境。

## 6. 当前待确认事项

- 当前是否在 `main` 分支；constitution 要求功能开发应在任务分支上进行。
- 本机 `.env` 是否配置完整的 LLM 和 Embedding 通道。
- 当前 `data/chroma_db`、`data/index_manifest.json`、BM25 和 parent store 是否存在且与配置一致。
- 真实文献库下 V1 / V2 查询是否端到端成功。
- `.agents/skills/rag-project-context/` 是未跟踪目录，应确认是否需要加入版本控制或保持本地私有。

## 7. 本次验证状态

已尝试运行测试：

```bash
pytest -q
python -m pytest -q
python3 -m pytest -q
```

结果：

- `pytest` 命令不存在。
- `python` 命令不存在。
- `python3` 存在，但未安装 pytest：`No module named pytest`。

因此，本次未完成自动化测试验证。当前文档状态判断来自代码和文档静态审计。

## 8. 下一步最适合开发的小功能

最适合的下一个小功能是：**补齐项目启动与配置文档：新增根目录 `README.md` 和 `.env.example`，并记录 V1 / V2 的最小可运行流程。**

理由：

- 当前代码已经有不少 V1/V2 能力，但根目录没有 README，新开发者不知道如何配置 LLM、Embedding、索引路径和启动 UI。
- 这个任务不碰核心业务逻辑，风险低。
- 可以同步 constitution 的文档同步要求。
- 完成后再做端到端验证、Debug Trace 面板或 V2 修订闭环会更稳。

建议验收标准：

- `README.md` 包含项目简介、技术栈、环境变量、安装、启动、索引、查询、V1/V2 模式说明、常见错误。
- `.env.example` 不含真实密钥，只列出必需变量。
- 文档明确说明 `EMBEDDING_API_KEY` / `EMBEDDING_BASE_URL` 与 LLM API 是两套配置。
- 在安装 pytest 后运行 `python3 -m pytest -q` 并记录结果。

## 9. 后续开发优先级建议

1. 文档与配置补齐：`README.md`、`.env.example`、测试运行说明。
2. 测试环境修复：安装依赖并跑通 `python3 -m pytest -q`。
3. V2 文献综合端到端冒烟测试：使用小型 PDF fixture 或本地样本文献验证索引、检索、生成、保存。
4. Debug Trace 最小面板：先展示 BM25 / vector / RRF / final chunks，而不是一次性做完整 V3 管理后台。
5. 完善 self-feedback 修订闭环：只有在 V2 端到端稳定后再做。

