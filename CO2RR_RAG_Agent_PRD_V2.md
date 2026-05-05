# CO2RR-LocalScholar V2：面向本地 CO2RR 文献的可验证 RAG 综合研究助手

## 1. 项目名称

**CO2RR-LocalScholar V2：面向本地 CO2RR 文献的可验证 RAG 综合研究助手**

本项目是在现有 V1 版 CO2RR 文献 RAG Agent 基础上的增量升级。V2 不替代 V1，而是在 V1 已有的本地文献解析、结构化抽取和证据校验能力之上，增加 OpenScholar-lite 风格的文献综合、引用感知生成、自我反馈修订和结论级引用校验能力。

---

## 2. V2 版本定位

V1 的核心定位是：**结构化实验信息抽取工具**。

V1 重点解决的问题是：从本地 CO2RR 文献 PDF 和 Supporting Information 中，抽取合成方法、测试条件、性能数据、机理解释等结构化信息，并为每条关键信息提供 `evidence_sentence`、文献名、页码或章节位置，防止无证据输出。

V2 的核心定位是：**可验证的本地 CO2RR 文献综合研究助手**。

V2 不是推翻 V1，而是在 V1 基础上增强以下能力：

- 从“检索相关片段并抽取表格”升级为“围绕研究问题综合多篇文献”；
- 从“每条抽取记录验证 evidence_sentence 是否来自原文”升级为“每个关键结论都做 claim-level citation verification”；
- 从“单轮生成”升级为“初稿生成、自我反馈、必要时二次检索、修订答案”；
- 从“实验信息表格输出”升级为“综合回答、关键结论、证据支持状态、结构化表格、文献对比和不确定项并存的 Markdown V2 报告”。

V2 继承 V1 的 PDF 解析、OCR 降级、SI 识别、父子 chunk、混合检索、结构化抽取、证据校验、Markdown 输出和 Streamlit UI。V2 新增 OpenScholar-lite 风格的文献综合能力，使系统能够从本地 CO2RR 文献库中生成可追溯、可校验、可复查的中文综合回答。

---

## 3. V1 已有能力复用

V2 必须复用并保持 V1 的基线能力，不得破坏 V1 原有工作流。

V1 保留能力包括：

- 本地 PDF 解析；
- OCR 降级；
- Supporting Information 识别；
- DOI / 标题 / 文献名提取；
- 父子 chunk 切分；
- ChromaDB 向量索引；
- BM25 关键词检索；
- BM25 + 向量检索 + RRF 融合；
- 结构化信息抽取；
- Pydantic schema 校验；
- `evidence_sentence` 原文回查；
- Markdown 表格输出；
- Streamlit UI；
- 查询结果自动保存。

V2 应将这些能力作为基础设施复用，而不是重新实现一套独立系统。

---

## 4. V2 新增核心需求

### FR-V2-01：Cross-encoder Reranker 精排

V2 需要在 V1 的 BM25 + 向量检索 + RRF 融合召回之后，新增 cross-encoder reranker 精排阶段。

需求说明：

- 对 RRF 融合后的候选父 chunk 进行精排；
- 输入为 `query + candidate parent chunks`；
- 输出每个候选 chunk 的 `rerank_score`；
- 默认从 `candidate_top_k=80` 精排到 `final_top_n=10`；
- 每篇文献最多保留 `max_chunks_per_paper=3` 个 chunk；
- reranker 阶段应优先保留与用户问题直接相关、证据密度高、上下文完整的父 chunk；
- 目标是提高进入 LLM 上下文的证据质量，降低无关 chunk 对综合回答的干扰。

验收标准：

- 检索结果中应包含 `rerank_score`；
- 同一文献进入最终上下文的 chunk 数量不得超过配置上限；
- 在评测集上，V2 的 Evidence Hit Rate 应高于仅使用 RRF 的 V1 基线。

### FR-V2-02：Citation-aware Synthesis 文献综合回答模式

V2 需要新增“文献综合回答模式”，用于回答多篇文献综合类问题。

适用问题包括：

- 多篇 CO2RR 文献共同说明了什么；
- 不同文献实验路线有什么差异；
- 添加剂机理解释是否一致；
- 不同测试条件对性能结果有什么影响；
- 当前文献证据对实验设计有什么启发。

输出要求：

- 使用中文生成综合回答；
- 输出关键结论 claims；
- 每个关键结论后必须带引用编号；
- 输出每个 claim 对应的 evidence；
- 输出不确定项；
- 明确区分“文献明确说明”和“Agent 分析”。

验收标准：

- 主回答中的关键事实必须有引用；
- 引用必须能够追溯到本地文献 chunk；
- 无引用的事实性 claim 不得进入主回答。

### FR-V2-03：Self-feedback 自我反馈修订

V2 需要新增 self-feedback 机制。

基本流程：

1. 先基于 rerank 后的上下文生成初稿；
2. 再让模型检查初稿；
3. 根据反馈修订答案；
4. 默认最多执行 1 轮 self-feedback。

检查内容包括：

- `unsupported_claims`：没有证据支持的结论；
- `missing_aspects`：问题中需要覆盖但初稿遗漏的方面；
- `citation_mismatch`：引用与结论不匹配；
- 是否混合不同文献实验条件；
- 是否需要补充检索。

验收标准：

- self-feedback 输出应记录在内部过程或调试信息中；
- 修订后的答案应减少 unsupported claims；
- 如果模型判断证据不足，应触发或建议 follow-up retrieval。

### FR-V2-04：Follow-up Retrieval 二次检索

V2 需要在 self-feedback 判断证据不足或覆盖不完整时，自动生成 follow-up queries。

需求说明：

- follow-up queries 只能在本地文献库中二次检索；
- 不默认联网查新文献；
- 二次检索结果需要再次经过 reranker；
- 新证据合并进上下文后，再修订答案；
- 默认最多生成 `max_followup_queries=3` 条二次检索 query。

验收标准：

- 当初稿存在明确证据缺口时，系统能够生成针对性的 follow-up queries；
- 二次检索不得绕过本地文献库边界；
- 二次检索加入的新证据必须参与 citation verification。

### FR-V2-05：Claim-level Citation Verification 结论级引用校验

V1 校验的是 `evidence_sentence` 是否来自原文。V2 需要进一步校验 claim 是否真的被 evidence 支持。

支持状态包括：

- `supported`：证据直接支持该结论；
- `partially_supported`：证据部分支持，但结论需要弱化或限定；
- `unsupported`：证据不支持该结论。

处理规则：

- `supported` claim 可以作为文献明确结论进入主回答；
- `partially_supported` claim 必须降低语气，或放入“不确定项”；
- `unsupported` claim 不得进入主回答，只能删除或放入“不确定项”；
- evidence 出现在原文中，不代表 claim 一定成立，必须进行 claim-level verification。

验收标准：

- V2 输出中每个关键结论必须有支持状态；
- unsupported claim 不得出现在“综合回答”的文献明确结论中；
- partially_supported claim 必须有说明。

### FR-V2-06：V1 / V2 双模式兼容

系统至少支持三种模式：

1. **结构化抽取模式**：沿用 V1，用于提取合成方法、测试条件、性能数据、机理解释等表格信息；
2. **文献综合模式**：V2 新增，用于回答多篇文献综合类问题；
3. **精读解释模式**：面向小白用户解释单篇英文文献，帮助理解背景、方法、结果、图表和实验含义。

要求：

- V2 不破坏 V1 原有结构化抽取能力；
- 用户可以明确选择模式；
- 若用户未选择模式，系统可根据问题类型自动建议模式；
- V1 输出格式和保存路径应继续可用。

### FR-V2-07：Markdown V2 输出结构

V2 文献综合模式推荐输出结构：

```md
# 查询结果：{query}

## 一、综合回答

## 二、关键结论与证据支持状态

| 编号 | 关键结论 | 引用 | 支持状态 | 说明 |
|---|---|---|---|---|

## 三、结构化信息表

## 四、文献对比与分析

## 五、Agent 分析

## 六、不确定项

## 七、原文证据摘录
```

验收标准：

- 输出必须是 Markdown；
- 关键结论表必须包含支持状态；
- 原文证据摘录必须包含可回查的来源信息；
- Agent 分析不得与文献明确结论混在一起。

### FR-V2-08：上下文预算与单篇文献片段限制

V2 需要新增上下文预算控制，避免少数文献占据全部上下文。

新增配置建议：

```yaml
retrieval:
  bm25_top_k: 50
  vector_top_k: 50
  rrf_k: 60
  candidate_top_k: 80
  final_top_n: 10
  max_chunks_per_paper: 3
  max_context_tokens: 12000
```

验收标准：

- 最终进入 LLM 的 chunk 数量不得超过 `final_top_n`；
- 单篇文献 chunk 数不得超过 `max_chunks_per_paper`；
- 上下文长度不得超过 `max_context_tokens`；
- 当上下文超限时，应优先保留 rerank 分数高、证据密度高的 chunk。

### FR-V2-09：Metadata-aware Retrieval 元数据增强检索

V2 需要在检索和 rerank 阶段利用 metadata。

可用 metadata 包括：

- 标题；
- DOI；
- 文献名；
- 年份；
- 章节；
- 页码；
- 是否 Supporting Information；
- chunk 类型；
- 父子 chunk 关系。

构造 `retrieval_text` 的推荐格式：

```text
Title: {paper_title}
DOI: {doi}
Section: {section}
Page: {page}
Supporting Information: {is_si}
Text: {chunk_text}
```

验收标准：

- reranker 输入不应只有正文片段，还应包含必要 metadata；
- 当问题涉及 Experimental、SI、测试条件、机理等定位词时，metadata 应参与排序。

### FR-V2-10：可选外部元数据增强

V2 可选支持外部元数据增强，但默认关闭。

需求说明：

- 可根据 DOI 或标题查询 Crossref / Semantic Scholar；
- 只补充标题、年份、作者、摘要、引用数等 metadata；
- 不自动下载外部全文；
- 不改变“本地文献库优先”的边界；
- 不将用户本地 PDF 全文上传到外部服务。

验收标准：

- `external_metadata.enabled=false` 时不得发起外部元数据请求；
- 外部元数据只能作为检索增强和展示辅助，不得替代本地原文证据；
- 最终回答的 evidence 必须来自本地文献库。

### FR-V2-11：OpenScholar 风格配置开关

V2 需要通过配置文件控制 OpenScholar-lite 风格能力。

推荐配置：

```yaml
v2:
  mode_enabled: true

reranker:
  enabled: true
  model: BAAI/bge-reranker-large
  candidate_top_k: 80
  final_top_n: 10

self_feedback:
  enabled: true
  max_iterations: 1
  allow_followup_retrieval: true
  max_followup_queries: 3

citation_verification:
  enabled: true
  mode: claim_evidence
  allow_partially_supported: true

external_metadata:
  enabled: false

context_budget:
  max_chunks_per_paper: 3
  max_context_tokens: 12000
```

验收标准：

- 每个 V2 增强能力都应可通过配置开启或关闭；
- 关闭 V2 后，系统应回到 V1 行为；
- 关闭 reranker 时，系统应使用 RRF 结果直接进入后续流程；
- 关闭 self-feedback 时，系统应单轮生成答案；
- 关闭 citation verification 时，应明确提示用户结论级引用校验未启用。

### FR-V2-12：CO2RR-RAG-Bench 小型评测集

V2 需要建立一个小型评测集，用于比较 V1 与 V2 的实际效果。

评测集要求：

- 20-50 篇 CO2RR PDF；
- 50-100 个测试问题；
- 每个问题标注 gold evidence；
- 每个问题标注 expected answer points；
- 覆盖合成方法、测试条件、性能数据、添加剂机理、文献对比和实验启发类问题。

评估指标包括：

- Retrieval Recall@K；
- MRR / nDCG；
- Evidence Hit Rate；
- Citation Support Accuracy；
- Answer Correctness；
- Coverage；
- Unsupported Claim Rate。

验收标准：

- 至少形成一版可复现的评测清单；
- V2 应能输出与 V1 的对比结果；
- 评测结果应能定位问题是出在检索、rerank、生成还是 citation verification。

---

## 5. V2 用户场景

### 5.1 多篇文献综合总结

用户问题示例：

> 这些 CO2RR 文献对 Ag 基催化剂提高 CO 选择性有什么共同结论？

系统应输出多篇文献的共同发现、分歧点、关键证据、支持状态和不确定项。

### 5.2 CO2RR 催化剂合成路线对比

用户问题示例：

> 对比这些文献中 AgNPs 的合成路线，哪些使用 NaBH4 还原法，哪些使用其他路线？

系统应输出结构化表格，区分不同文献的前驱体、还原剂、温度、时间、后处理和原文证据。

### 5.3 添加剂作用机理综合

用户问题示例：

> 咪唑类添加剂在 CO2RR 中的作用机理是否一致？

系统应综合不同文献中关于 CO2 富集、HER 抑制、中间体稳定、电双层调控等机理解释，并标注每个结论的支持状态。

### 5.4 实验条件差异对比

用户问题示例：

> 不同文献中 Ag 基催化剂的测试条件有什么差异？

系统应比较电解池类型、电解液、CO2 流速、电位、电流密度、产物分布和 FE，并避免把不同文献条件合并成一条虚构条件。

### 5.5 基于文献证据给出实验设计启发

用户问题示例：

> 基于这些文献，如果我要优化 AgNPs 的 CO2RR 测试条件，有哪些可借鉴的实验设计启发？

系统应只基于已有文献证据提出启发，不能编造新实验结果。建议必须明确来自哪些文献，并区分“文献明确说明”和“Agent 分析”。

### 5.6 小白精读单篇英文文献

用户问题示例：

> 帮我用中文精读这篇英文文献，解释它的研究背景、实验方法、关键结果和对我课题的启发。

系统应面向初学者解释单篇文献，保留关键英文术语，给出原文证据，并说明哪些内容是文献事实、哪些是辅助理解。

---

## 6. V2 输出要求

V2 默认输出 Markdown。

通用要求：

- 所有关键结论都必须带引用；
- 输出 claim 支持状态；
- 明确区分“文献明确说明”和“Agent 分析”；
- 不确定内容必须进入“不确定项”；
- 原文证据必须包含文献名、文件名、页码、章节、是否 SI、原文片段；
- 结构化表格应保留 V1 的字段严谨性；
- 原文未明确说明的字段填 `null` 或“未明确说明”；
- 不得把 Agent 推测写成文献结论。

V2 推荐输出结构见 FR-V2-07。

---

## 7. V2 防幻觉规则

V2 必须继承 V1 的防幻觉规则，并增加结论级校验约束。

规则如下：

- 没有 evidence 的 claim 不得进入主回答；
- evidence 出现在原文中，不代表 claim 一定成立，必须做 claim-level verification；
- 不允许把不同文献的实验条件合并成一个结论；
- 不允许根据常识补全实验条件；
- 不允许把 SI 中的信息伪装成正文信息；
- 不允许把单篇文献结论扩大成多篇文献共识；
- `partially_supported` 的结论必须弱化表达；
- `unsupported` 的结论必须删除或放入“不确定项”；
- Agent 分析必须单独标注，不能作为文献明确结论；
- 当本地文献库中没有足够证据时，应明确回答证据不足，而不是生成看似完整的答案。

---

## 8. V2 暂不纳入范围

V2 暂不做以下内容：

- 不构建 4500 万论文级别的超大数据库；
- 不训练 OpenScholar-8B；
- 不训练专属 retriever；
- 不训练专属 reranker；
- 不默认联网下载新文献；
- 不公开用户文献和 query；
- 不做复杂多 Agent 协作；
- 不做大规模专家评测；
- 不自动写论文；
- 不自动生成实验数据；
- 不自动分析图像曲线数据；
- 不将本地 PDF 全文上传到外部元数据服务。

这些边界用于保证 V2 仍然是一个轻量、可本地部署、以用户已有文献库为中心的 OpenScholar-lite 系统。

---

## 9. V2 优先级

### P0

- Reranker；
- 文献综合回答；
- Claim-level citation verification。

### P1

- Self-feedback；
- Follow-up retrieval；
- Markdown V2；
- V1 / V2 双模式兼容。

### P2

- Metadata-aware retrieval；
- 上下文预算控制；
- CO2RR-RAG-Bench。

### P3

- 外部元数据增强；
- 查询历史和多轮对话增强。

---

## 10. V1 到 V2 的差异表

| 能力 | V1 | V2 |
|---|---|---|
| 主要目标 | 结构化实验信息抽取 | 文献综合研究助手 |
| 检索 | BM25 + 向量 + RRF | 增加 reranker |
| 生成 | 表格抽取 | 综合回答 + claims |
| 校验 | evidence_sentence 原文回查 | claim-level citation verification |
| 推理 | 单轮 | self-feedback + follow-up retrieval |
| 输出 | Markdown 表格 | Markdown V2 综合报告 |
| 评估 | 基础验收 | CO2RR-RAG-Bench |
| 适用问题 | 合成方法、测试条件、性能数据抽取 | 多文献综合、机理对比、实验启发、精读解释 |
| 证据粒度 | 抽取记录级 evidence | claim 级 citation 与支持状态 |
| 系统边界 | 本地文献库优先 | 继续本地文献库优先，可选外部 metadata |

---

## 11. 验收标准汇总

V2 版本完成时，应满足以下验收标准：

1. V1 结构化抽取模式仍可正常运行；
2. 文献综合模式可以基于本地 CO2RR 文献生成中文综合回答；
3. RRF 后候选 chunk 能经过 reranker 精排；
4. 最终上下文 obey `final_top_n`、`max_chunks_per_paper` 和 `max_context_tokens`；
5. 主回答中的关键结论都带引用；
6. 每个关键结论都有 `supported`、`partially_supported` 或 `unsupported` 状态；
7. unsupported claim 不进入主回答；
8. partially_supported claim 被弱化表达或放入不确定项；
9. self-feedback 至少支持 1 轮初稿检查与修订；
10. 当证据不足时，系统可以生成 follow-up queries 并只在本地文献库中二次检索；
11. Markdown V2 报告包含综合回答、关键结论与证据支持状态、结构化信息表、文献对比、Agent 分析、不确定项和原文证据摘录；
12. CO2RR-RAG-Bench 至少形成初版评测方案，用于比较 V1 与 V2。

---

## 12. 一句话总结

**V1 让系统能够从本地 CO2RR 文献中可靠抽取实验信息；V2 在此基础上加入 OpenScholar-lite 风格的 rerank、citation-aware synthesis、self-feedback、follow-up retrieval 和 claim-level citation verification，使系统升级为可追溯、可校验、可复查的本地 CO2RR 文献综合研究助手。**
