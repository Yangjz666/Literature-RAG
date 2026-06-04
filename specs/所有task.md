# 所有 task：CO2RR 文献 RAG Agent 后续功能规划

本文档用于整理 CO2RR 文献 RAG Agent 在 Feature 001 之后的核心功能路线图。每个 Feature 都应单独创建功能分支，并按 Speckit / AGENTS.md 流程完成 specify、plan、tasks、implement、test、document sync 和交付记录。

## Feature 001：文献库管理与索引透明化

状态：已完成。

已完成内容：

- 文献库列表；
- 单篇文献详情；
- parse_report；
- index_status；
- chunk preview；
- 单篇重新解析；
- 单篇重建索引；
- 全量重建索引；
- 删除文献关联记录；
- 文档、测试、验收收尾。

当前状态说明：

- 已完成 T001-T068；
- 已合并到 `v2-dev`；
- 已 push 到 `origin/v2-dev`；
- 后续只做维护和 bug 修复。

维护注意事项：

- 删除文献关联记录默认不删除原始 PDF；
- 文献库管理仍使用本地 JSON/manifest、ChromaDB、BM25 和 parent store；
- 不引入数据库；
- 不重写 V1 / V2 主流程。

## Feature 002：检索调试 Debug Trace

状态：待开发，下一步优先做。

目标：

- 检索可调试；
- 用户能看到系统到底检索到了哪些内容；
- 开发者能定位问题发生在检索链路哪一步。

需要包含：

- original query；
- rewritten query；
- BM25 检索结果；
- vector 检索结果；
- RRF 融合结果；
- reranker 排序结果；
- final context chunks；
- 每个 chunk 的 filename、page、section、chunk_id、score、text preview；
- 查询失败时记录失败阶段和错误原因。

建议实现边界：

- 优先复用现有 retriever、reranker、context builder 和 V2 pipeline；
- Debug Trace 应作为查询过程的可观察输出，不替代回答生成逻辑；
- trace 数据应能在 Streamlit 中展示，也应便于测试断言；
- 失败 trace 不应暴露 API Key、.env 内容或本地隐私路径。

不做范围：

- 不做完整 citation verification；
- 不做 FastAPI；
- 不做 Docker；
- 不引入数据库；
- 不重写现有 RAG 主流程。

## Feature 003：结果追溯与 Citation Evidence

状态：待开发。

目标：

- 结果可追溯；
- 回答中的引用能对应到具体文献 chunk；
- 用户能判断回答是否真的有证据支持。

需要包含：

- citation_id；
- filename；
- page；
- section；
- chunk_id；
- evidence_text；
- 是否进入 final context；
- 是否被最终回答引用；
- 回答区域展示 citation evidence。

建议实现边界：

- 优先在现有回答输出和 context chunk metadata 上增加可追溯引用结构；
- citation evidence 必须能回到本地 chunk 和文献元数据；
- 没有证据时继续遵守 evidence-first 行为，不把推测伪装为文献事实。

不做范围：

- 暂不做 claim-level citation verification；
- 暂不做自动真假判定；
- 暂不做复杂证据评分。

## Feature 004：评测、日志、Token、耗时和成本统计

状态：待开发。

目标：

- 效果可评估；
- 运行可观察；
- 更像完整 AI 应用项目。

需要包含：

- 标准测试集；
- RAG 问答效果评估；
- 日志记录；
- Token 使用统计；
- LLM / Embedding 调用耗时统计；
- 成本估算；
- 查询历史或运行摘要；
- 测试结果记录。

建议实现边界：

- 优先使用轻量 JSON/Markdown/CSV 记录，避免引入复杂服务；
- 不记录 API Key、.env 内容、真实私有 PDF 路径或敏感原文全文；
- 评测样例应尽量轻量、可复现，并与真实私有文献库隔离。

不做范围：

- 不做复杂监控平台；
- 不引入重量级 observability 系统；
- 不做多用户权限系统。

## Feature 005：部署与项目展示闭环

状态：待开发，最后做。

目标：

- 系统可部署；
- 项目可展示；
- 方便写进简历和面试讲解。

需要包含：

- README 完整使用说明；
- `.env.example`；
- 安装说明；
- 启动命令；
- 测试命令；
- 常见问题；
- Docker 或部署说明；
- demo 使用流程；
- 项目截图或演示说明；
- 面试展示重点说明。

建议实现边界：

- 优先保证本地 WSL / Linux 环境可复现；
- 示例配置只能使用占位符，不得包含真实 API Key；
- demo 文档应突出 evidence-first、可追溯、可调试和可评测能力。

不做范围：

- 不做复杂云原生部署；
- 不做多用户生产系统；
- 不做商业化权限系统。

## 推荐开发顺序

1. Feature 001：文献库管理与索引透明化，已完成；
2. Feature 002：检索调试 Debug Trace，下一步；
3. Feature 003：结果追溯与 Citation Evidence；
4. Feature 004：评测、日志、Token、耗时和成本统计；
5. Feature 005：部署与项目展示闭环。

## 后续执行规则

- 每个 Feature 单独创建 `feature/xxx` 分支；
- 每个 Feature 单独维护 spec、plan、tasks、PROGRESS 和 CURRENT_TASK；
- 实现前必须确认开发基线、分支状态和 `git status`；
- 不提交 `.env`、API Key、`data/` 运行产物、本地 PDF、ChromaDB、BM25、parent store 或缓存；
- 任何涉及 RAG 输出的改动都必须保留 evidence-first 行为和可追溯 metadata。
