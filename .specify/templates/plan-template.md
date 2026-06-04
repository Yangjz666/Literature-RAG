# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Answer each gate with PASS/FAIL and a short justification. FAIL requires an
entry in Complexity Tracking before implementation may proceed.

- **Evidence First**: Does the plan define how key claims will be backed by
  Citation Evidence containing source, chunk_id, page or traceable location,
  and original evidence excerpt? Does it define the "当前文献证据不足" behavior?
- **Verifiable RAG**: Does the plan preserve Debug Trace fields for original
  query, rewritten query, BM25 results, vector search results, RRF fusion
  results, reranker results, final context chunks, and citation verification?
- **P0 Scope**: Is this work within the current P0 path, or clearly isolated
  from P0 stability if it is P1/P2?
- **Module Boundaries**: Are responsibilities assigned to existing modules
  such as pdf_parser, chunker, embedding_service, document_store,
  bm25_retriever, vector_retriever, rrf_fusion, reranker, query_rewriter,
  rag_answer_service, citation_service, citation_verifier,
  debug_trace_service, and config_service?
- **Configuration and Secret Safety**: Are API keys, model settings, database
  paths, and vector-store paths managed through configuration without logging
  or committing real secrets?
- **Branch Workflow**: Is the work on a focused feature/*, fix/*, or docs/*
  branch, with task, branch, expected files, and acceptance criteria stated?
- **Testable Acceptance**: Are automated or manual acceptance checks concrete
  enough to decide pass/fail?
- **Data Protection**: Does the plan avoid deleting uploaded PDFs,
  data/chroma_db, PRD, TDD, DEV_PLAN, TASKS, and other project records unless
  backup and user confirmation are specified?
- **Documentation Sync**: Does the plan identify PRD/TDD/DEV_PLAN/TASKS/README
  updates required by scope or technical changes?
- **AI Agent Constraints**: Is the work scoped to one explicit task, with no
  broad unrelated refactor or fake-data workaround?

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
