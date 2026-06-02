# Research: 文献库管理与索引透明化

## Decision: 本阶段使用 JSON/manifest 作为最小持久化方案

**Rationale**: 规格明确要求不引入数据库。现有项目已经有 `data/index_manifest.json`、`data/chroma_db/`、`bm25.pkl` 和 `parent_store.pkl`，使用 JSON 可以复用当前数据目录和配置路径，降低实现风险，并满足应用重启后状态保留。

**Alternatives considered**:

- SQLite：便于查询但违反“不引入数据库”的阶段约束。
- 只使用 `index_manifest.json`：字段会过度膨胀，难以表达解析报告、阶段状态和操作摘要。
- Streamlit session state：不能跨重启持久化，不满足 FR-016。

## Decision: parse_report 采用每文档一个 JSON 文件

**Rationale**: 单篇重新解析必须只影响当前文献。每文档文件能隔离失败、减少并发/半写入影响，并便于删除时逐项报告 parse_report 清理结果。默认目录为 `data/parse_reports/{document_id}.json`。

**Alternatives considered**:

- 集中 `parse_reports.json`：写入简单，但单篇失败或半写入会影响整个报告集合。
- 嵌入 `index_manifest`：会把解析事实与索引状态耦合，不利于“重新解析”和“重建索引”分离。

## Decision: index_status 采用集中 JSON 文件

**Rationale**: UI 需要快速聚合所有文献的索引状态、阶段、失败原因和最近操作摘要。集中 `data/index_status.json` 对 100 篇级别文献足够简单，且能与 `index_manifest` 保持兼容。

**Alternatives considered**:

- 每文档 index_status 文件：删除和单篇更新更隔离，但列表页需要大量文件读取。
- 只从 ChromaDB/BM25 推断状态：无法可靠表达失败阶段、旧状态保留和操作摘要。

## Decision: document_id 使用稳定文件身份，filename 保持兼容键

**Rationale**: 当前 manifest 以 filename 为 key，必须兼容。新增 `document_id` 用于 parse_report、index_status、chunk metadata 和删除定位。推荐从规范化相对路径和文件 fingerprint 生成；如果旧 manifest 缺少 `document_id`，聚合层应临时生成兼容 ID，不阻止页面展示。

**Alternatives considered**:

- 只用 filename：重名、移动目录和 SI 关联会变脆。
- 只用 DOI：SI、缺 DOI 或 DOI 解析失败文献无法稳定管理。

## Decision: 单篇重新解析与单篇索引重建必须拆成两个操作

**Rationale**: 规格要求两者分离。重新解析只更新解析事实和派生 chunk 计数，不自动覆盖可用索引；索引重建只基于当前解析内容更新该文献的 ChromaDB/BM25/parent store/index_status。这样失败时可以保留旧可用记录并报告新旧差异。

**Alternatives considered**:

- 重新解析后自动索引：操作语义不清，失败时难以判断解析失败还是索引失败。
- 单篇操作触发全库重建：违反 FR-011b，且增加数据保护风险。

## Decision: 删除文献只默认删除关联记录，不默认删除 PDF 本体

**Rationale**: 原始 PDF 属于研究数据，constitution 要求避免未经确认删除研究资料。删除操作应逐项尝试 manifest、parse_report、chunk、ChromaDB、BM25、parent store 和 index_status 清理，并返回每项成功/失败/跳过。

**Alternatives considered**:

- 同时删除 PDF：风险高，且规格关注的是删除文献及关联索引记录。
- 只删除 manifest：会留下可检索 chunk，违反 SC-006。

## Decision: Streamlit 使用独立管理入口并保留 V1/V2 默认入口

**Rationale**: 规格要求保留现有 V1 结构化抽取和 V2 文献综合入口。新增管理入口可通过 `st.tabs()`、sidebar radio 或页面 section 接入，但不得改变现有查询默认模式、参数和输出格式。

**Alternatives considered**:

- 替换现有首页为管理页：会破坏既有查询流程。
- 单独新应用文件：减少耦合，但用户需要启动不同入口，不利于当前本地工作流。
