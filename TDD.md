# CO2RR RAG Agent 技术设计文档

## 1. 设计原则与边界

本项目 V1 是一个面向 CO2RR 文献的 RAG 信息提取 Agent。核心目标不是泛泛总结文献，而是从本地文献原文中提取可验证、可复查、可用于实验设计的结构化信息。

**关键原则：**

1. **云端 API 优先**：LLM 抽取、关键词扩展和最终 Markdown 生成统一优先调用云端 API。V1 不部署本地 LLM，不集成 Ollama。
2. **本地文献库与本地索引**：PDF、chunk、ChromaDB、BM25 索引和输出文件保存在本机；只有检索命中的必要原文片段发送给云端 API。
3. **证据优先**：每条关键结论必须带 `evidence_sentence`、文献名、页码或章节位置。证据校验失败的记录不得进入主表格。
4. **不自动补全缺失实验条件**：原文未明确说明的字段填 `null` 或“未明确说明”，不能用常识补齐。
5. **区分事实与推测**：文献明确事实进入主表格；Agent 推测只进入“Agent 分析”或“不确定项”。

---

## 2. 技术栈总览

| 层次 | 组件 | 选型 | 版本 |
|---|---|---|---|
| PDF 解析 | 文字型 PDF | PyMuPDF (fitz) | >=1.23 |
| PDF 解析 | 扫描版 OCR 降级 | pytesseract + Pillow | >=0.3.10 |
| 文本切分 | 父子 chunk | LlamaIndex SentenceSplitter 或自定义段落/句子切分 | >=0.10 |
| 向量嵌入 | 本地嵌入模型 | sentence-transformers/all-MiniLM-L6-v2 | >=2.6 |
| 向量数据库 | 本地持久化 | ChromaDB | >=0.5 |
| 关键词检索 | BM25 | rank_bm25 | >=0.2.2 |
| LLM | 云端 API | OpenAI SDK，默认 `gpt-4o` | >=1.35 |
| 前端界面 | Web UI | Streamlit | >=1.35 |
| 数据验证 | 结构化输出 | Pydantic v2 | >=2.0 |
| 测试框架 | 单元/集成测试 | pytest | >=8.0 |

**LLM 部署说明：**

- V1 不使用 Ollama、本地 qwen、llama.cpp 等本地推理服务。
- `OPENAI_API_KEY` 是必需配置。若未配置，应在 UI 和日志中给出明确错误提示。
- 云端 API 只接收检索命中的相关 chunk，不上传完整 PDF。

---

## 3. 项目目录结构

```text
Literature-Agent/
├── app/
│   ├── __init__.py
│   ├── ingest.py          # 文献导入 + PDF 解析 + DOI/标题提取
│   ├── chunker.py         # 章节/段落/父子 chunk 切分
│   ├── indexer.py         # ChromaDB + BM25 索引 + manifest 管理
│   ├── retriever.py       # 混合检索 (BM25 + 向量 + RRF)
│   ├── extractor.py       # 云端 LLM 结构化信息抽取
│   ├── verifier.py        # evidence_sentence 回查校验
│   ├── generator.py       # Markdown 输出生成与保存
│   └── llm_client.py      # 云端 LLM API 统一接口
├── ui/
│   └── streamlit_app.py   # Streamlit 前端
├── data/
│   ├── chroma_db/         # ChromaDB 持久化目录
│   ├── index_manifest.json
│   ├── index.log
│   └── output/            # 查询结果自动保存
├── tests/
│   ├── fixtures/
│   └── test_acceptance.py
├── requirements.txt
└── config.yaml
```

---

## 4. 文献导入模块 (`ingest.py`)

### 4.1 PDF 解析

```python
import fitz

def extract_text(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        text = page.get_text()
        used_ocr = False
        if not text.strip():
            text = ocr_page(page)
            used_ocr = True
        pages.append({
            "page": page.number + 1,
            "text": text,
            "used_ocr": used_ocr,
        })
    meta = extract_metadata(doc)
    return {"meta": meta, "pages": pages}
```

### 4.2 异常处理

| 情况 | 处理 |
|---|---|
| 加密 PDF | 跳过，记录到 `data/index.log`，UI 提示用户手动解密 |
| 空文本 PDF | 自动调用 OCR |
| OCR 失败 | 跳过该页，保留失败原因 |
| 单文件解析超过 60 秒 | 中断该文件解析，继续处理下一篇 |

### 4.3 OCR 系统依赖

`pytesseract` 只是 Python 包，系统还需要安装 Tesseract 可执行程序。Windows 环境需要在配置中指定：

```yaml
ocr:
  tesseract_cmd: "C:/Program Files/Tesseract-OCR/tesseract.exe"
```

### 4.4 SI 识别规则

1. 文件名包含 `SI`、`Supporting`、`Supplementary`、`ESI`，不区分大小写。
2. 文件位于 `si/` 子目录。
3. 文件名前缀与主文献相同且有 `_SI`、`_S` 后缀。

SI chunk 在索引中必须标记 `is_si: true`，输出时显示“来源：Supporting Information”。

### 4.5 去重规则

- 优先 DOI：从 PDF 元数据或首页文本提取，正则建议为 `10\.\d{4,9}/[-._;()/:A-Z0-9]+`，匹配时忽略大小写。
- 无 DOI：用规范化后的前 500 字符 MD5。
- 重复文件保留文件名字典序靠前的一份，并在 `index.log` 中记录被忽略文件。

---

## 5. 文本切分模块 (`chunker.py`)

### 5.1 切分原则

不能只按固定字符数粗暴切分。优先保留文献结构，尤其是 Experimental、Methods、Electrochemical Measurements、Supporting Information 中的完整实验步骤。

切分优先级：

1. 页码和章节标题；
2. 小标题，例如 `Experimental Section`、`Electrochemical Measurements`；
3. 段落；
4. 句子；
5. 字符长度兜底。

### 5.2 父子 chunk 策略

| 层级 | 粒度 | 用途 |
|---|---|---|
| 子 chunk | 1-3 句，约 100-200 字符，最长不超过 300 字符 | BM25 和向量检索定位 |
| 父 chunk | 1 个完整段落或相邻段落，约 500-1000 字符 | 送入 LLM 抽取，保留上下文 |

同一个父 chunk 可包含多个子 chunk。检索命中子 chunk 后，送入 LLM 的是对应父 chunk，同时保留命中的子 chunk 作为证据定位窗口。

### 5.3 chunk 元数据

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
    "char_start": 1200,
    "char_end": 1380,
}
```

验收要求：切分后拼接所有子 chunk 时，不能丢失 `AgNO3`、`NaBH4`、`KHCO3` 等关键术语。

---

## 6. 索引管理模块 (`indexer.py`)

### 6.1 manifest 结构

`index_manifest.json` 采用嵌套结构，真实运行和测试都应围绕该结构实现。为了兼容早期测试，可在函数入口兼容平铺 `{filename: fingerprint}`。

```json
{
  "last_updated": "2026-04-25T16:30:00",
  "files": {
    "paper_01.pdf": {
      "mtime": 1234567890,
      "size": 50000,
      "fingerprint": "1234567890_50000",
      "content_hash": "md5...",
      "chunk_count": 42,
      "status": "indexed",
      "error": null
    }
  }
}
```

### 6.2 增量更新

```python
def get_file_fingerprint(path: str) -> str:
    stat = os.stat(path)
    return f"{stat.st_mtime}_{stat.st_size}"

def get_changed_files(folder: str, manifest: dict) -> tuple[list[str], list[str]]:
    files_manifest = manifest.get("files", manifest)
    current = {
        f: get_file_fingerprint(os.path.join(folder, f))
        for f in os.listdir(folder)
        if f.lower().endswith(".pdf")
    }
    added = [
        f for f, fp in current.items()
        if f not in files_manifest
        or (isinstance(files_manifest[f], str) and files_manifest[f] != fp)
        or (isinstance(files_manifest[f], dict) and files_manifest[f].get("fingerprint") != fp)
    ]
    removed = [f for f in files_manifest if f not in current]
    return added, removed
```

### 6.3 持久化对象

- ChromaDB：保存子 chunk embedding 和元数据。
- BM25：保存 tokenized 子 chunk，或启动时从 manifest/chunk 文件重建。
- parent chunk store：保存 `parent_chunk_id -> parent text + metadata`，用于检索命中后扩展上下文。

---

## 7. 混合检索模块 (`retriever.py`)

### 7.1 检索流程

```text
用户问题
  ├─ 云端 API 关键词扩展
  ├─ BM25 检索 top_k=20 子 chunk
  ├─ 向量检索 top_k=20 子 chunk
  ├─ RRF 融合与去重
  ├─ top 子 chunk 扩展为父 chunk
  └─ 送入 extractor
```

### 7.2 RRF 缺失 rank 处理

真实检索中，一个 chunk 可能只出现在 BM25 或只出现在向量检索。RRF 对缺失 rank 不加分。

```python
def rrf_score(bm25_rank: int | None, vec_rank: int | None, k: int = 60) -> float:
    score = 0.0
    if bm25_rank is not None:
        score += 1 / (k + bm25_rank)
    if vec_rank is not None:
        score += 1 / (k + vec_rank)
    return score
```

融合后先按 `chunk_id` 去重，再按 `parent_chunk_id` 去重。多个子 chunk 命中同一个父 chunk 时，保留最高 RRF 分数，同时记录全部命中的 `child_chunk_ids`。

### 7.3 嵌入模型风险

默认 `all-MiniLM-L6-v2` 速度快，但对化学术语和长英文实验句的语义召回有限。配置中保留 `embedding_model`，后续可替换为 `BAAI/bge-small-en-v1.5`、`BAAI/bge-m3` 或 E5 系列。

---

## 8. 云端 LLM 客户端 (`llm_client.py`)

### 8.1 接口设计

```python
import os
from typing import Generator
from openai import OpenAI

class LLMClient:
    def __init__(self, config: dict):
        api_key = config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for cloud API mode.")
        self.client = OpenAI(api_key=api_key)
        self.model = config.get("openai_model", "gpt-4o")

    def chat(self, prompt: str, json_mode: bool = False) -> str:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return resp.choices[0].message.content

    def stream(self, prompt: str) -> Generator[str, None, None]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
```

### 8.2 调用规则

| 场景 | 方法 | 输出 |
|---|---|---|
| 关键词扩展 | `chat(json_mode=True)` | JSON 字符串列表 |
| 合成信息抽取 | `chat(json_mode=True)` | `SynthesisRecord[]` |
| 测试条件抽取 | `chat(json_mode=True)` | `ElectrochemicalTestRecord[]` |
| 机理信息抽取 | `chat(json_mode=True)` | `MechanismRecord[]` |
| Markdown 生成 | `stream()` | 用户可实时看到输出 |

### 8.3 云端 API 数据最小化

发送给云端 API 的 prompt 只包含：

- 用户问题；
- 检索命中的父 chunk；
- 必要元数据：文献名、页码、章节、是否 SI；
- 抽取规则。

不上传完整 PDF，不上传未命中的文献全文。

---

## 9. 信息抽取模块 (`extractor.py`)

### 9.1 通用基类

```python
from pydantic import BaseModel

class SourceRecord(BaseModel):
    paper_name: str
    filename: str | None = None
    doi: str | None = None
    page: str | None = None
    section: str | None = None
    is_si: bool = False
    evidence_sentence: str
    is_agent_inference: bool = False
```

### 9.2 合成方法 schema

```python
class SynthesisRecord(SourceRecord):
    catalyst: str
    method_type: str | None = None
    precursors: list[str] = []
    solvent: str | None = None
    temperature: str | None = None
    time: str | None = None
    post_treatment: str | None = None
```

### 9.3 CO2RR 测试条件 schema

```python
class ElectrochemicalTestRecord(SourceRecord):
    catalyst: str
    cell_type: str | None = None
    electrolyte: str | None = None
    co2_flow_rate: str | None = None
    potential_or_current: str | None = None
    product: str | None = None
    faradaic_efficiency: str | None = None
```

### 9.4 添加剂/机理 schema

```python
class MechanismRecord(SourceRecord):
    additive: str | None = None
    catalyst_system: str | None = None
    main_effect: str | None = None
    mechanism_explanation: str | None = None
```

### 9.5 Prompt 约束

```text
你是严格的 CO2RR 文献信息抽取助手。

规则：
1. evidence_sentence 必须是原文中的完整原句或连续原文片段，不能改写。
2. 原文没有明确说明的字段填 null，不允许根据常识补全。
3. 多篇文献的条件不能合并成一条记录。
4. 来自 Supporting Information 的内容必须保留 is_si=true。
5. 如果你做出推测，is_agent_inference=true，且该记录不得作为文献明确结论。
6. 只输出 JSON，不输出解释性文本。

用户问题：
{query}

候选原文片段：
{context}
```

---

## 10. 证据校验模块 (`verifier.py`)

### 10.1 校验目标

验证 `evidence_sentence` 是否确实来自对应 source chunk。校验失败时：

- `confidence = "低"`；
- `confidence_note` 包含 `⚠️ 证据未能在原文中验证`；
- 该记录只能进入“不确定项”，不能进入主表格。

### 10.2 文本规范化

真实 PDF 文本会有换行、断词、空格和单位格式差异。校验前先规范化：

```python
import re
import unicodedata

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("℃", "°C")
    return text.strip()
```

### 10.3 匹配策略

```python
import difflib

def verify_evidence(evidence: str, source_text: str, threshold: float = 0.85) -> tuple[str, str]:
    evidence_n = normalize_text(evidence)
    source_n = normalize_text(source_text)
    if not evidence_n:
        return "低", "证据为空"
    if evidence_n in source_n:
        return "高", "精确匹配"

    windows = make_sentence_windows(source_n, window_size=2)
    best = max((difflib.SequenceMatcher(None, evidence_n, w).ratio() for w in windows), default=0.0)
    if best >= threshold:
        return "中", f"模糊匹配 {best:.2f}"
    return "低", "证据未能在原文中验证"
```

`make_sentence_windows` 按句子切分 source text，用 1-2 句滑动窗口做相似度匹配，避免拿 evidence 和整段文本比较导致误判。

---

## 11. 输出生成模块 (`generator.py`)

### 11.1 输出结构

```md
# 查询结果：{query}

## 文献明确说明

| 文献名称 | 催化剂/对象 | 关键信息 | 原文证据 | 来源 | 可信度 |
|---|---|---|---|---|---|

## Agent 分析

仅包含 is_agent_inference=true 的内容。

## 不确定项

仅包含 evidence 校验失败、字段缺失严重或低可信度记录。

## 原文证据摘录
```

### 11.2 主表格过滤规则

进入主表格必须同时满足：

- `confidence in ("高", "中")`；
- `is_agent_inference is False`；
- `evidence_sentence` 非空；
- 有文献名称和页码或章节位置。

### 11.3 自动保存

输出文件名：

```text
data/output/YYYYMMDD_HHMMSS_查询关键词.md
```

查询关键词需要做文件名清理：去掉路径分隔符、控制字符和过长文本。

---

## 12. Streamlit UI (`ui/streamlit_app.py`)

### 12.1 页面能力

- 选择或输入文献文件夹路径；
- 点击“建立/更新索引”；
- 显示索引进度；
- 输入自然语言问题；
- 显示查询步骤；
- 流式展示 Markdown；
- 展示保存路径。

### 12.2 状态反馈

索引过程：

```text
正在处理文献 (12/47)：Zhang_2023_AgNPs.pdf
预计剩余时间：约 3 分钟
```

查询过程：

```text
[1/4] 检索相关段落...
[2/4] 调用云端 API 提取实验条件...
[3/4] 校验原文证据...
[4/4] 生成 Markdown 输出...
```

### 12.3 错误提示

| 情况 | UI 提示 |
|---|---|
| 未配置 API Key | “未检测到 OPENAI_API_KEY，请先配置云端 API Key。” |
| 检索结果为空 | “在当前文献库中未找到相关内容，请尝试换用其他关键词。” |
| PDF 解析失败 | “以下文件解析失败，已跳过：[文件名]。” |
| 云端 API 调用失败 | “云端 LLM 服务调用失败，请检查网络、API Key 或额度。” |
| 证据校验失败 | 输出到“不确定项”，并提示人工核查 |

---

## 13. 数据流图

```text
PDF 文件夹
    |
    v
[ingest.py] PyMuPDF 解析 / OCR 降级 / DOI 提取 / SI 标记
    |
    v
[chunker.py] 章节 + 段落 + 父子 chunk 切分
    |
    v
[indexer.py] ChromaDB 向量索引 + BM25 索引 + manifest 持久化
    |
    v
用户提问
    |
    v
[retriever.py] BM25 + 向量检索 -> RRF 融合 -> 扩展父 chunk
    |
    v
[extractor.py] 云端 API 结构化抽取 -> Pydantic 校验
    |
    v
[verifier.py] evidence_sentence 回查原文
    |
    v
[generator.py] Markdown 表格 + Agent 分析 + 不确定项
    |
    v
data/output/YYYYMMDD_HHMMSS_xxx.md
```

---

## 14. 配置文件 (`config.yaml`)

```yaml
llm_backend: openai
openai_model: gpt-4o
openai_api_key: ""          # 留空则从环境变量 OPENAI_API_KEY 读取

embedding_model: sentence-transformers/all-MiniLM-L6-v2

chroma_db_path: ./data/chroma_db
output_dir: ./data/output
index_manifest_path: ./data/index_manifest.json
index_log_path: ./data/index.log

ocr:
  enabled: true
  tesseract_cmd: ""

retrieval:
  bm25_top_k: 20
  vector_top_k: 20
  rrf_k: 60
  final_top_k: 10

chunking:
  child_chunk_size: 150
  child_chunk_max_size: 300
  parent_chunk_size: 800
  overlap_sentences: 1

evidence_verify:
  fuzzy_threshold: 0.85

performance:
  pdf_parse_timeout_sec: 60
  query_timeout_sec: 60
```

---

## 15. 依赖安装与运行

### 15.1 Python 依赖

```bash
pip install pymupdf pytesseract pillow \
            llama-index llama-index-vector-stores-chroma \
            chromadb rank-bm25 \
            sentence-transformers \
            openai \
            pydantic streamlit \
            pytest pytest-cov
```

### 15.2 系统依赖

- 安装 Tesseract OCR。
- 配置 `OPENAI_API_KEY`。

### 15.3 运行

```bash
streamlit run ui/streamlit_app.py
```

### 15.4 验证

```bash
pytest tests/test_acceptance.py -v
```

---

## 16. 性能目标（V1）

| 指标 | 目标 |
|---|---|
| 文献库规模 | <=100 篇 PDF，<=3000 页 |
| 全量索引建立 | <=10 分钟 |
| 增量索引（1 篇） | <=30 秒 |
| 单次查询响应 | <=60 秒，包含云端 API 抽取 |
| mock LLM 验证链路 | <=5 秒 |

性能目标依赖网络质量和云端 API 响应速度。若 API 超时，应保留已完成检索结果，并在 UI 中提示失败原因。

---

## 17. 验收测试映射

| 验收项 | 覆盖模块 | 设计位置 |
|---|---|---|
| AC-01 PDF 解析、OCR、SI、DOI、去重 | `ingest.py` | 第 4 节 |
| AC-02 父子 chunk、元数据、不丢关键词 | `chunker.py` | 第 5 节 |
| AC-03 证据校验、防幻觉 | `verifier.py` | 第 10 节 |
| AC-04 RRF 与关键词扩展 | `retriever.py` | 第 7 节 |
| AC-05 结构化抽取与 Pydantic schema | `extractor.py` | 第 9 节 |
| AC-06 增量索引与 manifest | `indexer.py` | 第 6 节 |
| AC-07 Markdown 输出与自动保存 | `generator.py` | 第 11 节 |
| AC-08 端到端 mock LLM 链路 | 全流程 | 第 13 节 |
| AC-09 防幻觉合规 | `extractor.py`、`verifier.py`、`generator.py` | 第 9-11 节 |

---

## 18. V1 暂不实现

- 本地 LLM 部署；
- Ollama、llama.cpp、vLLM 等本地推理服务；
- 自动联网查文献；
- 自动画图；
- 自动写论文；
- 自动分析图片中的曲线数据；
- FastAPI 服务化；
- 多 Agent 协作；
- 多轮对话和查询历史界面。
