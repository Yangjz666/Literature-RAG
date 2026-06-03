# Tasks: 文献库管理与索引透明化

**Input**: Design documents from `/specs/001-library-index-transparency/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: 本 Feature 触及本地状态持久化、索引状态、Streamlit 管理入口和现有 V1/V2 回归，因此包含基础 pytest、轻量 UI/契约测试和手工验收任务。

**Scope Guard**: 本任务清单只做文献库管理与索引透明化；不得加入完整 Debug Trace、citation verification、FastAPI、Docker、数据库、联网下载或 V1/V2 主流程重写。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 确认当前分支、路径和实现边界，避免任务执行时扩大范围。

- [X] T001 Confirm current branch is `001-library-index-transparency` and record implementation scope in `CURRENT_TASK.md`
- [X] T002 [P] Review existing PDF parsing, chunking, indexing, and Streamlit entry points in `app/ingest.py`, `app/chunker.py`, `app/indexer.py`, and `ui/streamlit_app.py`
- [X] T003 [P] Review existing config paths and add planned path notes for `data/parse_reports/` and `data/index_status.json` in `config.yaml`
- [X] T004 [P] Confirm no real API keys or research data paths need to be added to `config.yaml` or `.env`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 建立 parse_report、index_status 和原子 JSON 文件读写能力；这些是所有 user story 的共享基础。

**Critical**: No user story work can begin until this phase is complete.

- [X] T005 Create `ParseStatus` constants and parse_report field defaults in `app/parse_report.py`
- [X] T006 Implement `document_id` generation helper using stable file identity in `app/parse_report.py`
- [X] T007 Implement parse_report validation for required fields and allowed `success`, `partial`, `failed` statuses in `app/parse_report.py`
- [X] T008 Implement atomic JSON save and load helpers for per-document reports in `app/parse_report.py`
- [X] T009 Implement parse_report listing and diff helpers in `app/parse_report.py`
- [X] T010 Create `IndexStatus` constants and stage field defaults in `app/index_status.py`
- [X] T011 Implement index_status validation for `not_indexed`, `parsing`, `parsed`, `chunked`, `embedding`, `indexed`, and `failed` in `app/index_status.py`
- [X] T012 Implement atomic load, save, update, and failure-record helpers for `data/index_status.json` in `app/index_status.py`
- [X] T013 Implement operation summary helpers for reparse, rebuild_index, full_rebuild, and delete in `app/index_status.py`
- [X] T014 [P] Add unit tests for parse_report validation, save, load, list, and diff behavior in `tests/test_parse_report.py`
- [X] T015 [P] Add unit tests for index_status state validation, failure recording, and operation summaries in `tests/test_index_status.py`

**Checkpoint**: parse_report and index_status primitives are ready and tested.

---

## Phase 3: User Story 1 - 查看文献库状态 (Priority: P1) MVP

**Goal**: 用户进入文献库管理入口后，可以看到本地 PDF/SI、manifest、parse_report 和 index_status 聚合后的文献列表。

**Independent Test**: 使用包含本地 PDF/SI、旧 manifest、成功/失败 parse_report、未索引 index_status 的样本目录，打开文献库管理页面即可验证所有列表字段完整展示。

### Tests for User Story 1

- [X] T016 [P] [US1] Add document library aggregation tests for empty folder, local PDF discovery, and SI detection in `tests/test_document_library.py`
- [X] T017 [P] [US1] Add document library aggregation tests for old `data/index_manifest.json` compatibility in `tests/test_document_library.py`
- [X] T018 [P] [US1] Add document library aggregation tests for parse_report and index_status merge precedence in `tests/test_document_library.py`

### Implementation for User Story 1

- [X] T019 [US1] Implement local PDF/SI directory scanning and stable document item creation in `app/document_library.py`
- [X] T020 [US1] Implement manifest loading and old-format compatibility merge in `app/document_library.py`
- [X] T021 [US1] Implement parse_report and index_status merge logic for list rows in `app/document_library.py`
- [X] T022 [US1] Implement missing metadata fallback values and error summary derivation in `app/document_library.py`
- [X] T023 [US1] Add `document_id` metadata propagation to chunk generation inputs without changing existing chunk output compatibility in `app/chunker.py`
- [X] T024 [US1] Add `document_id` and path-aware manifest fields while preserving old manifest reads in `app/indexer.py`
- [X] T025 [US1] Add a `文献库管理` Streamlit entry point that renders the aggregated list in `ui/streamlit_app.py`
- [X] T026 [US1] Add list filters for parse status, index status, SI flag, filename, and DOI in `ui/streamlit_app.py`
- [X] T027 [US1] Preserve existing V1 structured extraction and V2 literature synthesis default entry behavior while adding the new UI entry in `ui/streamlit_app.py`

**Checkpoint**: US1 is independently usable as the MVP literature library list.

---

## Phase 4: User Story 2 - 查看单篇文献解析与索引详情 (Priority: P1)

**Goal**: 用户可以打开单篇文献详情，查看 parse_report、chunk 列表、chunk 页码/section/SI 来源、索引阶段和失败原因。

**Independent Test**: 选择一篇已索引文献、一篇部分解析文献和一篇失败文献，详情页能展示对应 report、chunk、状态和错误信息。

### Tests for User Story 2

- [ ] T028 [P] [US2] Add tests for parse_report detail loading and failed-report display data in `tests/test_parse_report.py`
- [ ] T029 [P] [US2] Add tests for document detail item including chunk preview and index failure fields in `tests/test_document_library.py`

### Implementation for User Story 2

- [ ] T030 [US2] Implement parse_report detail lookup by `document_id` in `app/parse_report.py`
- [ ] T031 [US2] Implement chunk preview lookup from ChromaDB and parent store metadata for one document in `app/indexer.py`
- [ ] T032 [US2] Implement document detail aggregation including parse_report, chunk previews, index_status, and errors in `app/document_library.py`
- [ ] T033 [US2] Add document selection and detail panel rendering in `ui/streamlit_app.py`
- [ ] T034 [US2] Add parse_report JSON summary and raw JSON viewer in `ui/streamlit_app.py`
- [ ] T035 [US2] Add chunk preview table with `chunk_id`, page, section, SI flag, and text preview in `ui/streamlit_app.py`
- [ ] T036 [US2] Add index stage, failure stage, failure reason, and latest operation display in `ui/streamlit_app.py`

**Checkpoint**: US2 details work independently after selecting a document from the US1 list.

---

## Phase 5: User Story 3 - 重建解析与索引 (Priority: P2)

**Goal**: 用户可以对单篇文献重新解析、对单篇文献重建索引，并可明确启动全量重建索引且看到进度和摘要。

**Independent Test**: 对一篇已有文献执行重新解析和单篇索引重建，验证只影响当前文献；执行全量重建时按文献边界更新进度并保留失败摘要。

### Tests for User Story 3

- [X] T037 [P] [US3] Add tests for single-document reparse preserving old parse_report on failure in `tests/test_parse_report.py`
- [X] T038 [P] [US3] Add tests for single-document rebuild updating only target document status in `tests/test_index_status.py`
- [X] T039 [P] [US3] Add tests for full rebuild operation summary counts in `tests/test_index_status.py`

### Implementation for User Story 3

- [X] T040 [US3] Add single-file parse wrapper that returns pages, metadata, warnings, and failed reports without changing `load_folder()` behavior in `app/ingest.py`
- [X] T041 [US3] Write parse_report after successful, partial, or failed PDF parsing in `app/ingest.py`
- [X] T042 [US3] Implement `reparse_document` operation with old-report preservation and diff summary in `app/document_library.py`
- [X] T043 [US3] Add single-document indexing helper that chunks only the target paper in `app/indexer.py`
- [X] T044 [US3] Implement single-document index rebuild using existing `chunk_paper()` and `LiteratureIndex.add_chunks()` in `app/indexer.py`
- [X] T045 [US3] Update index_status stages during single-document reparse and rebuild operations in `app/index_status.py`
- [X] T046 [US3] Implement full rebuild progress summary without changing existing index storage format in `app/indexer.py`
- [X] T047 [US3] Add reparse, rebuild current index, and full rebuild controls with user-visible progress in `ui/streamlit_app.py`
- [X] T048 [US3] Ensure single-document reparse and single-document rebuild controls are separate actions in `ui/streamlit_app.py`
- [X] T049 [US3] Ensure single-document operations never call full-library rebuild paths in `app/document_library.py`

**Checkpoint**: US3 operations are independently testable and keep single-document boundaries.

---

## Phase 6: User Story 4 - 删除文献及关联记录 (Priority: P2)

**Goal**: 用户可以删除某篇文献的关联记录，并逐项看到 manifest、parse_report、chunk、ChromaDB、BM25、parent store、index_status 清理结果。

**Independent Test**: 删除一篇已索引文献后，该文献 chunk 不再出现在检索结果；若某项清理失败，UI 显示明确失败项和原因。

### Tests for User Story 4

- [ ] T050 [P] [US4] Add tests for delete operation result shape and partial failure reporting in `tests/test_document_library.py`
- [ ] T051 [P] [US4] Add tests for index_status cleanup and delete operation summary in `tests/test_index_status.py`
- [ ] T052 [P] [US4] Add tests for manifest and parse_report cleanup behavior in `tests/test_document_library.py`

### Implementation for User Story 4

- [ ] T053 [US4] Implement parse_report delete helper that removes only `data/parse_reports/{document_id}.json` in `app/parse_report.py`
- [ ] T054 [US4] Implement manifest entry removal or invalidation by `document_id` and filename in `app/indexer.py`
- [ ] T055 [US4] Implement ChromaDB vector record deletion by `document_id` with filename fallback in `app/indexer.py`
- [ ] T056 [US4] Implement BM25 rebuild after target-document deletion in `app/indexer.py`
- [ ] T057 [US4] Implement parent store cleanup by `document_id` with filename fallback in `app/indexer.py`
- [ ] T058 [US4] Implement `delete_document_records` orchestration with per-item success, failed, or skipped results in `app/document_library.py`
- [ ] T059 [US4] Add delete confirmation, SI relationship impact notice, and per-item result table in `ui/streamlit_app.py`
- [ ] T060 [US4] Ensure delete operation does not delete original PDF files by default in `app/document_library.py`

**Checkpoint**: US4 deletion is safe, visible, and independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 补齐文档、回归、验收和安全检查。

- [ ] T061 [P] Add user-facing documentation for page usage, fields, statuses, rebuild actions, delete behavior, and known limitations in `docs/document_library.md`
- [ ] T062 Update README with a short link or section for document library management in `README.md`
- [ ] T063 Update V3 planning documentation to reflect implemented scope and exclusions in `CO2RR_RAG_Agent_PRD_V3.md`
- [ ] T064 Run parse_report, document_library, and index_status tests and record results in `CURRENT_TASK.md`
- [ ] T065 Run existing V1/V2 regression or smoke tests for structured extraction and literature synthesis entry points and record results in `CURRENT_TASK.md`
- [ ] T066 Verify no complete Debug Trace, citation verification, FastAPI, Docker, database, or V1/V2 rewrite tasks were introduced in `specs/001-library-index-transparency/tasks.md`
- [ ] T067 Verify no original PDFs, `data/chroma_db`, `data/index_manifest.json`, PRD, TDD, DEV_PLAN, or TASKS files are deleted without documented confirmation in `CURRENT_TASK.md`
- [ ] T068 Summarize changed files, tests, risks, and remaining follow-up scope in `CURRENT_TASK.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundational; MVP.
- **US2 (Phase 4)**: Depends on US1 list selection and foundational report/status modules.
- **US3 (Phase 5)**: Depends on Foundational; UI controls depend on US1/US2 page structure.
- **US4 (Phase 6)**: Depends on Foundational; UI controls depend on US1/US2 page structure.
- **Polish (Phase 7)**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Required MVP; no dependency on other user stories after Foundational.
- **US2 (P1)**: Depends on US1 list item selection but remains independently testable with fixture data.
- **US3 (P2)**: Can implement backend operations after Foundational; UI integration is easier after US2.
- **US4 (P2)**: Can implement backend deletion after Foundational; UI integration is easier after US2.

### Parallel Opportunities

- T002, T003, T004 can run in parallel.
- T014 and T015 can run in parallel after T005-T013 are specified.
- US1 tests T016-T018 can run in parallel.
- US2 tests T028-T029 can run in parallel.
- US3 tests T037-T039 can run in parallel.
- US4 tests T050-T052 can run in parallel.
- Documentation task T061 can run in parallel with README task T062 after UI behavior is stable.

---

## Parallel Example: User Story 1

```text
Task: "T016 [P] [US1] Add document library aggregation tests for empty folder, local PDF discovery, and SI detection in tests/test_document_library.py"
Task: "T017 [P] [US1] Add document library aggregation tests for old data/index_manifest.json compatibility in tests/test_document_library.py"
Task: "T018 [P] [US1] Add document library aggregation tests for parse_report and index_status merge precedence in tests/test_document_library.py"
```

## Parallel Example: User Story 3

```text
Task: "T037 [P] [US3] Add tests for single-document reparse preserving old parse_report on failure in tests/test_parse_report.py"
Task: "T038 [P] [US3] Add tests for single-document rebuild updating only target document status in tests/test_index_status.py"
Task: "T039 [P] [US3] Add tests for full rebuild operation summary counts in tests/test_index_status.py"
```

---

## Implementation Strategy

### MVP First

Implement Phase 1, Phase 2, and US1 first. This delivers the minimum useful literature library list without changing the RAG query flow.

### Incremental Delivery

1. US1: Library status list from local PDF/SI + manifest + parse_report + index_status.
2. US2: Document detail, parse_report, chunk preview, and index failure visibility.
3. US3: Reparse and rebuild operations with progress and old-state preservation.
4. US4: Delete associated records with per-item reporting.
5. Polish: Documentation, regression checks, and scope guard verification.

### Scope Boundaries

Do not add complete Debug Trace, citation verification, FastAPI, Docker, database persistence, online literature download, default PDF deletion, or V1/V2 main-flow rewrites in this feature.
