cme from `main` after phase acceptance. Phase
acceptance MUST verify that the project starts normally, core functionality
runs end to end, basic tests pass, README or development documentation is
updated, PRD/TDD/DEV_PLAN/TASKS match actual behavior, and major risks are
recorded. Releases MUST include notes covering new features, fixes, known
risks, test status, and usage changes. Recommended milestones are `v0.1.0` for
basic RAG Q&A, `v0.2.0` for Citation Evidence and Debug Trace, `v0.3.0` for
hybrid retrieval with RRF and reranking, `v0.4.0` for claim-level citation
verification, and `v1.0.0` for the complete demonstrable MVP.

Rationale: Stable, tagged releases are necessary for research demos,
experiments, and rollback.

## P0 Scope and Architecture

P0 scope is limited to the smallest complete CO2RR literature RAG workflow:
users upload and manage PDFs, the system parses text, chunks content with
metadata, creates embeddings, stores retrievable chunks, performs basic RAG
question answering, displays Citation Evidence, exposes retrieval Debug Trace,
and refuses unsupported answers with "当前文献证据不足". P0 plans MUST explicitly
name the involved modules and data stores. P0 acceptance MUST include evidence
display and insufficient-evidence behavior for at least one realistic CO2RR
literature query.

Backend plans MUST preserve these module responsibilities:

- `pdf_parser`: PDF text parsing.
- `chunker`: text chunking and metadata generation.
- `embedding_service`: embedding generation and management.
- `document_store`: literature, chunk, and metadata storage.
- `bm25_retriever`: keyword retrieval.
- `vector_retriever`: vector retrieval.
- `rrf_fusion`: multi-route recall fusion.
- `reranker`: result reranking.
- `query_rewriter`: query rewriting.
- `rag_answer_service`: evidence-grounded answer generation.
- `citation_service`: Citation Evidence construction.
- `citation_verifier`: claim-level citation verification.
- `debug_trace_service`: retrieval trace recording and display.
- `config_service`: model, API, path, and configuration management.

## Development Workflow and Quality Gates

Before development, contributors MUST state the current task, current branch,
expected files, and acceptance criteria. If the branch is `main`, development
MUST stop until a task branch is created. Each feature or fix branch MUST pass
its acceptance criteria, run relevant tests, avoid real secret changes, avoid
important data deletion, avoid unrelated refactors, and summarize changed files,
tests, and risks before merge to `develop`.

Feature specifications MUST mark P0/P1/P2 priority and define measurable,
independent acceptance. Plans MUST include a Constitution Check covering
evidence grounding, Debug Trace, P0 scope, module boundaries, configuration and
secret safety, branch workflow, testability, data protection, documentation
synchronization, and AI coding-agent constraints. Tasks MUST include explicit
work for citation evidence, debug trace, configuration safety, tests, and
documentation whenever the feature touches those concerns.

## Governance

This constitution supersedes conflicting local conventions for CO2RR RAG Agent
development. Amendments MUST be proposed as documentation changes, explain the
reason, identify affected templates or runtime guidance, and update dependent
Spec Kit artifacts in the same change when applicable. Governance versioning
uses semantic versioning: MAJOR for incompatible principle removals or
redefinitions, MINOR for added principles or materially expanded governance, and
PATCH for wording clarifications that do not change obligations.

Compliance review is required during specification, planning, task generation,
implementation, and merge review. Any justified violation MUST be recorded in
the plan's Complexity Tracking table with the simpler alternative considered and
the removal or mitigation path. No feature, fix, or release may claim acceptance
while violating the evidence-first, secret-safety, data-protection, or branch
governance rules without explicit written approval.

## Language and Documentation

项目需求文档、规格说明、开发计划、任务拆解、验收标准和面向用户的说明文档，默认必须使用中文。代码变量名、接口路径、类名、函数名、提交信息和必要技术术语可以使用英文。

Rationale: 项目负责人以中文作为主要工作语言，中文文档有助于提高评审效率，并减少 AI 编码过程中的理解偏差。

**Version**: 1.0.0 | **Ratified**: 2026-06-01 | **Last Amended**:2026-06-01