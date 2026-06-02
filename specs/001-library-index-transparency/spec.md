# Feature Specification: 文献库管理与索引透明化

**Feature Branch**: `001-library-index-transparency`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "创建 CO2RR RAG 项目 V3 工程化升级第一阶段：文献库管理与索引透明化"

## Clarifications

### Session 2026-06-02

- Q: 文献库管理页面的数据来源是什么？ → A: 本地 PDF/SI 文件目录 + manifest/parse_report/index 状态文件共同作为文献库管理页面数据来源。
- Q: parse_report 保存在哪里，是否引入数据库？ → A: 使用 JSON/manifest 文件持久化，parse_report 保存为每文档记录或集中 JSON；本阶段不引入数据库。
- Q: 单篇重新解析和重建索引的行为边界是什么？ → A: 重新解析和索引重建分离；各自只处理单篇文档范围，失败时保留可用旧记录并报告结果。
- Q: 删除文献时是否同步删除 ChromaDB、BM25 和 parent store？ → A: 同步尝试删除 manifest、parse_report、chunk、ChromaDB、BM25、parent store 记录，并逐项报告成功/失败。
- Q: 如何保证不破坏现有 V1 结构化抽取和 V2 文献综合入口？ → A: 新增独立管理入口；V1 结构化抽取和 V2 文献综合默认入口、参数和结果格式保持不变，并以回归/冒烟测试验收。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 查看文献库状态 (Priority: P1)

CO2RR 研究用户需要在系统界面中查看当前文献库内所有主文献和 Supporting Information 文件，并快速判断每篇文献是否完成解析、是否完成索引、是否存在失败原因。

**Why this priority**: 这是文献可管理和索引透明化的最小可用能力；没有全局状态视图，用户无法判断当前 RAG 回答建立在哪些文献基础上。

**Independent Test**: 使用包含成功解析、部分解析、失败解析、未索引、已索引和 Supporting Information 的样本文献库，打开文献库管理页面即可验证所有字段和状态是否完整展示。

**Acceptance Scenarios**:

1. **Given** 文献库中存在多篇主文献和 Supporting Information，**When** 用户进入文献库管理页面，**Then** 系统显示标题、文件名、DOI、年份、期刊、SI 标记、主文献关系、解析状态、索引状态、页数、已解析页数、chunk 数量、表格数量、图注数量、OCR 使用情况和最后更新时间。
2. **Given** 某篇 PDF 解析失败，**When** 用户查看文献库列表，**Then** 系统在该文献行显示失败状态，并提供可进入详情或解析报告查看失败原因的入口。
3. **Given** Supporting Information 已与主文献建立关联，**When** 用户查看文献库列表，**Then** 系统清楚显示该文件是 SI，并显示其关联主文献。

---

### User Story 2 - 查看单篇文献解析与索引详情 (Priority: P1)

CO2RR 研究用户需要点击某篇文献查看详情，确认该文献的解析报告、chunk 列表、chunk 页码、所属章节、SI 来源、文本预览、索引状态和错误日志。

**Why this priority**: 单篇详情是定位解析缺失、chunk 异常和索引失败的核心入口，也是后续证据追溯和检索调试的基础。

**Independent Test**: 选择一篇已成功解析并完成索引的文献、一篇部分解析文献和一篇失败文献，分别进入详情页验证报告、chunk、状态和错误信息是否与实际处理结果一致。

**Acceptance Scenarios**:

1. **Given** 一篇文献已成功解析并生成多个 chunk，**When** 用户打开文献详情，**Then** 系统显示文献基本信息、完整解析报告、chunk 列表、每个 chunk 的页码、章节、SI 标记和文本预览。
2. **Given** 一篇文献解析过程中产生警告，**When** 用户查看解析报告，**Then** 系统显示警告内容、解析状态、总页数、已解析页数、文本长度、表格数量、图注数量和 OCR 使用情况。
3. **Given** 一篇文献索引失败，**When** 用户打开文献详情，**Then** 系统显示索引失败阶段和失败原因，不把该文献误标为可用索引。

---

### User Story 3 - 重建解析与索引 (Priority: P2)

CO2RR 研究用户需要对单篇文献重新解析、对单篇文献重建索引，并在必要时执行全量重建索引，同时看到处理进度和完成摘要。

**Why this priority**: 当 PDF 解析质量、chunk 策略或索引内容异常时，用户需要可控地修复单篇或全库索引，而不是手动清理数据文件。

**Independent Test**: 对一篇已存在文献执行重新解析和单篇索引重建，对全库执行索引重建，验证进度、状态迁移、chunk 数量和失败摘要是否准确。

**Acceptance Scenarios**:

1. **Given** 用户选择重新解析某篇文献，**When** 系统开始处理，**Then** 页面显示当前文件名、当前阶段、错误提示和完成后的解析摘要。
2. **Given** 用户选择重建某篇文献索引，**When** 系统完成处理，**Then** 该文献的解析状态、chunk 数量、索引状态和最后更新时间反映最新结果。
3. **Given** 用户执行全量重建索引，**When** 重建运行中，**Then** 系统显示已完成文献数量、失败文献数量、当前文献 chunk 数和最终完成摘要。

---

### User Story 4 - 删除文献及关联记录 (Priority: P2)

CO2RR 研究用户需要从文献库中删除某篇文献，并同步处理或明确提示其关联 chunk、关键词索引、向量索引和父级 chunk 记录的处理结果。

**Why this priority**: 删除能力避免文献库长期积累错误或重复文献，并防止已删除文献继续参与后续 RAG 检索和回答。

**Independent Test**: 删除一篇已索引文献后，验证列表不再显示该文献，详情不可访问，后续查询不会返回该文献的 chunk；若任何关联记录无法删除，系统必须显示明确结果。

**Acceptance Scenarios**:

1. **Given** 一篇文献已有解析报告和索引记录，**When** 用户确认删除，**Then** 系统删除文献记录并同步处理对应 chunk 与索引记录，或逐项提示未能处理的记录及原因。
2. **Given** 用户尝试删除一篇关联 Supporting Information 的主文献，**When** 删除操作会影响关联文件，**Then** 系统在确认前提示影响范围，避免用户误删关联数据。

### Evidence & Verification Expectations *(mandatory for RAG features)*

- **Citation Evidence**: 本功能本身不生成新的 CO2RR 科学结论；当页面展示 chunk 文本、页码、章节、SI 来源或错误日志时，这些信息必须可回溯到对应文献、文件名、document_id、chunk_id 和页码。
- **Insufficient Evidence Behavior**: 原有问答、结构化抽取和文献综合入口的证据不足行为必须保持不变；如果用户从文献详情或管理页发起与文献内容相关的结论性查询，仍必须在证据不足时回答"当前文献证据不足"。
- **Debug Trace Visibility**: 本阶段只要求展示解析、chunk、embedding、关键词索引、向量索引和父级 chunk 保存的状态与错误；完整检索 Debug Trace 不在本阶段范围内。
- **Model Inference Separation**: 页面中的解析报告、索引状态和 chunk 元数据必须作为处理事实展示；任何由模型生成或推断的标题、DOI、年份、期刊或章节信息必须与直接解析得到的字段可区分，并保留来源说明或低置信提示。

### Edge Cases

- 文献库为空时，系统显示空状态和可执行的下一步操作，不显示错误页面。
- PDF 文件损坏、受密码保护、无可解析文本或 OCR 后仍失败时，系统生成 failed 解析报告并记录错误原因。
- PDF 只解析出部分页面时，系统标记 partial，并显示总页数、已解析页数和警告。
- Supporting Information 无法自动关联主文献时，系统仍显示该 SI 文件，并将主文献关系标记为未关联。
- DOI、年份、期刊或标题缺失时，系统允许字段为空或标记未知，但不得阻止文献进入管理列表。
- 单篇重建索引失败时，系统不得清空该文献仍可用的旧状态，除非用户已确认覆盖或清理。
- 单篇重新解析或单篇索引重建失败时，系统应保留该文档仍可用的旧解析或旧索引记录，并报告新旧状态差异和失败原因。
- 全量重建过程中部分文献失败时，系统保留成功文献结果，并在摘要中列出失败文献和原因。
- 删除关联记录时某一类索引清理失败，系统必须显示逐项结果，避免用户误以为文献已完全移除。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a literature library management page that lists all known PDF and Supporting Information files discovered from the local literature directories, enriched by available manifest, parse_report, and index status records.
- **FR-002**: System MUST display, for each listed document, title, filename, DOI, year, journal, SI status, main-document relationship, parse status, index status, total pages, parsed pages, chunk count, table count, figure-caption count, OCR usage, and last updated time.
- **FR-003**: Users MUST be able to open a document detail view from the library list.
- **FR-004**: Users MUST be able to view a parse report for each document after parsing has completed, partially completed, or failed.
- **FR-005**: System MUST create or update one parse report per processed PDF containing document_id, filename, paper_title, doi, year, journal, is_si, main_document_id, parse_status, pages_total, pages_parsed, text_length, chunks_created, tables_found, figure_captions_found, ocr_used, error_message, warnings, created_at, and updated_at.
- **FR-005a**: System MUST persist parse_report data in project-managed JSON or manifest files that survive application restarts; this feature MUST NOT require a new database as the primary persistence layer.
- **FR-006**: System MUST restrict parse_status values to success, partial, and failed.
- **FR-007**: System MUST track index_status for every document using not_indexed, parsing, parsed, chunked, embedding, indexed, or failed.
- **FR-008**: System MUST record whether parsing completed, chunks were generated, embeddings completed, vector index write succeeded, keyword index write succeeded, parent chunk storage succeeded, and any failure reason for each document.
- **FR-009**: System MUST show index progress while indexing or rebuilding is running, including current filename, current stage, completed document count, failed document count, current document chunk count, error messages, and completion summary.
- **FR-010**: Users MUST be able to trigger single-document re-parse from the management or detail view.
- **FR-011**: Users MUST be able to trigger single-document index rebuild from the management or detail view.
- **FR-011a**: System MUST keep single-document re-parse and single-document index rebuild as separate operations: re-parse updates that document's parse report and derived chunk records, while index rebuild updates only that document's index records from available parsed content.
- **FR-011b**: System MUST NOT turn a single-document operation into a full-library rebuild unless the user explicitly starts a full rebuild.
- **FR-012**: Users MUST be able to trigger full index rebuild and see progress across the whole document set.
- **FR-013**: Users MUST be able to delete a document and receive a per-record outcome for associated chunks, keyword index records, vector index records, parent chunk records, parse report, and library manifest.
- **FR-013a**: Deleting a document MUST attempt to remove or invalidate the associated library manifest entry, parse_report, chunk records, vector index records, keyword index records, and parent chunk store records in the same user-visible operation.
- **FR-014**: The document detail view MUST show basic metadata, parse_report, chunk list, chunk page numbers, chunk sections, SI origin, chunk text preview, index status, and error logs.
- **FR-015**: System MUST preserve existing RAG query entry points, structured extraction mode, and literature synthesis mode behavior while adding library management capabilities.
- **FR-015a**: System MUST add the literature management experience as an independent management entry point; existing V1 structured extraction and V2 literature synthesis default entry points, parameters, and output formats MUST remain unchanged for this feature.
- **FR-016**: System MUST keep library and index state persistent across application restarts.
- **FR-017**: System MUST expose document and chunk identifiers consistently enough for later retrieval debugging, evidence tracing, evaluation, and deployment work.
- **FR-018**: System MUST protect real API keys and research data paths through configuration when this feature touches model, embedding, database, or vector-store settings.
- **FR-019**: System MUST avoid deleting or overwriting research PDFs or existing index data without a user-visible confirmation and a recoverable or clearly documented outcome.
- **FR-020**: System MUST document the library management page usage, supported actions, known limitations, and data-safety expectations in README or development documentation.

### Key Entities *(include if feature involves data)*

- **Document**: A main PDF or Supporting Information file discovered from the local literature directories and enriched by manifest, parse_report, and index status records. Key attributes include document_id, filename, title, DOI, year, journal, SI status, main-document relationship, parse status, index status, counts, timestamps, and error summary.
- **Parse Report**: A per-document record describing parse outcome, metadata extracted, processing counts, warnings, errors, OCR usage, creation time, and update time.
- **Library Manifest**: A project-managed JSON or manifest record set that links discovered files, parse reports, document identifiers, and index status without requiring a database in this feature.
- **Index Status**: A per-document state record describing the current processing stage and whether parsing, chunking, embedding, keyword indexing, vector indexing, and parent chunk storage succeeded.
- **Chunk Record**: A searchable literature fragment associated with a document, including chunk_id, page number, section, SI origin, text preview, parent relationship, and index availability.
- **Index Operation**: A user-triggered re-parse, single-document rebuild, full rebuild, or delete operation with progress, stage, counts, errors, and completion summary.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can open the literature library page and identify every known PDF or Supporting Information file in the local collection within 30 seconds for a collection of at least 100 documents.
- **SC-002**: For at least 95% of documents with completed processing records, the page displays parse status, index status, chunk count, page counts, OCR usage, and last updated time without requiring the user to inspect raw files.
- **SC-003**: For every failed or partially successful parse in a representative test set, the user can view an error message or warning explaining the failure or limitation.
- **SC-004**: A user can complete single-document re-parse or single-document index rebuild from the interface and see a final success or failure summary without restarting the application.
- **SC-005**: During full index rebuild, progress information updates at each document boundary and at each major processing stage, so the user can identify the current file and failed count at any time.
- **SC-006**: Deleting an indexed document prevents that document's chunks from appearing in subsequent retrieval results, or clearly reports any remaining records that could not be removed.
- **SC-006a**: After document deletion, the deletion summary identifies the outcome for manifest, parse_report, chunks, vector index, keyword index, and parent chunk records separately.
- **SC-007**: Existing RAG query, structured extraction, and literature synthesis workflows remain usable after this feature is enabled, as verified by the current project regression checks or documented smoke tests.
- **SC-007a**: Regression or smoke-test evidence must show that V1 structured extraction and V2 literature synthesis can still be launched through their existing entry points and produce their expected output formats after this feature is enabled.
- **SC-008**: User-facing documentation explains the library management page, parse_report fields, index_status meanings, rebuild actions, deletion behavior, and known limitations before the feature is accepted.

## Assumptions

- 本功能是 V3 工程化升级第一阶段，优先级为 P0，因为它直接支撑后续检索调试、证据追溯、评测和部署。
- 目标用户是本地运行 CO2RR 文献 RAG 系统的研究者或开发者，默认拥有对本地文献库的管理权限。
- 文献库来源仍为本地已有 PDF 和 Supporting Information 文件；本阶段不联网下载文献。
- 文献库管理页面以本地 PDF/SI 文件发现为基础，并合并 manifest、parse_report 和现有索引状态；未索引或解析失败的本地文件仍应进入列表。
- 对缺失元数据采取保守显示策略：允许未知、空值或低置信提示，不因元数据缺失阻断解析报告生成。
- 本阶段以 JSON/manifest 文件实现最小可用持久化，不引入新的数据库系统；后续功能可在不改变用户可见行为的前提下迁移到数据库。
- 完整检索 Debug Trace、claim-level citation verification 升级、文献综合增强、多 Agent、Docker 部署和服务化接口均不属于本功能范围。
- 本功能范围包括文献库列表、解析报告、索引状态、进度展示、单篇重新解析、单篇索引重建、全量索引重建、删除及文档说明；完整检索 Debug Trace、claim-level citation verification 升级、文献综合增强、多 Agent、联网下载、Docker 部署和服务化接口推迟到后续 Feature。
- 单篇重建和删除操作需要用户确认；全量重建操作需要用户明确启动并能看到进度。

## Documentation & Data Safety *(mandatory)*

- **Priority Scope**: P0。本功能是 V3 第一阶段工程化能力，解决文献不可管理、索引不可观察的问题，并为证据追溯、检索调试和评测提供基础。
- **Documentation Impact**: 需要同步 README 或开发文档；后续计划阶段应评估是否更新 PRD_V3、TDD、DEV_PLAN、TASKS 和项目上下文文档。
- **Data Protection**: 本功能会触及上传或本地 PDF、解析报告、chunk 记录、关键词索引、向量索引和 parent chunk store。删除、重建或覆盖前必须有用户可见确认；处理结果必须明确说明成功、失败和残留记录。
- **Branch Expectation**: feature/* 类型分支；当前 Spec Kit 分支为 `001-library-index-transparency`。
