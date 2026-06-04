---
name: rag-project-context
description: 当用户需要总结 RAG 项目进度、生成或更新 PROJECT_CONTEXT.md、CURRENT_TASK.md、README 项目说明、开发交接文档、让新的 GPT/Codex 快速理解项目状态时使用。不要在普通代码修改任务中自动触发。
---

# RAG Project Context Skill

## 目标

你的任务是帮助用户维护一个 RAG 项目的上下文说明文件，让新的 GPT、Codex、Claude 或其他 AI 工具能够快速理解当前项目进度、技术栈、已完成功能、未完成功能、当前任务和下一步开发方向。

本 skill 优先服务于用户的 CO2RR Literature RAG Agent 项目。

输出内容优先使用中文。

---

## 触发场景

当用户提出以下需求时，使用本 skill：

- 生成 `PROJECT_CONTEXT.md`
- 更新 `PROJECT_CONTEXT.md`
- 总结当前项目进度
- 让 GPT 快速了解当前项目
- 生成项目交接文档
- 生成 `CURRENT_TASK.md`
- 总结当前开发阶段
- 梳理已经完成和未完成的功能
- 给 Codex / GPT / Claude 一个项目背景说明
- 准备下一阶段开发任务

---

## 不应该做的事

除非用户明确要求，否则不要：

- 大规模重构代码
- 修改业务逻辑
- 删除已有文件
- 改数据库结构
- 新增复杂功能
- 一次性生成过多需求
- 随意假设已经完成的功能

如果不确定某个功能是否已经完成，应标记为“待确认”，不要写成“已完成”。

---

## 工作流程

### 第一步：阅读项目文件

优先查看以下文件：

- `README.md`
- `PROJECT_CONTEXT.md`
- `CURRENT_TASK.md`
- `PRD.md`
- `TDD.md`
- `DEV_PLAN.md`
- `TASKS.md`
- `docs/`
- `app/`
- `backend/`
- `ui/`
- `streamlit_app.py`
- `requirements.txt`
- `pyproject.toml`
- `.env.example`
- `docker-compose.yml`

如果文件不存在，不要报错，继续根据已有文件总结。

---

### 第二步：判断项目当前状态

请从代码和文档中判断：

1. 项目名称是什么；
2. 项目目标是什么；
3. 当前属于 V1 / V2 / V3 哪个阶段；
4. 已经完成哪些功能；
5. 哪些功能只是写在需求里但还没实现；
6. 当前技术栈是什么；
7. 当前启动方式是什么；
8. 当前主要问题是什么；
9. 下一步最适合做什么。

注意：

- “文档里写了”不等于“代码已经实现”。
- “代码里有接口”不等于“前端已经可用”。
- “函数存在”不等于“端到端跑通”。
- 需要区分：已完成、部分完成、待开发、待确认。

---

### 第三步：生成或更新 PROJECT_CONTEXT.md

如果用户要求生成项目上下文，请创建或更新根目录下的：

`PROJECT_CONTEXT.md`

推荐结构如下：

```md
# PROJECT_CONTEXT.md

## 1. 项目名称

填写项目名称。

## 2. 项目一句话介绍

用 1～3 句话说明这个项目是干什么的。

## 3. 项目目标

说明项目最终想实现什么。

## 4. 当前开发阶段

说明项目目前处于哪个阶段，例如：

- V1：基础 RAG 问答
- V2：工程化增强
- V3：检索可调试、证据可追溯、结果可评估

## 5. 当前技术栈

列出后端、前端、数据库、向量库、Embedding、LLM、部署方式等。

## 6. 当前启动方式

写清楚如何启动项目，例如：

```bash
cd Literature-rag
source .venv/bin/activate
python -m streamlit run ui/streamlit_app.py
