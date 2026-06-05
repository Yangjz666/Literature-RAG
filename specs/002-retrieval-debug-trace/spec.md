# Feature Specification: 检索调试 Debug Trace

**Feature Branch**: `feature/002-retrieval-debug-trace`

**Created**: 2026-06-05

**Status**: Draft

**Input**: User description: "为 CO2RR 文献 RAG Agent V3 增加检索调试 Debug Trace，使每次 RAG 查询的检索链路可观察、可调试、可展示；只做旁路记录和界面展示，不重写现有 RAG 主流程。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 查看回答背后的检索片段 (Priority: P1)

作为普通用户，我希望在得到 RAG 回答后，可以展开查看系统检索到了哪些文献片段，从而判断回答是否可信。

**Why this priority**: 这是本功能的最小可用价值。CO2RR 文献助手必须让用户看到回答依据，否则无法满足 evidence-first 和可追溯要求。

**Independent Test**: 完成一次普通文献问答后，用户展开调试面板，能看到原始问题、检索模式、最终上下文片段和每个片段的来源信息。

**Acceptance Scenarios**:

1. **Given** 用户完成一次有答案的 RAG 查询，**When** 用户展开“检索调试 Debug Trace”，**Then** 系统展示本次查询的原始问题、检索模式、最终上下文片段、查询耗时和最终回答。
2. **Given** 某个上下文片段来自本地文献库，**When** 用户查看该片段，**Then** 系统展示 filename、page、section、chunk_id、score 和 text_preview。
3. **Given** 某阶段没有可展示数据，**When** 用户查看调试面板，**Then** 系统显示“当前阶段未启用”或 `not_available`，而不是空白或报错。

---

### User Story 2 - 定位检索链路质量问题 (Priority: P2)

作为开发者，我希望看到关键词检索、向量检索、融合排序、重排序和最终上下文的中间结果，从而定位检索效果差的原因。

**Why this priority**: 检索质量问题可能出现在多个阶段。阶段级可见性可以减少排查时间，并避免无依据地修改主流程。

**Independent Test**: 使用同一个问题执行查询后，开发者能在调试面板中分别查看已启用检索阶段的 Top K 结果，并确认未启用阶段被标记为 `not_available`。

**Acceptance Scenarios**:

1. **Given** 查询流程包含关键词检索和向量检索，**When** 开发者查看调试面板，**Then** 系统分别展示两个阶段的结果列表和每条结果的来源、分数、片段预览。
2. **Given** 当前项目未启用某个融合或排序阶段，**When** 开发者查看对应区域，**Then** 系统明确展示 `not_available`。
3. **Given** 最终上下文与早期召回结果不同，**When** 开发者对比各阶段结果，**Then** 系统提供足够的 chunk 标识和来源信息用于判断差异来源。

---

### User Story 3 - 查询失败时定位失败阶段 (Priority: P2)

作为用户，我希望当查询失败时，系统能告诉我失败发生在哪个阶段，而不是只显示难以理解的错误信息。

**Why this priority**: 失败阶段定位能减少用户困惑，也能让开发者快速判断问题属于检索、上下文构建、回答生成还是引用解析。

**Independent Test**: 模拟任一查询阶段失败后，调试面板仍能打开，并显示 failed_stage、用户可读失败原因和可用的部分结果。

**Acceptance Scenarios**:

1. **Given** 查询在向量检索阶段失败，**When** 用户查看调试面板，**Then** 系统展示 failed_stage 为 `vector_search_failed`，并显示用户可读失败原因。
2. **Given** 查询失败前已有部分检索结果，**When** 用户查看调试面板，**Then** 系统保留并展示已产生的部分结果。
3. **Given** 查询出现未知失败，**When** 用户查看调试面板，**Then** 系统展示 `unknown_failed` 和简洁错误说明，不直接暴露完整内部 traceback。

---

### User Story 4 - 追溯回答引用到具体证据 (Priority: P3)

作为科研用户，我希望回答中的引用能对应到具体文献、页码、section 和 chunk，方便我回到原文核查。

**Why this priority**: 这能增强科研核查效率，但本阶段只做基础结果追溯，不承担完整 claim-level citation verification。

**Independent Test**: 完成一次包含引用或证据片段的查询后，用户能在调试面板中看到 citation/evidence 与最终上下文 chunk 的匹配状态。

**Acceptance Scenarios**:

1. **Given** 最终回答包含可解析 citation，**When** 用户查看引用追溯区域，**Then** 系统展示 citation 对应的 filename、page、section、chunk_id 和 evidence_text preview。
2. **Given** 某 citation 无法匹配最终上下文 chunk，**When** 用户查看引用追溯区域，**Then** 系统将该 citation 标记为 `unmatched`。
3. **Given** 用户查看引用追溯区域，**When** 系统展示结果，**Then** 系统不声称该 claim 已被自动验证，只展示基础匹配关系。

### Evidence & Verification Expectations *(mandatory for RAG features)*

- **Citation Evidence**: 调试面板展示的最终上下文片段和回答引用必须尽量包含 filename、page、section、chunk_id、parent_chunk_id（如有）、score 和 evidence/text preview。科学结论不得脱离最终上下文展示为“已证实”。
- **Insufficient Evidence Behavior**: 本功能不改变原有证据不足策略。若回答链路判断证据不足，系统仍应拒绝无证据结论或标注证据不足，并在调试面板中展示最终上下文为空、过弱或不可用的状态。
- **Debug Trace Visibility**: 本功能必须展示原始问题、改写后问题状态、查询模式、关键词检索、向量检索、融合排序、重排序、最终上下文、最终回答、引用追溯、耗时、警告、错误和失败阶段；未启用阶段显示 `not_available`。
- **Model Inference Separation**: 本功能只展示回答、检索上下文和引用追溯，不将模型推理自动标记为文献事实；引用匹配不等同于 claim-level citation verification。

### Edge Cases

- 查询流程没有问题改写能力时，rewritten_query 显示 `not_available`。
- 查询流程未启用融合排序或重排序时，对应阶段显示 `not_available`。
- 某条检索结果缺少 page、section、parent_chunk_id 或 score 时，调试面板仍展示可用字段，并对缺失字段显示 `not_available`。
- text_preview 必须限制长度，避免过长全文影响页面阅读或泄露过多本地文献内容。
- 查询失败时，调试记录仍应尽量保留已完成阶段的结果、failed_stage、failure_reason 和 warning。
- 调试记录生成本身失败时，不应导致原本可完成的 RAG 查询失败。
- 引用无法匹配最终上下文 chunk 时，应标记 `unmatched`，不得伪造匹配关系。
- 用户连续执行多次查询时，页面应展示当前查询的调试记录，并避免与上一轮查询混淆。
- 本地文献库、索引或配置缺失时，调试面板应显示用户可读提示，不直接展示敏感路径或密钥。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create one debug trace for each completed or failed RAG query attempt.
- **FR-002**: Each debug trace MUST include trace_id, created_at, user_query, original_query, rewritten_query, query_mode, final_answer, elapsed_ms, warning, error, and failed_stage.
- **FR-003**: Each debug trace MUST record keyword retrieval results when that stage is available, including Top K chunk entries and their source metadata.
- **FR-004**: Each debug trace MUST record vector retrieval results when that stage is available, including Top K chunk entries and their source metadata.
- **FR-005**: Each debug trace MUST record fusion results when that stage is available, and MUST show `not_available` when it is not enabled.
- **FR-006**: Each debug trace MUST record reranking results when that stage is available, and MUST show `not_available` when it is not enabled.
- **FR-007**: Each debug trace MUST record final_context_chunks representing the context selected for answer generation.
- **FR-008**: Each recorded chunk result MUST include document_id, filename, page, section, chunk_id, parent_chunk_id when present, score when present, source_stage, and text_preview.
- **FR-009**: System MUST keep text previews bounded so debug trace display does not present full long-form document text by default.
- **FR-010**: Users MUST be able to expand a “检索调试 Debug Trace” panel after each RAG query without disrupting the normal answer reading flow.
- **FR-011**: The debug panel MUST default to collapsed for ordinary answer viewing.
- **FR-012**: The debug panel MUST present stage results in structured sections or tables and MUST also allow viewing the raw debug trace object.
- **FR-013**: System MUST display original_query, rewritten_query, query_mode, elapsed_ms, warning, error, and failed_stage in user-readable form.
- **FR-014**: System MUST capture citations_used or evidence references from the final answer when available.
- **FR-015**: Each citation/evidence entry MUST display filename, page, section, chunk_id, evidence_text preview, and match status when available.
- **FR-016**: System MUST mark citation/evidence entries as `unmatched` when they cannot be associated with a final_context_chunk.
- **FR-017**: System MUST NOT perform or claim complete citation verification, claim-level truth judgment, or automatic conclusion validation in this feature.
- **FR-018**: System MUST record failed_stage using one of the recognized stage labels: query_rewrite_failed, bm25_failed, vector_search_failed, rrf_failed, reranker_failed, context_builder_failed, llm_failed, citation_parse_failed, or unknown_failed.
- **FR-019**: System MUST display a user-readable failure reason when a query fails, without exposing raw internal traceback as the primary message.
- **FR-020**: Debug trace recording failure MUST NOT cause an otherwise successful RAG query to fail.
- **FR-021**: System MUST keep debug trace data in the current user session by default and MUST NOT introduce a database for this feature.
- **FR-022**: If future local persistence is enabled, debug trace files MUST be treated as local runtime data and excluded from version control.
- **FR-023**: System MUST preserve existing document query, structured extraction, literature synthesis, and Feature 001 document library/index transparency entry points.
- **FR-024**: System MUST NOT change existing local index storage formats or require rebuilding the whole literature library solely to enable debug trace.
- **FR-025**: System MUST protect real API keys, local research paths, local PDF contents, vector-store contents, and other sensitive runtime data from being committed or exposed unnecessarily.
- **FR-026**: System MUST update project progress documentation for this feature before claiming implementation completion.

### Key Entities *(include if feature involves data)*

- **Debug Trace**: A per-query record that captures the original user input, query mode, stage results, final context, final answer, citations, timing, warnings, errors, and failed stage.
- **Stage Result Set**: A grouped set of retrieval or ranking results for one stage, such as keyword retrieval, vector retrieval, fusion, reranking, or final context selection.
- **Trace Chunk Result**: A single literature chunk shown in a stage result set, including document identity, location metadata, score, source stage, and bounded text preview.
- **Citation Evidence Match**: A citation or evidence reference extracted from the final answer and matched, when possible, to a final context chunk.
- **Failure Stage**: A normalized label identifying where a query failed, used for user-facing diagnosis and developer debugging.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a successful RAG query, users can open the debug trace panel and identify at least one final context chunk source within 10 seconds.
- **SC-002**: For enabled retrieval stages, at least 95% of displayed chunk rows include filename, chunk_id, source_stage, and text_preview.
- **SC-003**: For unavailable stages, 100% of debug traces display `not_available` or an equivalent user-readable “当前阶段未启用” message instead of failing silently.
- **SC-004**: For simulated failures in recognized stages, 100% of debug traces display failed_stage and a user-readable failure reason.
- **SC-005**: Debug trace capture adds no more than minor user-visible delay to ordinary local queries, with the answer display still appearing within the same expected interaction flow.
- **SC-006**: Existing document query, structured extraction, literature synthesis, and Feature 001 document library/index transparency entry points remain accessible after the feature is implemented.
- **SC-007**: At least one automated test covers successful trace creation, unavailable stages, citation matching or unmatched citation handling, and failure-stage recording before implementation is accepted.
- **SC-008**: No real API key, private local PDF path, local index artifact, or debug trace runtime artifact is included in version control as part of this feature.

## Assumptions

- This is a V3 P0/P1-adjacent observability feature and should be developed on `feature/002-retrieval-debug-trace` from `V3-DEV`.
- The current application already has at least one RAG query path that produces a final answer and a final context or retrievable evidence source.
- Some retrieval stages may not currently exist or may not expose intermediate results; those stages should be represented as `not_available` rather than forcing architecture rewrites.
- Query rewrite may not be enabled in the current project; rewritten_query can therefore be `not_available`.
- Debug trace data is intended for current-page diagnosis by default, not long-term audit storage.
- This feature is separate from complete citation verification and does not judge whether every answer claim is fully supported.
- Tests for this feature should use mock or fixture data and should not depend on real LLM calls, real embedding APIs, or a private PDF library.

## Documentation & Data Safety *(mandatory)*

- **Priority Scope**: V3 P0/P1 support feature. The constitution names Debug Trace as part of the verifiable RAG workflow, and this feature improves trust, diagnosis, and acceptance without changing scientific conclusions.
- **Documentation Impact**: Must maintain `CURRENT_TASK.md` and `specs/002-retrieval-debug-trace/PROGRESS.md`; after planning/implementation, update relevant quickstart or user documentation, and add or update retrieval debug documentation if the user-facing behavior changes.
- **Data Protection**: This feature must not commit `.env`, API keys, private PDF paths, local index artifacts, local debug trace runtime artifacts, or private research data. It must not require changing existing vector, keyword, or parent chunk storage formats.
- **Branch Expectation**: `feature/*`, specifically `feature/002-retrieval-debug-trace`, with eventual merge target `V3-DEV` after planning, tasks, implementation, tests, documentation sync, and acceptance.
