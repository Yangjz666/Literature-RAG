# CO2RR-LocalScholar V3 PRD：面向 CO2RR 科研文献的工程化可验证 RAG 系统

## 1. 项目名称

**CO2RR-LocalScholar V3：面向 CO2RR 科研文献的工程化可验证 RAG 系统**

---

## 2. V3 版本定位

V1 解决“本地 CO2RR 文献结构化实验信息抽取”问题，重点是从 PDF 和 Supporting Information 中提取催化剂合成、测试条件、性能数据和机理解释，并为每条信息提供原文证据。

V2 解决“多篇文献综合与结论级引用校验”问题，重点是 Reranker、Citation-aware synthesis、Self-feedback、Follow-up retrieval 和 Claim-level citation verification。

V3 不推翻 V1 和 V2，而是在 V1/V2 基础上进行工程化和产品化升级。

V3 的核心定位是：

> 将 CO2RR RAG 从“能索引、能问答的 Demo”升级为“可调试、可追溯、可评估、可部署、适合简历展示和科研使用的垂直领域 RAG 应用”。

---

## 3. V3 升级目标

V3 阶段重点解决以下问题：

1. 用户不知道系统检索到了哪些文献片段；
2. 用户不知道回答中的引用是否真的支持结论；
3. 文献索引过程不够透明，无法判断 PDF 是否解析成功；
4. RAG 出错时无法定位是解析问题、检索问题、Reranker 问题还是 LLM 生成问题；
5. 缺少文献库管理页面；
6. 缺少结构化数据表和统一数据模型；
7. 缺少日志、Token、耗时和成本统计；
8. 缺少标准测试用例和验收方式；
9. 缺少部署说明；
10. 不够像一个完整 AI 应用项目。

V3 最终目标：

- 文献可管理；
- 检索可调试；
- 证据可追溯；
- 结论可校验；
- 结果可保存；
- 效果可评估；
- 系统可部署；
- 项目可展示。

---

## 4. V3 总体架构

推荐系统架构如下：

```text
本地 PDF / SI / Markdown / TXT
        ↓
文档解析层
        - PDF 文本解析
        - OCR 降级
        - SI 识别
        - 标题 / DOI / 年份 / 页码提取
        ↓
Chunk 切分与 Metadata 层
        - 父子 chunk
        - 页码
        - 章节
        - 是否 SI
        - 文献标题
        - DOI
        ↓
索引层
        - ChromaDB 向量索引
        - BM25 关键词索引
        - index_manifest.json
        ↓
检索层
        - Query Rewrite
        - BM25 检索
        - 向量检索
        - RRF 融合
        - Reranker 精排
        - 上下文预算控制
        ↓
证据层
        - Citation Evidence
        - Evidence sentence 回查
        - Claim-level citation verification
        ↓
生成层
        - 结构化抽取模式
        - 文献综合模式
        - 单篇精读模式
        - Agent 分析
        ↓
UI 层
        - Streamlit 问答页
        - 文献库管理页
        - 检索 Debug 面板
        - 历史记录页
        ↓
输出层
        - Markdown 报告
        - 查询历史
        - 日志
        - 评测结果