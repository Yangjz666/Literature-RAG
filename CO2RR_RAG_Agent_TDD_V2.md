# CO2RR-LocalScholar V2 技术设计文档

## 1. 设计目标与边界

本技术文档对应 `CO2RR_RAG_Agent_PRD_V2.md`，用于指导 V2 的工程实现。

V2 的目标是在 V1 的本地 PDF 解析、父子 chunk、混合检索、结构化抽取、`evidence_sentence` 校验和 Markdown 输出基础上，实现一个面向本地 CO2RR 文献库的 OpenScholar-lite 技术路线。

OpenScholar 的公开实现提供了几个可参考的关键机制：

- 标准 RAG：将 top-N passages 输入生成模型，OpenScholar 多文献任务默认 `top_n=10`；
- Cross-encoder reranker：通过 `ranking_ce` 和 reranker 模型重排候选 passages；
- Self-feedback：生成后进行反馈检查和修订；
- Posthoc citation attribution：生成后做引用归因；
- `max_per_paper`：限制同一篇论文进入上下文的 passage 数量；
- Semantic Scholar / web API：用于外部检索增强。

V2 会参考这些机制，但做以下本地化修改：

- 不构建 OpenScholar 的 4500 万论文级别数据库；
- 不训练 OpenScholar-8B、专属 retriever 或专属 reranker；
- 不默认联网检索新文献；
- 继续以本地 PDF 文献库为唯一默认全文来源；
- 外部 API 只作为可选 metadata 增强，不作为默认证据来源；
- 输出语言面向中文 CO2RR 研究场景；
- 继续保留 V1 的结构化抽取模式。

---

## 2. V2 总体架构

### 2.1 分层架构

```text
用户问题
  |
  v
[query_router.py]
  |-- structured_extraction -> V1 extractor/verifier/generator
  |-- synthesis            -> V2 synthesis pipeline
  |-- deep_reading         -> V2 single-paper explanation pipeline

V2 synthesis pipeline:

[retriever.py]
  BM25 + vector search + RRF
  |
  v
[reranker.py]
  cross-encoder rerank + max_per_paper
  |
  v
[context_builder.py]
  metadata-aware context + token budget control
  |
  v
[synthesizer.py]
  citation-aware draft generation
  |
  v
[feedback.py]
  self-feedback + follow-up query decision
  |
  v
[followup_retriever.py]
  local-only second retrieval
  |
  v
[claim_verifier.py]
  claim-level citation verification
  |
  v
[report_v2.py]
  Markdown V2 output + auto save
```

### 2.2 与 V1 的关系

V2 不重写 V1，而是在 V1 模块旁边增加增量模块。

V1 继续保留：

- `app/ingest.py`
- `app/chunker.py`
- `app/indexer.py`
- `app/retriever.py`
- `app/extractor.py`
- `app/verifier.py`
- `app/generator.py`
- `app/llm_client.py`
- `ui/streamlit_app.py`

V2 建议新增：

- `app/query_router.py`
- `app/reranker.py`
- `app/context_builder.py`
- `app/synthesizer.py`
- `app/feedback.py`
- `app/followup_retriever.py`
- `app/claim_verifier.py`
- `app/report_v2.py`
- `app/metadata_enricher.py`
- `app/eval_bench.py`

V2 修改现有模块时应保持兼容：

- `retriever.py`：扩展为可返回 candidate parent chunks，而不是改变 V1 默认行为；
- `generator.py`：保留 V1 Markdown 表格输出，V2 综合报告放到 `report_v2.py`；
- `config.yaml`：新增 V2 配置段，不删除 V1 配置；
- `ui/streamlit_app.py`：新增模式选择，不改变原有结构化抽取入口。

---

## 3. 技术栈选型

| 层次 | V1 / V2 组件 | 推荐选型 | 说明 |
|---|---|---|---|
| PDF 解析 | 正文 PDF | PyMuPDF | 复用 V1 |
| OCR | 扫描 PDF 降级 | pytesseract + Pillow | 复用 V1 |
| chunk | 父子 chunk | 现有 chunker | 复用 V1 |
| 向量索引 | dense retrieval | ChromaDB | 复用 V1 |
| 关键词检索 | sparse retrieval | rank-bm25 | 复用 V1 |
| 融合召回 | RRF | 现有 `rrf_score` | 复用 V1 |
| rerank | cross-encoder | `BAAI/bge-reranker-large` 或 `OpenScholar/OpenScholar_Reranker` | V2 新增 |
| LLM | synthesis / feedback | 现有 OpenAI-compatible / Anthropic-compatible client | 复用并扩展 |
| schema | records / claims | Pydantic v2 | V2 新增 claim schema |
| 评测 | CO2RR-RAG-Bench | pytest + JSONL/CSV gold data | V2 新增 |
| UI | mode switch | Streamlit | 扩展 V1 UI |

reranker 说明：

- OpenScholar reranker 是面向科学文献综合微调的 reranker，可作为高级选项；
- 默认工程实现建议先支持 Hugging Face cross-encoder 接口；
- 如果本地无法加载 reranker，应自动降级为 RRF 排序，并在日志和 UI 中提示。

---

## 4. 数据对象设计

### 4.1 V1 chunk metadata 复用

V2 继续复用 V1 chunk metadata：

```python
{
    "chunk_id": "paper_01_p3_c12",
    "parent_chunk_id": "paper_01_p3_parent_4",
    "paper_name": "Zhang_2023",
    "filename": "paper_01.pdf",
    "doi": "10.1021/xxx",
    "page": 3,
    "section": "Experimental",
    "is_si": False,
    "text": "...",
}
```

### 4.2 V2 CandidateChunk

RRF 和 reranker 之间传递 `CandidateChunk`。

```python
class CandidateChunk(BaseModel):
    chunk_id: str
    parent_chunk_id: str
    paper_name: str
    filename: str | None = None
    doi: str | None = None
    title: str | None = None
    year: str | None = None
    page: str | int | None = None
    section: str | None = None
    is_si: bool = False
    text: str
    retrieval_text: str
    bm25_rank: int | None = None
    vector_rank: int | None = None
    rrf_score: float | None = None
    rerank_score: float | None = None
    hit_child_ids: list[str] = []
```

### 4.3 SourceCitation

用于统一引用编号和原文证据摘录。

```python
class SourceCitation(BaseModel):
    citation_id: str        # 例如 [S1]
    chunk_id: str
    paper_name: str
    filename: str | None = None
    doi: str | None = None
    page: str | int | None = None
    section: str | None = None
    is_si: bool = False
    evidence_text: str
```

### 4.4 ClaimRecord

V2 的结论级校验围绕 `ClaimRecord`。

```python
class ClaimRecord(BaseModel):
    claim_id: str
    claim_text: str
    citation_ids: list[str]
    support_status: Literal["supported", "partially_supported", "unsupported"]
    support_note: str
    is_agent_analysis: bool = False
```

### 4.5 SynthesisResult

```python
class SynthesisResult(BaseModel):
    query: str
    mode: Literal["synthesis", "deep_reading"]
    answer: str
    claims: list[ClaimRecord]
    structured_records: list[dict] = []
    citations: list[SourceCitation]
    agent_analysis: str | None = None
    uncertainties: list[str] = []
    feedback_trace: list[dict] = []
```

---

## 5. 检索与精排设计

### 5.1 V2 检索流程

```text
query
  |
  |-- keyword expansion
  |
  |-- BM25 top_k=50
  |
  |-- vector top_k=50
  |
  |-- RRF merge
  |
  |-- expand child hits to parent chunks
  |
  |-- candidate_top_k=80
  |
  |-- metadata-aware retrieval_text
  |
  |-- cross-encoder rerank
  |
  |-- max_chunks_per_paper=3
  |
  |-- final_top_n=10
```

### 5.2 RRF 候选集

V1 `hybrid_retrieve` 当前返回最终 top-k parent chunks。V2 需要增加一个可选参数或新函数：

```python
hybrid_retrieve_candidates(
    query: str,
    index: LiteratureIndex,
    llm_client: LLMClient,
    config: dict,
) -> list[CandidateChunk]
```

要求：

- 返回 RRF 排序后的 parent chunks；
- 数量由 `retrieval.candidate_top_k` 控制；
- 每个 parent chunk 保留 `hit_child_ids`；
- 不改变 V1 `hybrid_retrieve` 的默认行为。

### 5.3 Metadata-aware retrieval_text

reranker 输入不直接使用裸 `text`，而是使用 `retrieval_text`：

```text
Title: {title}
DOI: {doi}
Paper: {paper_name}
Section: {section}
Page: {page}
Supporting Information: {is_si}
Text: {text}
```

章节权重建议：

- 问题涉及合成：优先 `Experimental`, `Synthesis`, `Preparation`, `Methods`, SI；
- 问题涉及测试：优先 `Electrochemical Measurements`, `Results`, `Figure caption`, SI；
- 问题涉及机理：优先 `Discussion`, `Mechanism`, `Results`, `Conclusion`。

这些权重可以先作为 prompt 和 retrieval_text 增强，不必在 P0 阶段实现复杂打分器。

### 5.4 Cross-encoder reranker

接口设计：

```python
def rerank_candidates(
    query: str,
    candidates: list[CandidateChunk],
    config: dict,
) -> list[CandidateChunk]:
    ...
```

输入：

- `query`
- candidate parent chunks
- `retrieval_text`

输出：

- 按 `rerank_score` 降序排列的 chunks；
- 每个 chunk 附加 `rerank_score`；
- 应用 `max_chunks_per_paper`；
- 返回 `final_top_n`。

降级策略：

- reranker 未安装：保留 RRF 排序；
- 模型下载失败：保留 RRF 排序；
- GPU 不可用：使用 CPU 或保留 RRF 排序；
- 任一降级都应写入日志，并在 UI 的查询过程里显示提示。

---

## 6. 上下文构建与预算控制

### 6.1 ContextBuilder 输入输出

```python
def build_v2_context(
    query: str,
    ranked_chunks: list[CandidateChunk],
    config: dict,
) -> tuple[str, list[SourceCitation]]:
    ...
```

输出：

- `context_text`：给 LLM 的引用感知上下文；
- `citations`：引用编号到原文 chunk 的映射。

### 6.2 引用编号规则

每个进入上下文的 chunk 分配稳定引用编号：

```text
[S1] Zhang_2023 | paper_01.pdf | page=3 | section=Experimental | SI=false
原文片段...
```

要求：

- `S1`, `S2` 等编号只在本次回答内有效；
- 输出中的引用编号必须来自 `citations`；
- 原文证据摘录按引用编号列出；
- 同一 chunk 不重复分配多个编号。

### 6.3 token 预算

`context_budget.max_context_tokens` 默认 12000。

预算策略：

1. 按 rerank 排序遍历 chunk；
2. 超过 `max_chunks_per_paper` 的同文献 chunk 跳过；
3. 累计 token 估算；
4. 超出预算时停止加入低分 chunk；
5. 保留被跳过 chunk 的统计，方便调试。

token 估算可以先用粗略规则：

```text
estimated_tokens = len(text) / 4
```

后续可替换为模型 tokenizer。

---

## 7. Citation-aware Synthesis 设计

### 7.1 生成入口

```python
def synthesize_with_citations(
    query: str,
    context_text: str,
    citations: list[SourceCitation],
    llm_client: LLMClient,
    config: dict,
) -> str:
    ...
```

### 7.2 Prompt 约束

核心约束：

- 只能使用提供的 context；
- 每个事实性结论必须带 `[Sx]` 引用；
- 不得引用未出现在 context 中的来源；
- 不得合并不同文献的实验条件；
- 原文未明确说明时写“未明确说明”；
- Agent 分析必须单独标注；
- 输出中文 Markdown。

### 7.3 生成输出中间格式

为方便 claim-level verification，建议 synthesis 阶段输出 JSON 中间结构，再由 `report_v2.py` 渲染为 Markdown。

```json
{
  "answer": "...",
  "claims": [
    {
      "claim_text": "...",
      "citation_ids": ["S1", "S3"],
      "is_agent_analysis": false
    }
  ],
  "structured_records": [],
  "agent_analysis": "...",
  "uncertainties": []
}
```

如果 LLM 不稳定，也可以允许先输出 Markdown，再用二次解析抽取 claims。P0 推荐 JSON 中间结构，便于测试。

---

## 8. Self-feedback 与 Follow-up Retrieval

### 8.1 Self-feedback 流程

```text
draft answer
  |
  v
feedback prompt
  |
  v
feedback JSON:
  - unsupported_claims
  - missing_aspects
  - citation_mismatch
  - mixed_paper_conditions
  - need_followup_retrieval
  - followup_queries
  |
  v
if need_followup_retrieval:
    local follow-up retrieval
    rerank
    merge context
    revise
else:
    revise directly
```

### 8.2 FeedbackRecord

```python
class FeedbackRecord(BaseModel):
    unsupported_claims: list[str] = []
    missing_aspects: list[str] = []
    citation_mismatch: list[str] = []
    mixed_paper_conditions: list[str] = []
    need_followup_retrieval: bool = False
    followup_queries: list[str] = []
    revision_instructions: list[str] = []
```

### 8.3 Follow-up Retrieval

```python
def run_followup_retrieval(
    feedback: FeedbackRecord,
    index: LiteratureIndex,
    llm_client: LLMClient,
    config: dict,
) -> list[CandidateChunk]:
    ...
```

要求：

- 只使用本地 index；
- 每条 follow-up query 走 BM25 + vector + RRF + reranker；
- 去重已存在上下文 chunk；
- 合并后重新执行 context budget；
- 最多执行 `self_feedback.max_iterations=1` 轮。

---

## 9. Claim-level Citation Verification

### 9.1 与 V1 evidence 校验的区别

V1 校验：

```text
evidence_sentence 是否出现在 source chunk 中
```

V2 校验：

```text
claim 是否被其引用的 evidence 支持
```

这两者必须同时存在。V2 不能因为 evidence 出现在原文中，就默认 claim 成立。

### 9.2 校验流程

```text
ClaimRecord
  |
  |-- 找到 citation_ids 对应 SourceCitation
  |
  |-- 拼接 evidence_text
  |
  |-- claim-evidence verification
  |
  |-- 输出 supported / partially_supported / unsupported
```

### 9.3 校验策略

P0 阶段推荐组合策略：

1. 规则预检：
   - claim 无 citation -> `unsupported`；
   - citation_id 不存在 -> `unsupported`；
   - claim 涉及数字、单位、电位、FE、温度、时间，但 evidence 中没有对应值 -> `partially_supported` 或 `unsupported`；
2. LLM 判别：
   - 输入 claim + evidence；
   - 输出 `supported / partially_supported / unsupported`；
   - 要求给出简短理由；
3. 保守后处理：
   - LLM 输出不合法时降级为 `unsupported`；
   - 多条 evidence 支持不一致时标为 `partially_supported`；
   - 涉及跨文献共识时，至少需要两篇不同文献的引用，否则降级为 `partially_supported`。

### 9.4 ClaimVerifier 接口

```python
def verify_claims(
    claims: list[ClaimRecord],
    citations: list[SourceCitation],
    llm_client: LLMClient,
    config: dict,
) -> list[ClaimRecord]:
    ...
```

### 9.5 输出过滤规则

- `supported`：进入“综合回答”和“关键结论与证据支持状态”；
- `partially_supported`：降低语气，进入主表但标注原因，或移动到“不确定项”；
- `unsupported`：不得进入综合回答，只能进入“不确定项”或被删除；
- 所有过滤行为应写入 `feedback_trace`。

---

## 10. Markdown V2 报告生成

### 10.1 ReportV2 输入

```python
def generate_markdown_v2(result: SynthesisResult) -> str:
    ...
```

### 10.2 输出结构

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

### 10.3 Evidence 摘录格式

```md
### [S1] Zhang_2023

- 文件名：paper_01.pdf
- DOI：10.1021/xxx
- 页码：3
- 章节：Experimental
- Supporting Information：否

> 原文片段...
```

### 10.4 自动保存

继续复用 V1 的保存规则，建议 V2 文件名增加模式标识：

```text
data/output/YYYYMMDD_HHMMSS_v2_synthesis_{query_keyword}.md
```

---

## 11. 模式路由设计

### 11.1 模式类型

```python
QueryMode = Literal[
    "structured_extraction",
    "synthesis",
    "deep_reading",
]
```

### 11.2 路由规则

结构化抽取模式：

- 包含“合成方法”“测试条件”“FE”“电解液”“表格”“提取”等词；
- 默认调用 V1 extractor。

文献综合模式：

- 包含“总结”“对比”“共同说明”“是否一致”“启发”“综合”等词；
- 调用 V2 synthesis pipeline。

精读解释模式：

- 包含“精读”“解释这篇”“小白”“逐段”“单篇”等词；
- 使用 V2 deep_reading pipeline；
- 可以只检索指定文献或 top-1 文献。

用户在 UI 中显式选择模式时，以用户选择为准。

---

## 12. 配置设计

V2 在 `config.yaml` 中新增配置，不删除 V1 配置。

```yaml
v2:
  mode_enabled: true
  default_mode: auto

retrieval:
  bm25_top_k: 50
  vector_top_k: 50
  rrf_k: 60
  candidate_top_k: 80
  final_top_n: 10
  max_chunks_per_paper: 3
  max_context_tokens: 12000

reranker:
  enabled: true
  model: BAAI/bge-reranker-large
  fallback_to_rrf: true
  device: auto

self_feedback:
  enabled: true
  max_iterations: 1
  allow_followup_retrieval: true
  max_followup_queries: 3

citation_verification:
  enabled: true
  mode: claim_evidence
  allow_partially_supported: true
  verifier_model: ""

external_metadata:
  enabled: false
  providers:
    - crossref
    - semantic_scholar
  cache_path: ./data/external_metadata_cache.json

context_budget:
  max_chunks_per_paper: 3
  max_context_tokens: 12000

output:
  save_v2_trace: true
  save_feedback_trace: true
```

兼容规则：

- `v2.mode_enabled=false` 时，UI 不显示 V2 模式；
- `reranker.enabled=false` 时跳过 rerank；
- `self_feedback.enabled=false` 时单轮生成；
- `external_metadata.enabled=false` 时不得发起外部请求。

---

## 13. 外部元数据增强设计

外部元数据增强为 P3，可选实现，默认关闭。

### 13.1 允许查询的内容

- 标题；
- 作者；
- 年份；
- 期刊；
- 摘要；
- 引用数；
- Semantic Scholar paper id。

### 13.2 禁止行为

- 不自动下载外部全文；
- 不把本地 PDF 全文上传到外部服务；
- 不把外部摘要当作本地 evidence；
- 不用外部元数据覆盖本地解析出的 DOI 或标题，只能补充缺失字段。

### 13.3 缓存

外部 metadata 应缓存到：

```text
data/external_metadata_cache.json
```

缓存 key：

```text
doi:{doi}
title:{normalized_title}
```

---

## 14. UI 设计变更

Streamlit UI 需要新增但不破坏 V1。

### 14.1 新增控件

- 查询模式选择：
  - 结构化抽取模式；
  - 文献综合模式；
  - 精读解释模式；
- V2 高级设置折叠区：
  - 是否启用 reranker；
  - 是否启用 self-feedback；
  - 是否允许二次检索；
  - 是否启用 claim-level verification；
  - final_top_n；
  - max_chunks_per_paper。

### 14.2 查询状态显示

V2 查询过程：

```text
[1/7] 本地混合检索...
[2/7] Cross-encoder 精排...
[3/7] 构建带引用上下文...
[4/7] 生成引用感知初稿...
[5/7] Self-feedback 检查...
[6/7] Claim-level citation verification...
[7/7] 生成 Markdown V2 报告...
```

如果触发二次检索：

```text
[5.1/7] 发现证据缺口，生成 follow-up queries...
[5.2/7] 本地二次检索并重新精排...
```

---

## 15. 评测设计：CO2RR-RAG-Bench

### 15.1 数据格式

建议使用 JSONL：

```json
{
  "question_id": "q001",
  "question": "哪些文献使用 NaBH4 还原法制备 AgNPs？",
  "mode": "synthesis",
  "gold_evidence": [
    {
      "filename": "paper_01.pdf",
      "page": 3,
      "text": "NaBH4 ... was added dropwise ..."
    }
  ],
  "expected_answer_points": [
    "指出 NaBH4 作为还原剂",
    "列出对应文献",
    "不合并其他文献条件"
  ]
}
```

### 15.2 指标

检索指标：

- Recall@K；
- MRR；
- nDCG；
- Evidence Hit Rate。

生成指标：

- Answer Correctness；
- Coverage；
- Unsupported Claim Rate；
- Citation Support Accuracy。

系统指标：

- 平均查询耗时；
- reranker 降级次数；
- follow-up retrieval 触发率；
- V1/V2 输出差异。

### 15.3 V1/V2 对比

每个问题至少保存：

- V1 检索结果；
- V1 输出；
- V2 RRF 候选；
- V2 rerank 后上下文；
- V2 初稿；
- V2 feedback trace；
- V2 最终回答；
- claim verification 结果。

---

## 16. 测试计划

### 16.1 单元测试

新增测试文件建议：

- `tests/test_v2_reranker.py`
- `tests/test_v2_context_builder.py`
- `tests/test_v2_synthesizer.py`
- `tests/test_v2_feedback.py`
- `tests/test_v2_claim_verifier.py`
- `tests/test_v2_report.py`
- `tests/test_v2_router.py`

### 16.2 核心测试用例

Reranker：

- reranker 返回 `rerank_score`；
- reranker 失败时降级为 RRF；
- `max_chunks_per_paper=3` 生效。

ContextBuilder：

- 引用编号稳定；
- 超过 token budget 时截断低分 chunk；
- metadata 出现在 `retrieval_text` 和 context 中。

Synthesis：

- 所有关键 claim 都带 citation_ids；
- 无证据问题返回证据不足；
- 不把不同文献实验条件合并。

Self-feedback：

- 能识别 unsupported claim；
- 能生成 follow-up queries；
- `max_iterations=1` 生效。

ClaimVerifier：

- supported / partially_supported / unsupported 三类都可判定；
- unsupported 不进入主回答；
- partially_supported 降低语气或进入不确定项。

ReportV2：

- Markdown 包含七个指定章节；
- 证据摘录包含文献名、文件名、页码、章节、SI 标记；
- 自动保存文件名包含 `v2_synthesis`。

### 16.3 回归测试

V2 合入后必须继续通过 V1 验收：

```bash
pytest tests/test_acceptance.py -v
```

新增 V2 测试：

```bash
pytest tests/test_v2_*.py -v
```

---

## 17. 实施阶段建议

### Phase 1：P0 最小闭环

目标：实现 V2 文献综合最小可用链路。

范围：

- `reranker.py`；
- `context_builder.py`；
- `synthesizer.py`；
- `claim_verifier.py`；
- `report_v2.py`；
- 配置项；
- 基础单测。

完成标准：

- 本地检索 -> rerank -> citation-aware synthesis -> claim verification -> Markdown V2 输出跑通；
- V1 结构化抽取不受影响。

### Phase 2：P1 自我反馈与二次检索

范围：

- `feedback.py`；
- `followup_retriever.py`；
- feedback trace 保存；
- UI 查询状态扩展。

完成标准：

- 能识别证据缺口；
- 能本地二次检索；
- 能修订答案。

### Phase 3：P2 评测与上下文优化

范围：

- CO2RR-RAG-Bench 初版；
- metadata-aware retrieval 优化；
- token budget 更精确估算；
- V1/V2 对比报告。

### Phase 4：P3 可选增强

范围：

- Crossref / Semantic Scholar metadata；
- 查询历史；
- 多轮对话增强；
- 单篇精读体验优化。

---

## 18. 风险与降级策略

| 风险 | 影响 | 降级策略 |
|---|---|---|
| reranker 模型下载失败 | 无法精排 | 使用 RRF 排序 |
| reranker 速度慢 | 查询耗时增加 | 降低 candidate_top_k 或关闭 reranker |
| LLM citation 输出不规范 | claim 无法校验 | JSON schema 校验失败则重试一次 |
| self-feedback 过度修改 | 删除正确结论 | claim verifier 以 evidence 为准 |
| 二次检索引入噪声 | 答案变散 | 二次检索也必须 rerank 和 budget 控制 |
| 上下文超长 | LLM 截断或成本高 | max_context_tokens 截断 |
| 外部 metadata 不稳定 | 查询失败或慢 | 默认关闭并缓存 |

---

## 19. OpenScholar 到 CO2RR-LocalScholar 的映射

| OpenScholar 机制 | OpenScholar 原路线 | V2 本地化改造 |
|---|---|---|
| Retriever | 大规模 scientific datastore / offline retrieval / API retrieval | 本地 ChromaDB + BM25 + RRF |
| `top_n=10` | 多文献任务默认输入 10 个 passages | `final_top_n=10` parent chunks |
| `ranking_ce` | cross-encoder reranker | 本地 reranker，可降级为 RRF |
| `reranker` | OpenScholar reranker / BGE reranker | 默认 BGE reranker，可选 OpenScholar reranker |
| `feedback` | self-feedback loop | 1 轮中文 CO2RR 自我反馈 |
| `ss_retriever` | feedback 中使用 Semantic Scholar 增强 | 默认关闭；只允许本地 follow-up retrieval |
| `posthoc_at` | posthoc citation attribution | claim-level citation verification |
| `use_abstract` | 用摘要增强 rerank | 本地 metadata-aware retrieval，可选外部摘要 |
| `max_per_paper` | 限制同论文 passages | `max_chunks_per_paper=3` |
| OpenScholar-8B | 专门训练生成模型 | 使用现有云端 LLM，不训练本地 8B |
| ScholarQABench | 自动评测 | CO2RR-RAG-Bench 小型评测集 |

---

## 20. 参考资料

- OpenScholar GitHub README：<https://github.com/akariasai/openscholar>
- OpenScholar reranker model card：<https://huggingface.co/OpenSciLM/OpenScholar_Reranker>
- OpenScholar retriever model card：<https://huggingface.co/OpenScholar/OpenScholar_Retriever>
- Self-RAG GitHub README：<https://github.com/akariasai/self-rag>

