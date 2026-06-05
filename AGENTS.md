<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan at
`specs/002-retrieval-debug-trace/plan.md` and `.specify/memory/constitution.md`. Development MUST follow the CO2RR
RAG Agent constitution: evidence-first answers, verifiable RAG traces, P0
stability, modular backend boundaries, configuration and secret safety,
branch-driven workflow, testable acceptance, research data protection, and
documentation synchronization.
<!-- SPECKIT END -->

进入新的 Speckit Feature 后，plan.md 路径应更新为当前 Feature 对应的 plan 文件，不要删除 SPECKIT 块。

## 项目说明与开发约束

本文件用于指导 AI Agent / Codex 在本项目中进行开发、修改、测试和提交。在执行任何代码修改前，必须先阅读本文件，并遵守项目已有 Speckit 规格文档、`.specify/memory/constitution.md` 和当前任务说明。

### 1. 项目是什么

本项目是一个面向 CO2RR 文献的本地 RAG Agent，用于从本地 PDF / Supporting Information 文献库中检索证据，并基于检索到的上下文生成可追溯回答。

项目目标不是简单聊天，而是构建 evidence-first 的科研文献助手。开发时必须坚持：

```text
证据优先；
不确定就标注不确定；
不能没有证据就编造结论；
不能把 AI 推测伪装成文献事实。
```

核心能力包括：

1. 从本地 PDF / SI 文献中解析文本；
2. 对文献进行 chunk 切分；
3. 建立 BM25、ChromaDB 向量索引和 parent chunk store；
4. 根据用户问题进行本地检索；
5. 基于检索到的 context 生成回答；
6. 输出带文献证据、chunk、页码、section 或原文片段的结果；
7. 支持 CO2RR 文献中的结构化信息抽取，例如催化剂、电解液、电解池、膜、电位、FE、jCO、稳定性等；
8. 逐步增强文献库管理、索引可观察、检索可调试、证据可追溯和结果可评测能力。

### 2. 项目目录结构

```text
app/
  后端核心逻辑目录，包含 PDF 解析、chunk、索引、检索、reranker、回答生成、文献库管理等模块。

ui/
  Streamlit 前端入口目录，主要包含 streamlit_app.py，用于页面展示、用户输入、文献库管理和 RAG 查询入口。

tests/
  测试目录，包含 parse_report、document_library、index_status、retriever 等相关测试。

specs/
  Speckit 生成的功能规格、技术方案、任务清单、进度文档和契约文档。
  每个功能通常对应 specs/xxx-feature-name/。

.specify/
  Speckit 项目配置和 constitution 所在目录。
  其中 .specify/memory/constitution.md 是项目开发原则，不得随意删除或覆盖。

data/
  本地运行数据目录，用于保存本地索引、ChromaDB、BM25、parent store、parse_report、输出结果等。
  data/ 属于本地运行产物，默认不应提交到 Git。

eval/
  项目正式评测样例或评测集目录。
  如果是可复现的轻量测试样例，可以提交到 Git。

docs/
  项目文档目录，用于保存架构说明、部署说明、文献库管理说明、Demo 场景等。

scripts/
  项目脚本目录，如有批处理、评测、启动、维护脚本，可以放在这里。

config.yaml
  项目默认配置文件，可以保存非敏感默认配置。
  不得保存 API Key、个人路径或隐私信息。

.env
  本地环境变量文件，用于保存 API Key、模型配置、base_url 等敏感或本地配置。
  绝对不能提交到 Git。

requirements.txt
  Python 依赖列表。

AGENTS.md
  AI Agent / Codex 的项目开发规则说明文件。
```

如果实际目录结构发生变化，开发者或 AI Agent 应先查看当前项目文件树，再基于真实结构修改，不得凭空假设路径。

### 3. 开发前必须确认

开发任何功能前必须先确认：

1. 当前功能属于 V1、V2、V3 还是用户指定版本；
2. 当前开发基线分支是否正确；
3. 当前是否在功能分支上；
4. `git status` 是否干净；
5. 当前任务是否已有 Speckit spec / plan / tasks；
6. 当前改动是否会影响 V1 / V2 / V3 既有入口；
7. 是否存在未提交的无关改动；
8. 是否有本地数据、API Key 或缓存文件即将被提交。

开发过程中必须遵守：

1. 优先小步修改，不要一次性重写大量文件；
2. 优先复用现有模块，不要无理由重写主流程；
3. 新增功能必须尽量模块化；
4. UI、检索、索引、LLM 调用、证据校验等职责要分清；
5. 不得把临时调试代码长期留在项目中；
6. 不得把真实 API Key、真实 PDF 路径、个人本地路径写入代码；
7. 不得绕过 embedding 配置校验；
8. 不得在没有测试的情况下声称功能完成；
9. 不得把本地运行产物当成项目源码提交；
10. 如果当前任务范围过大，应先建议拆分 Feature，不要强行一次性完成。

### 4. 高风险文件和目录

以下文件或目录属于高风险位置，修改前必须谨慎：

```text
.specify/memory/constitution.md
AGENTS.md
specs/*/spec.md
specs/*/plan.md
specs/*/tasks.md
specs/*/PROGRESS.md
CURRENT_TASK.md
```

这些文件是项目原则、Agent 规则、Speckit 开发依据和进度记录。如需修改，必须说明原因，并保持与当前功能范围一致。

以下核心模块可能影响 RAG 主流程，修改时必须保留兼容性：

```text
app/ingest.py
app/chunker.py
app/indexer.py
app/retriever.py
app/reranker.py
app/context_builder.py
ui/streamlit_app.py
config.yaml
```

修改这些文件时必须注意：

1. 不破坏现有 PDF 解析流程；
2. 不破坏已有 `chunk_id`、`parent_chunk_id`、`filename`、`page` 等字段；
3. 不破坏旧 `index_manifest` 兼容；
4. 不破坏 ChromaDB、BM25、parent store 的读取逻辑；
5. 不破坏 Streamlit 中已有的文献查询、结构化抽取或文献综合入口。

### 5. 配置和敏感信息安全

不得提交或硬编码：

```text
.env
API Key
密钥
个人本地路径
Windows 用户目录
真实 PDF 私有路径
```

错误示例：

```text
OPENAI_API_KEY=sk-真实key
EMBEDDING_API_KEY=sk-真实key
/mnt/c/Users/34939/Desktop/文献/...
```

正确做法：

```text
.env.example 中只写占位符；
README 中说明用户自行配置；
真实 key 只放在本地 .env。
```

不要把 `.env` 内容、API Key 或密钥写入日志、提交记录或文档。

### 6. 默认不提交的本地运行数据

任何情况下都不允许提交以下内容：

```text
.env
API Key
密钥
个人本地路径
data/chroma_db/
data/chroma_db_backup_*/
data/index_backup_*/
data/*.pkl
data/*.sqlite3
data/index_manifest.json
data/index_status.json
data/parse_reports/
data/output/
data/eval/
__pycache__/
.pytest_cache/
.venv/
```

如果这些文件已经被 Git 跟踪，必须：

1. 加入 `.gitignore`；
2. 使用 `git rm --cached` 或等价方式移出 Git 跟踪；
3. 保留本地文件，不得误删用户本地数据；
4. 单独提交清理改动。

禁止把真实 API Key、真实本地文献库、真实向量库、真实索引产物提交到仓库。

### 7. 怎么运行项目

通常在 WSL Ubuntu 项目根目录运行。

进入项目：

```bash
cd /home/yang_mind/projects/Literature-rag
```

激活虚拟环境：

```bash
source .venv/bin/activate
```

启动 Streamlit：

```bash
.venv/bin/python -m streamlit run ui/streamlit_app.py
```

如果需要确认当前终端环境变量是否存在，可以执行：

```bash
echo $OPENAI_BASE_URL
echo $OPENAI_MODEL
echo $EMBEDDING_BASE_URL
echo $EMBEDDING_MODEL
```

### 8. 怎么测试项目

功能完成后必须先在功能分支测试。

推荐先运行相关测试：

```bash
.venv/bin/python -m pytest tests/test_parse_report.py
.venv/bin/python -m pytest tests/test_document_library.py
.venv/bin/python -m pytest tests/test_index_status.py
```

如果改动影响检索、索引、RAG 主流程，应运行更多测试：

```bash
.venv/bin/python -m pytest
```

Streamlit smoke test：

```bash
.venv/bin/python -m streamlit run ui/streamlit_app.py
```

如果项目依赖真实 API、真实 embedding 或真实 PDF，测试中应优先使用 mock、fixture 和临时目录，不得让单元测试强依赖真实 API Key。

手动检查至少包括：

1. 页面能正常启动；
2. 文献查询入口仍然存在；
3. 文献库管理页面能打开；
4. 新功能入口能访问；
5. 没有明显 traceback；
6. 如果涉及索引，能正常建立或读取索引；
7. 如果涉及 RAG 查询，回答仍然基于本地证据。

### 9. 代码风格要求

本项目以 Python 为主，代码风格要求如下：

1. 模块职责清晰，不要把所有逻辑堆到一个文件；
2. 函数命名要清楚表达意图；
3. 新增函数应尽量小而可测试；
4. 涉及文件读写时要处理异常；
5. 涉及 JSON 写入时应尽量使用原子写入，避免文件写坏；
6. 涉及 API 调用时要有错误处理、超时处理和用户可读提示；
7. 涉及 RAG 证据时要保留 metadata，例如 `filename`、`page`、`section`、`chunk_id`、`parent_chunk_id`；
8. 不要吞掉异常后静默失败；
9. 不要在代码中硬编码用户本地路径；
10. 不要在代码中硬编码 API Key；
11. 测试代码应使用临时目录、fixture 或 mock，不依赖真实本地文献库；
12. UI 文案优先使用中文，便于用户理解。

### 10. RAG 与证据规则

本项目是科研文献 RAG，不允许无证据生成结论。

回答或报告中必须区分：

```text
文献明确事实
AI 基于证据的分析
证据不足的不确定结论
```

开发涉及 RAG 输出时必须保证：

1. 关键事实尽量带 citation；
2. citation 能回到具体 chunk、文献、页码或 section；
3. 没有证据时应拒答或标记不确定；
4. 不得把不同文献的实验条件和性能错误拼接成一个结论；
5. 不得把 Agent 推测写成文献已经证明的事实。

### 11. 文档同步要求

如果功能改变了使用方式、运行方式、配置方式或项目结构，必须同步更新文档。

可能需要更新：

```text
README.md
docs/*.md
CURRENT_TASK.md
specs/*/PROGRESS.md
specs/*/quickstart.md
specs/*/plan.md
```

每次功能交付时，应记录：

```text
完成了什么；
如何运行；
如何测试；
测试是否通过；
是否有已知风险；
下一步建议。
```

不得出现“代码已改但文档完全不同步”的情况。

## 功能开发 Git 工作流

本项目所有新功能开发必须遵守以下 Git 工作流。该规则用于避免 AI 或开发者直接在长期分支上修改代码，保证每个功能都有独立分支、测试、提交、合并和合并后验证。

### 1. 开发基线分支选择

所有新功能必须从当前版本对应的开发基线分支创建独立功能分支，不允许直接在 `main`、`v2-dev`、`V3-DEV` 或其他长期开发分支上直接编写功能代码。

开发基线规则如下：

1. 如果开发 V2 相关功能，应从 `v2-dev` 创建功能分支；
2. 如果开发 V3 相关功能，应从 `V3-DEV` 创建功能分支；
3. 如果用户明确指定其他开发基线分支，则以用户指定分支为准；
4. 如果不确定当前功能属于哪个版本，必须先询问用户，不得自行决定。

### 2. 开发前 Git 状态检查

开始编程之前，必须先检查当前 Git 状态。从开发基线分支创建功能分支前，应先确认该基线分支已同步远程最新状态，例如通过 lazygit pull，避免从过期基线创建功能分支。

必须确认：

1. 当前分支不是 `main`；
2. 当前分支是正确的开发基线分支，或已经是正确的功能分支；
3. 开始新功能前，`git status` 必须干净；
4. 如果存在未提交改动、未跟踪文件或冲突，必须先向用户说明；
5. 不允许在存在无关改动的情况下开始新功能开发；
6. 不允许在未确认基线分支的情况下直接修改代码。

推荐检查项：

```bash
git branch --show-current
git status
```

如果用户要求优先使用 `lazygit`，则应优先通过 `lazygit` 查看当前分支和工作区状态。

### 3. 功能分支创建规则

所有新功能必须创建独立功能分支，分支命名统一使用：

```text
feature/xxx
```

示例：

```text
feature/document-library
feature/debug-trace
feature/citation-verification
feature/deployment-readiness
feature/001-library-index-transparency
```

规则：

1. 禁止直接在 `main` 上开发功能；
2. 禁止直接在 `v2-dev` 上开发功能；
3. 禁止直接在 `V3-DEV` 上开发功能；
4. 一个功能分支只做一个明确功能；
5. 不要把多个无关功能混在同一个功能分支；
6. 如果当前功能范围变大，必须先询问用户是否拆分为多个功能分支。

### 4. 功能开发规则

功能开发只能在功能分支中进行。

开发过程中必须遵守：

1. 优先复用现有模块，不得无理由重写主流程；
2. 不得破坏已有 V1 / V2 / V3 功能入口；
3. 不得引入与当前功能无关的新架构；
4. 不得把临时调试代码、API Key、本地路径或个人数据写入代码；
5. 如果发现当前功能需要扩大范围，必须先停止并向用户说明；
6. 如果涉及 Speckit，应遵循 `specify → clarify → plan → tasks → analyze → implement` 的顺序，不得跳过需求和计划阶段直接实现。

### 5. 功能完成后的测试要求

功能实现完成后，必须先在当前功能分支运行测试。

至少包括：

1. 与当前功能直接相关的 pytest；
2. 必要时运行完整 pytest；
3. 必要的 Streamlit 手动 smoke test；
4. 如果涉及 RAG、索引、文献库、检索、UI 或 LLM 调用，必须手动验证核心流程；
5. 必须确认原有 V1 / V2 / V3 入口没有被破坏；
6. 如果测试失败，不允许提交为完成状态，必须先修复或向用户说明失败原因。

推荐命令：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m streamlit run ui/streamlit_app.py
```

如果只需要运行相关测试，可以使用：

```bash
.venv/bin/python -m pytest tests/test_xxx.py
```

### 6. 功能分支提交规则

只有在功能分支测试通过后，才允许提交。

提交前必须确认：

1. 当前分支是 `feature/xxx`；
2. 测试已经运行，并记录测试结果；
3. `git status` 中没有无关改动；
4. 没有提交 `.env`、API Key、本地索引、本地输出、缓存文件；
5. 提交内容只包含当前功能相关的代码、测试、文档和 Speckit 文件；
6. 如有本地运行数据，应加入 `.gitignore` 或从 Git 跟踪中移除。

提交信息应清晰描述本次改动，例如：

```text
feat: add document library management
feat: add retrieval debug trace
fix: handle legacy chroma metadata mismatch
docs: update deployment guide
chore: ignore local data artifacts
```

如果一次功能较大，可以拆成多个 commit，但每个 commit 都应保持主题清晰。

### 7. 合并规则

功能分支测试通过并提交后，才允许合并回对应开发基线分支。

合并目标规则：

1. V2 功能合并回 `v2-dev`；
2. V3 功能合并回 `V3-DEV`；
3. 用户指定其他基线分支时，合并回用户指定分支；
4. 合并前必须保证功能分支工作区干净；
5. 合并前必须确认功能分支已经完成测试并提交。

合并方向必须是：

```text
feature/xxx → v2-dev
feature/xxx → V3-DEV
```

禁止反向合并，除非用户明确要求将基线分支的新改动同步到功能分支。

如果合并发生冲突，必须：

1. 停止自动继续；
2. 明确说明冲突文件；
3. 解决冲突后重新运行测试；
4. 测试通过后再继续后续流程。

### 8. 合并后测试要求

功能分支合并到开发基线分支后，必须再次运行测试。

合并后至少执行：

1. 相关 pytest；
2. 必要时完整 pytest；
3. Streamlit smoke test；
4. 核心页面或核心流程手动验证；
5. 如果涉及 RAG / 文献库 / 检索 / 索引 / 证据引用，必须验证对应功能在合并后仍可用。

合并后测试的目的是确认：

1. 合并没有引入冲突残留；
2. 新功能在开发基线分支上可运行；
3. 原有功能没有被破坏；
4. 配置文件、依赖和入口文件仍然一致。

如果合并后测试失败，不允许 push，必须先修复问题或回滚合并。

### 9. Push 规则

只有在合并后测试通过后，才允许 push 到远程仓库。

Push 前必须确认：

1. 当前分支是正确的开发基线分支，例如 `v2-dev` 或 `V3-DEV`；
2. 功能分支已经合并；
3. 合并后测试已通过；
4. 工作区干净；
5. 没有敏感信息、本地数据或缓存文件被提交。

Push 示例：

```bash
git push origin v2-dev
git push origin V3-DEV
```

如果用户要求保留远程功能分支，可额外 push：

```bash
git push origin feature/xxx
```

但默认最重要的是推送合并后的开发基线分支。

### 10. Git 操作方式

本项目所有 Git 操作优先使用 `lazygit` 完成，包括：

1. 查看当前分支；
2. 查看工作区状态；
3. stage 文件；
4. commit；
5. 切换分支；
6. 创建功能分支；
7. 合并分支；
8. push。

除非用户明确要求使用命令行 Git，否则不要优先使用命令行 Git 操作。

如果必须给出命令行操作，应同时说明这些命令在 `lazygit` 中对应的操作含义。

### 11. 标准交付检查清单

每个功能完成时，必须在回复或任务记录中给出交付状态。

```text
当前功能：
开发基线分支：
功能分支：
开发前 git status 是否干净：
是否从正确基线分支创建：
功能分支测试是否通过：
测试命令：
手动 smoke test 是否完成：
是否已提交功能分支：
是否已合并回开发基线分支：
合并后测试是否通过：
合并后测试命令：
是否已 push：
未提交文件是否只包含可忽略本地数据：
已知风险：
后续建议：
```

如果其中任意一项未完成，必须明确写“未完成”或“待确认”，不得声称功能已经完整交付。

### 12. 违规情况处理

如果发现以下情况，必须立即停止继续开发，并向用户说明：

1. 当前在 `main`、`v2-dev` 或 `V3-DEV` 上直接修改功能代码；
2. 开发前 `git status` 不干净；
3. `.env` 或 API Key 即将被提交；
4. `data/` 运行时数据即将被提交；
5. 功能范围超出当前 spec / tasks；
6. 测试失败但准备继续合并或 push；
7. 合并后未测试就准备 push。

必须先修复 Git 状态、测试状态或范围问题，再继续后续开发。

## 项目进程文档同步规则

每个 Speckit Feature 必须维护项目进度文档。当前 Feature 的专属进度文档应位于：

```text
specs/<feature-name>/PROGRESS.md
```

项目根目录还必须维护：

```text
CURRENT_TASK.md
```

每次完成一个需求、阶段、User Story 或 task 后，必须同步更新 `CURRENT_TASK.md` 和 `specs/<feature-name>/PROGRESS.md`。不得只改代码不更新进度文档。

更新内容至少包括：

1. 本次完成了哪些 task 编号；
2. 当前进行到 `tasks.md` 的哪个 Phase / User Story；
3. 还有哪些 task 没完成；
4. 修改了哪些文件；
5. 执行了哪些测试命令；
6. 测试是否通过；
7. 是否做了 Streamlit 手动 smoke test；
8. 是否存在风险；
9. 下一步建议；
10. 是否已经提交、合并、push。

如果只完成部分任务，不得声称整个 Feature 已完成。

### 进度文档建议结构

`specs/<feature-name>/PROGRESS.md` 建议包含：

1. Feature 基本信息；
2. 总体目标；
3. `tasks.md` 阶段进度；
4. 已完成内容；
5. 当前未完成任务；
6. 测试记录；
7. 风险与注意事项；
8. 下一步计划；
9. 强制更新规则。

### 测试记录命令格式

进度文档和交付记录中的测试命令应优先使用：

```bash
.venv/bin/python -m pytest
.venv/bin/python -m streamlit run ui/streamlit_app.py
```

如果只运行相关测试，应写成：

```bash
.venv/bin/python -m pytest tests/test_xxx.py
```

### 文档同步验收要求

功能交付时必须确认：

1. `CURRENT_TASK.md` 已更新；
2. 当前 Feature 的 `PROGRESS.md` 已更新；
3. 测试命令和结果已记录；
4. 风险、未完成项和下一步建议已记录；
5. 若已提交、合并或 push，状态必须准确记录；
6. 若未完成提交、合并或 push，必须明确写“未完成”或“待确认”。
