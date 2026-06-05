# 检索调试 Debug Trace

Debug Trace 是每次 RAG 查询的检索链路记录，用于查看系统在回答前实际检索、融合、重排序和送入上下文的文献片段。它服务于可观察性和排错，不替代文献证据本身。

## 面板入口

在 Streamlit 的 `文献查询` 页面提交问题后，回答区域下方会出现默认折叠的「检索调试 Debug Trace」面板。展开后可以查看本轮查询的 trace 信息、各阶段结果、Citation / Evidence 基础映射和 Raw JSON。

当前 trace 默认只保存在 `st.session_state`，每次新查询会覆盖上一轮当前 trace，不默认落盘。

## 阶段含义

- Query 信息：本轮 `trace_id`、创建时间、原始问题、查询模式、耗时等。
- BM25 results：关键词检索命中的 chunk。
- Vector results：向量检索命中的 chunk。
- RRF results：BM25 与向量检索融合后的候选结果；如果当前路径不可用则显示 `not_available`。
- Reranker results：重排序后的候选结果；如果 reranker 未启用或当前路径不可用则显示 `not_available`。
- Final context chunks：最终送入回答生成流程的上下文片段。
- Citation / Evidence：最终回答或报告中 citation/evidence 与 final context chunk 的基础映射。
- Raw JSON：当前 trace 的 JSON-safe 调试数据，便于开发者定位问题。

## not_available

`not_available` 表示某个阶段在当前查询路径中没有启用、没有可安全获取的数据，或该阶段不属于当前模式。它不等同于查询失败。

例如：结构化抽取路径可能没有 reranker 输出；某些配置下没有 RRF 或 reranker 阶段；这些情况应显示 `not_available`，而不是伪造结果。

## matched / unmatched

Citation / Evidence 表格中的 `match_status` 只表示 citation/evidence 是否能根据 `chunk_id` 与本轮 final context chunk 做基础匹配：

- `matched`：citation/evidence 的 `chunk_id` 能在 final context chunks 中找到。
- `unmatched`：citation/evidence 没有匹配到本轮 final context chunk。
- `not_available`：缺少足够字段或当前路径没有可用 citation/evidence。

该状态不判断回答内容真假，不判断 claim 是否被充分支持，也不代表完整 citation verification。

## 不是 Citation Verification

本功能不做：

- claim-level verification；
- 自动判断回答真假；
- 证据充分性评分；
- 跨文献实验条件一致性验证；
- 文献事实自动裁决。

如果证据不足，回答流程仍应遵守 evidence-first 原则，明确标注不确定或拒绝无证据结论。

## 后续升级方向

后续可在独立 Feature 中逐步增强：

- 将 trace 与引用证据检查结合，形成更完整的 citation verification；
- 对 claim 做逐条证据覆盖检查；
- 增加可配置的 trace 落盘策略，但必须忽略 `data/debug_traces/`，不得提交本地 trace；
- 增加更细粒度的 query rewrite、reranker、follow-up retrieval 阶段展示；
- 增加评测集中的 trace 质量检查。
