# Implementation Plan: 文献库管理与索引透明化

**Branch**: `001-library-index-transparency` | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-library-index-transparency/spec.md`

## Summary

本功能为 CO2RR RAG Agent V3 工程化升级第一阶段，目标是在不重写项目、不引入数据库的前提下，新增“文献库管理”独立入口，使用户能查看本地 PDF/SI、解析报告、chunk 数量、索引状态、失败原因，并执行单篇重新解析、单篇索引重建、全量索引重建和删除关联记录。

技术路线：复用现有 `app/ingest.py` PDF 解析、`app/chunker.py` 父子 chunk、`app/indexer.py` ChromaDB/BM25/parent store/index_manifest 能力；新增 `app/parse_report.py`、`app/document_library.py`、`app/index_status.py` 作为 JSON/manifest 持久化与状态聚合层；在 `ui/streamlit_app.py` 中新增独立管理页面，保留现有 V1 结构化抽取和 V2 文献综合入口、参数和输出格式。

## Technical Context

**Language/Version**: Python 3.12（当前 `.venv` 与 pytest 缓存显示项目在 Python 3.12/3.13 环境运行；实现不得依赖 3.13 专属语法）

**Primary Dependencies**: Streamlit、PyYAML、PyMuPDF (`fitz`)、ChromaDB、rank-bm25、OpenAI-compatible embeddings client、pytest

**Storage**: 本阶段仅使用项目数据目录下 JSON/manifest 文件、现有 ChromaDB 持久化目录、现有 BM25 pickle、现有 parent store pickle；不引入数据库。新增默认路径：`data/parse_reports/`、`data/index_status.json`、兼容现有 `data/index_manifest.json`。

**Testing**: pytest；新增 `tests/test_parse_report.py`、`tests/test_document_library.py`，建议新增 `tests/test_index_status.py`；保留并运行现有 V1/V2 冒烟或回归测试。

**Target Platform**: 本地运行的 Streamlit 应用，Linux/WSL 文件系统优先，路径通过 `config.yaml` 与 `.env` 配置。

**Project Type**: 单仓库 Python RAG 应用，Streamlit UI + `app/` 后端模块。

**Performance Goals**: 至少 100 篇本地 PDF/SI 的文献库列表 30 秒内可打开；单篇操作只处理目标文献；全量重建按文献边界和阶段更新进度。

**Constraints**: 不重写项目；不引入数据库；优先复用现有解析、chunk、BM25、ChromaDB、parent store 和 `index_manifest`；单篇重新解析与单篇索引重建分离；单篇操作不得触发全库重建；失败时保留旧可用记录并报告新旧差异；删除操作必须用户确认并逐项报告清理结果。

**Scale/Scope**: V3 第一阶段本地管理能力；覆盖文献库列表、详情、解析报告、chunk 预览、索引状态、单篇重解析、单篇重建索引、全量重建索引、删除与文档说明；不覆盖完整检索 Debug Trace 升级、claim-level citation verification 升级、联网下载、数据库迁移、Docker/服务化部署。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Evidence First**: PASS。该功能不生成新的科学结论；详情页展示的 chunk 文本、页码、section、SI 来源必须携带 `document_id`、`chunk_id`、filename 和 page。现有问答证据不足行为“当前文献证据不足”保持不变。
- **Verifiable RAG**: PASS。本阶段不改写完整检索 Debug Trace；新增索引透明化只展示 parsing/chunking/embedding/vector/BM25/parent store 阶段状态，必须不删除现有 query routing、hybrid retrieval、V2 synthesis trace 所需字段。
- **P0 Scope**: PASS。该功能是 V3 第一阶段 P0 工程化支撑，提升文献可管理性和索引可观察性，同时与现有 V1/V2 查询入口隔离。
- **Module Boundaries**: PASS。PDF 解析继续由 `ingest` 承担，chunk 由 `chunker` 承担，embedding/vector/BM25/parent store 由 `indexer` 承担；新增模块只负责 parse_report、index_status 和 library 聚合，不侵入 RAG 回答生成链路。
- **Configuration and Secret Safety**: PASS。新增路径从 `config.yaml` 读取并有安全默认值；不记录 API Key；embedding 配置继续走现有 `.env`/config 机制。
- **Branch Workflow**: PASS。当前分支为 `001-library-index-transparency`，任务为生成该功能技术方案与设计产物；预期文件为本 feature 目录下计划/设计文档和 `AGENTS.md` plan 指针。
- **Testable Acceptance**: PASS。计划定义 pytest 单元测试、Streamlit 手工验收、V1/V2 回归冒烟，覆盖解析报告、状态聚合、单篇操作边界、删除逐项结果。
- **Data Protection**: PASS。删除 PDF 本体不在默认操作范围内；删除索引关联记录必须用户确认并逐项报告；失败保留旧可用记录。
- **Documentation Sync**: PASS。实现阶段必须新增 `docs/document_library.md` 或更新 README，并评估 PRD_V3/TDD/DEV_PLAN/TASKS 是否需同步。
- **AI Agent Constraints**: PASS。工作限定为一个明确功能，不做全仓重构，不以假数据替代真实状态文件。

## Project Structure

### Documentation (this feature)

```text
specs/001-library-index-transparency/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── library-management.md
│   └── local-state-files.md
└── tasks.md              # 后续 /speckit-tasks 生成
```

### Source Code (repository root)

```text
app/
├── ingest.py                 # 复用 PDF 解析；解析后写 parse_report
├── chunker.py                # 复用父子 chunk 生成
├── indexer.py                # 复用/扩展 ChromaDB、BM25、parent store、manifest 操作
├── parse_report.py           # 新增：parse_report 生成、保存、读取、diff
├── document_library.py       # 新增：聚合本地 PDF/SI + manifest + parse_report + index_status
└── index_status.py           # 新增：index_status 状态流转、持久化、操作摘要

ui/
└── streamlit_app.py          # 新增独立“文献库管理”页面/标签，保留 V1/V2 查询入口

data/
├── index_manifest.json       # 兼容扩展
├── index_status.json         # 新增：每 document_id 索引阶段状态
├── parse_reports/            # 新增：每 document_id 一个 JSON
└── chroma_db/                # 现有 ChromaDB、bm25.pkl、parent_store.pkl

tests/
├── test_parse_report.py
├── test_document_library.py
└── existing V1/V2 regression tests

docs/
└── document_library.md       # 实现阶段新增；若不建 docs，则更新 README.md
```

**Structure Decision**: 采用现有单仓库 Python/Streamlit 结构，新增模块放入 `app/`，UI 接入在 `ui/streamlit_app.py`，持久化放入项目 `data/`，测试放入现有 `tests/`。不新增服务层项目、不引入数据库、不迁移现有 RAG 查询链路。

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 无 | N/A | N/A |

## Phase 0 Research

见 [research.md](./research.md)。主要决策：使用 JSON/manifest 最小持久化；parse_report 采用每文档 JSON；index_status 采用集中 JSON；单篇操作通过 `document_id`/filename 精确删除并重建目标文献记录；删除操作逐项执行并报告。

## Phase 1 Design

见 [data-model.md](./data-model.md)、[quickstart.md](./quickstart.md)、[contracts/library-management.md](./contracts/library-management.md)、[contracts/local-state-files.md](./contracts/local-state-files.md)。

### 当前架构理解

现有 `ui/streamlit_app.py` 同时负责配置、索引构建和查询入口；`app/ingest.py` 通过 PyMuPDF 提取 PDF 页面文本与 DOI，失败文件当前会被跳过；`app/chunker.py` 从 `paper["pages"]` 生成父子 chunk；`app/indexer.py` 写入 ChromaDB collection、重建 BM25 pickle、保存 parent store pickle，并维护 `data/index_manifest.json`。V1 结构化抽取通过 `extractor/generator/verifier`，V2 文献综合通过 `query_router/pipeline_v2/report_v2`，二者依赖现有 `LiteratureIndex` 检索接口。

### 新增模块设计

- `app/parse_report.py`：定义 `ParseReport` 字典结构、`build_parse_report()`、`save_parse_report()`、`load_parse_report()`、`list_parse_reports()`、`diff_parse_reports()`；失败解析也必须保存报告。
- `app/document_library.py`：扫描配置指定 PDF/SI 目录，合并 `index_manifest`、`data/parse_reports/*.json`、`data/index_status.json` 和 Chroma/BM25/parent store 可读计数，输出 UI 可直接渲染的 `DocumentLibraryItem`。
- `app/index_status.py`：定义状态枚举、阶段布尔字段、`load_index_status()`、`update_index_status()`、`mark_stage()`、`record_failure()`、`operation_summary()`；写入采用临时文件替换，避免半写入损坏。
- `app/indexer.py`：增加单文档边界方法，如 `rebuild_document_index(paper, document_id, progress_cb=None)`、`remove_document_records(document_id, filename)`；内部仍复用 `add_chunks()`、`remove_by_filename()`，并补充按 `document_id` 删除。
- `app/ingest.py`：解析单个 PDF 后写 parse_report；新增单文件解析入口，`load_folder()` 可保持兼容。
- `ui/streamlit_app.py`：新增独立“文献库管理”入口，现有“文献索引”和“文献查询”入口保留默认行为。

### 数据文件设计

- `data/parse_reports/{document_id}.json`：每篇文献一个解析报告，适合失败隔离和单篇更新。
- `data/index_status.json`：集中保存每篇文献索引阶段状态和最近一次操作摘要。
- `data/index_manifest.json`：继续兼容 filename key；新增记录可包含 `document_id`、`filepath`、`fingerprint`、`chunk_count`、`status`、`error`、`updated_at`。
- ChromaDB、`bm25.pkl`、`parent_store.pkl`：继续由 `LiteratureIndex` 管理；新增删除/重建逻辑必须先按文档删除旧索引，再写新索引，失败时可恢复旧状态记录。

### parse_report 字段设计

必填字段：`document_id`、`filename`、`filepath`、`file_fingerprint`、`paper_title`、`doi`、`year`、`journal`、`is_si`、`main_document_id`、`metadata_source`、`parse_status`、`pages_total`、`pages_parsed`、`text_length`、`chunks_created`、`tables_found`、`figure_captions_found`、`ocr_used`、`error_message`、`warnings`、`created_at`、`updated_at`。

约束：`parse_status` 仅允许 `success`、`partial`、`failed`；模型推断或启发式推断字段必须通过 `metadata_source` 标记；`document_id` 建议由规范化相对路径或内容 fingerprint 生成，保证同一文件稳定。

### index_status 状态流转

状态枚举：`not_indexed` → `parsing` → `parsed` → `chunked` → `embedding` → `indexed`，任一阶段可转入 `failed`。字段记录 `parse_completed`、`chunks_generated`、`embedding_completed`、`vector_index_written`、`keyword_index_written`、`parent_store_written`、`failure_stage`、`failure_reason`、`last_operation_id`、`updated_at`。

单篇重新解析只更新 parse_report 和该文档派生 chunk 记录状态，不自动写 embedding/vector/BM25/parent store；单篇索引重建只基于已有解析内容重建当前文献索引，不扫描或重建全库。

### Streamlit 页面设计

新增 `文献库管理` 页面/标签：

- 列表区：显示 filename、title、DOI、year、journal、SI、main document、parse_status、index_status、pages、chunks、tables、figures、OCR、last_updated、error_summary。
- 筛选区：按解析状态、索引状态、SI、失败原因、文件名/DOI 搜索。
- 详情区：选择单篇后显示基本元数据、parse_report JSON 摘要、chunk 列表、page、section、SI 来源、文本预览、index_status、错误日志。
- 操作区：单篇重新解析、单篇重建索引、删除文献、全量重建索引。危险操作用确认控件，结果显示逐项成功/失败。
- 兼容区：现有 V1 结构化抽取与 V2 文献综合入口保持原布局或放在独立查询标签中，默认模式不变。

### 删除、重新解析、重建索引的处理逻辑

- 重新解析：读取目标文件 → 保存旧 parse_report 快照 → 执行单文件 `extract_text()` → 生成新 parse_report → chunk 计数更新 → 成功时提交新报告，失败时保留旧报告并保存失败尝试摘要/diff。
- 重建索引：读取目标 parse_report/解析内容 → chunk 当前文献 → 删除当前文献旧 Chroma/BM25/parent store 记录 → 写入新向量/BM25/parent store → 更新 manifest/index_status；失败时保留旧状态记录并报告旧 chunk_count、新失败阶段、失败原因。
- 删除：确认影响范围 → 逐项尝试 manifest、parse_report、chunk 记录、ChromaDB、BM25、parent store、index_status 清理 → 不默认删除 PDF 文件本体 → 返回每项 `success/failed/skipped` 与原因。

### 错误处理策略

所有写文件操作使用原子写入；失败不会清空旧 parse_report/index_status；单篇操作必须产生 operation summary；删除按项捕获异常并继续后续清理；UI 不暴露 API Key、绝对敏感路径可按配置选择缩略显示；损坏/加密/空文本 PDF 也生成 `failed` parse_report。

### 测试方案

- `tests/test_parse_report.py`：字段默认值、状态枚举校验、保存/读取、失败报告、diff。
- `tests/test_document_library.py`：空库、只有本地 PDF、manifest 合并、parse_report 合并、index_status 合并、SI 识别、旧 manifest 兼容。
- `tests/test_index_status.py`（实现阶段建议新增）：状态流转、失败保留旧状态、operation summary。
- UI 手工验收：列表、详情、筛选、单篇操作、删除逐项报告、全量进度。
- 回归：运行现有 V1/V2 相关 pytest 或记录 `streamlit_app.py` 可启动、结构化抽取与文献综合入口仍可用的 smoke test。

### 不做范围

不引入数据库；不重写 Streamlit 为多页面框架之外的大改；不更换 ChromaDB/BM25/parent store；不实现完整检索 Debug Trace 升级；不增强 claim-level citation verification；不联网下载文献；不默认删除原始 PDF；不做 Docker/服务化部署；不改变 V1/V2 默认入口、参数和输出格式。

## Post-Design Constitution Check

- **Evidence First**: PASS。数据模型和 UI 契约要求 document/chunk/page 可追溯，并保留原有证据不足行为。
- **Verifiable RAG**: PASS。索引状态契约不替代完整 Debug Trace，且不修改现有检索接口输出。
- **P0 Scope**: PASS。设计限定为文献库与索引透明化，不扩展到后续 V3 能力。
- **Module Boundaries**: PASS。新增模块职责清晰，现有解析、chunk、索引、检索、生成链路边界不被打散。
- **Configuration and Secret Safety**: PASS。新增路径配置化，不新增 secret。
- **Branch Workflow**: PASS。当前 feature 分支和产物路径明确。
- **Testable Acceptance**: PASS。测试与 quickstart 验收步骤可判定通过/失败。
- **Data Protection**: PASS。删除逐项报告且不默认删除 PDF 本体，失败保留旧状态。
- **Documentation Sync**: PASS。quickstart 和实现文档要求已列出。
- **AI Agent Constraints**: PASS。不做无关重构或假数据替代。
