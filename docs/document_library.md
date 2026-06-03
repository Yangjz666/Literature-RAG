# 文献库管理与索引透明化

`文献库管理` 是 Feature 001 新增的独立管理入口，用于查看本地 PDF / Supporting Information、解析报告、索引状态、失败原因和 chunk 预览，并执行单篇重新解析、单篇重建索引、全量重建索引和删除关联记录。

该页面不改变现有 `文献查询` 的 V1 结构化抽取和 V2 文献综合主流程。

## 进入页面

1. 启动 Streamlit：

   ```bash
   .venv/bin/python -m streamlit run ui/streamlit_app.py
   ```

2. 在侧边栏填写本地文献文件夹路径。
3. 在侧边栏 `入口` 中选择 `文献库管理`。

页面数据来自本地 PDF/SI 文件目录、`index_manifest.json`、`data/parse_reports/`、`data/index_status.json` 和现有索引文件。缺少某类状态文件时，页面会尽量显示已有信息。

## 文献库列表

列表用于快速判断每篇文献的解析和索引状态。

主要字段：

- `parse_status`：`unknown`、`success`、`partial`、`failed`。
- `index_status`：`not_indexed`、`parsing`、`parsed`、`chunked`、`embedding`、`indexed`、`failed`。
- `SI`：是否识别为 Supporting Information。
- `chunk 数量`：优先来自 index_status，其次来自 parse_report 或 manifest。
- `错误摘要`：优先显示 index_status 的失败原因，其次显示 parse_report 或 manifest 错误。

可用筛选：

- 解析状态；
- 索引状态；
- 主文献 / Supporting Information；
- 文件名或 DOI 关键词。

## 单篇文献详情

在列表下方选择一篇文献后，详情区显示：

- 基本元数据；
- parse_report 摘要；
- parse_report 原始 JSON；
- index_status 阶段；
- failure_stage；
- failure_reason；
- 最近一次 operation summary；
- chunk preview，包括 `chunk_id`、`page`、`section`、`is_si`、`text_preview`。

如果索引对象无法加载，页面仍会显示文献状态和 parse_report，但 chunk preview、单篇重建索引和全量重建索引可能受限。

## 单篇重新解析

使用方式：

1. 进入 `文献库管理`。
2. 选择目标文献。
3. 点击 `单篇重新解析`。
4. 查看页面显示的 operation summary。

行为边界：

- 只解析当前文献；
- 不触发全库重建；
- 成功时更新当前文献 parse_report 和解析状态；
- 失败时保留旧 parse_report，并记录 failure_stage / failure_reason。

## 单篇重建索引

使用方式：

1. 选择目标文献。
2. 点击 `单篇重建索引`。
3. 查看操作摘要和失败原因。

行为边界：

- 只处理当前文献；
- 复用现有 chunk、ChromaDB、BM25 和 parent store 写入逻辑；
- 不调用全量重建路径；
- 成功时更新 manifest 和 index_status；
- 失败时保留旧可用状态，并记录 failure_stage / failure_reason。

## 全量重建索引

使用方式：

1. 确认侧边栏文献文件夹路径正确。
2. 点击 `全量重建索引`。
3. 查看进度和 summary。

行为边界：

- 只有用户明确点击按钮才会触发；
- 按文献边界处理；
- operation summary 会记录成功数量、失败数量和错误信息；
- 全量重建依赖 Embedding 配置和本地 PDF 可读性。

## 删除文献关联记录

删除入口位于单篇详情页。

使用方式：

1. 选择目标文献。
2. 阅读删除区提示。
3. 在确认输入框中输入当前文件名。
4. 点击 `删除该文献关联记录`。
5. 查看逐项清理结果表。

删除范围：

- manifest；
- parse_report；
- chunks；
- ChromaDB vector records；
- BM25；
- parent store；
- index_status。

每一项都会返回：

- `success`；
- `failed`；
- `skipped`；
- `reason`。

重要保护：

- 删除关联记录默认不会删除原始 PDF 文件。
- 如果 ChromaDB、BM25 或 parent store 某项清理失败，其他项仍会继续尝试。
- 删除后，如果原始 PDF 仍在本地文献文件夹中，重新扫描列表时该 PDF 可能以未解析 / 未索引状态再次出现。
- 对主文献或 Supporting Information 执行删除前，应确认是否需要同步处理关联文件。

## 不做范围

Feature 001 不包含以下能力：

- 完整 Debug Trace；
- citation verification；
- FastAPI；
- Docker；
- 数据库迁移；
- 联网文献下载；
- 多用户系统；
- V1/V2 主流程重写。

## 已知风险和限制

- 真实索引操作依赖 Embedding API 配置，`.env` 缺失时无法完成向量写入。
- chunk preview 依赖现有 ChromaDB / parent store 可读。
- 本功能使用本地 JSON/manifest 文件和现有索引文件，不提供并发多用户写入保护。
- Streamlit 自动启动 smoke test 只能确认应用可启动，不能替代浏览器内真实点击验证。
- 建议先用小型测试文献夹验证重新解析、重建索引和删除关联记录，再用于正式文献库。
