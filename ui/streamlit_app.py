import logging
import os
import sys
from pathlib import Path

import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.chunker import chunk_paper
from app.extractor import detect_query_type, extract_mechanism_info, extract_synthesis_info, extract_test_conditions
from app.generator import generate_markdown_output, save_output
from app.document_library import list_document_library, reparse_document
from app.indexer import (
    LiteratureIndex,
    build_manifest_entry,
    get_changed_files,
    load_manifest,
    rebuild_all_documents_index,
    rebuild_document_index,
    save_manifest,
)
from app.ingest import load_folder, parse_single_pdf
from app.llm_client import LLMClient
from app.pipeline_v2 import run_synthesis_pipeline
from app.query_router import QueryMode, detect_query_mode
from app.retriever import hybrid_retrieve
from app.verifier import verify_batch

logging.basicConfig(level=logging.INFO)

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
STYLE_PATH = Path(__file__).parent / "styles.css"


@st.cache_resource
def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@st.cache_resource
def get_llm_client(config: dict) -> LLMClient | None:
    try:
        return LLMClient(config)
    except RuntimeError:
        return None


@st.cache_resource
def get_index(config: dict) -> LiteratureIndex:
    return LiteratureIndex(config)


def inject_css() -> None:
    if STYLE_PATH.exists():
        st.markdown(
            f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def get_provider_and_model(config: dict) -> tuple[str, str]:
    provider = os.environ.get("LLM_PROVIDER", config.get("llm_provider", config.get("llm_backend", "openai"))).lower()
    if provider == "anthropic":
        model = os.environ.get("ANTHROPIC_MODEL", config.get("anthropic_model", ""))
    else:
        model = os.environ.get("OPENAI_MODEL", config.get("openai_model", ""))
    return provider, model


MODE_LABELS = {
    "自动": None,
    "结构化抽取": QueryMode.STRUCTURED_EXTRACTION.value,
    "文献综合": QueryMode.SYNTHESIS.value,
    "精读解释": QueryMode.DEEP_READING.value,
}


def v2_mode_enabled(config: dict) -> bool:
    return bool((config.get("v2") or {}).get("mode_enabled", False))


def selected_query_mode(query: str, label: str, config: dict) -> QueryMode:
    return detect_query_mode(query, explicit_mode=MODE_LABELS[label], config=config)


def render_document_library_page(folder_path: str, config: dict) -> None:
    st.header("文献库管理")
    st.caption("数据来源：本地 PDF/SI 目录、index_manifest、parse_report 和 index_status。")

    rows = list_document_library(folder_path, config)
    if not rows:
        st.info("当前没有可显示的文献。请选择本地文献文件夹，或先建立索引/生成解析报告。")
        return

    col1, col2, col3, col4 = st.columns(4)
    parse_filter = col1.selectbox("解析状态", ["全部", "unknown", "success", "partial", "failed"])
    index_filter = col2.selectbox(
        "索引状态",
        ["全部", "not_indexed", "parsing", "parsed", "chunked", "embedding", "indexed", "failed"],
    )
    si_filter = col3.selectbox("SI", ["全部", "主文献", "Supporting Information"])
    keyword = col4.text_input("文件名 / DOI", value="")

    filtered = rows
    if parse_filter != "全部":
        filtered = [row for row in filtered if row.get("parse_status") == parse_filter]
    if index_filter != "全部":
        filtered = [row for row in filtered if row.get("index_status") == index_filter]
    if si_filter != "全部":
        want_si = si_filter == "Supporting Information"
        filtered = [row for row in filtered if bool(row.get("is_si")) == want_si]
    if keyword.strip():
        needle = keyword.strip().lower()
        filtered = [
            row for row in filtered
            if needle in str(row.get("filename") or "").lower()
            or needle in str(row.get("doi") or "").lower()
        ]

    st.caption(f"显示 {len(filtered)} / {len(rows)} 条文献记录")
    table_rows = [
        {
            "标题": row.get("title") or "",
            "文件名": row.get("filename") or "",
            "DOI": row.get("doi") or "",
            "SI": bool(row.get("is_si")),
            "parse_status": row.get("parse_status") or "unknown",
            "index_status": row.get("index_status") or "not_indexed",
            "chunk 数量": int(row.get("chunk_count") or 0),
            "错误摘要": row.get("error_summary") or "",
        }
        for row in filtered
    ]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("文献详情与重建操作")
    selected_filename = st.selectbox(
        "选择文献",
        [row.get("filename") or row.get("document_id") for row in filtered],
        disabled=not filtered,
    )
    selected = next(
        (row for row in filtered if (row.get("filename") or row.get("document_id")) == selected_filename),
        None,
    )
    if not selected:
        return

    detail_cols = st.columns(3)
    detail_cols[0].metric("解析状态", selected.get("parse_status") or "unknown")
    detail_cols[1].metric("索引状态", selected.get("index_status") or "not_indexed")
    detail_cols[2].metric("chunk 数量", int(selected.get("chunk_count") or 0))
    st.json(
        {
            "document_id": selected.get("document_id"),
            "filename": selected.get("filename"),
            "filepath": selected.get("filepath"),
            "doi": selected.get("doi"),
            "failure_or_error": selected.get("error_summary"),
        },
        expanded=False,
    )

    action_col1, action_col2, action_col3 = st.columns(3)
    if action_col1.button("单篇重新解析", key=f"reparse_{selected.get('document_id')}", type="secondary"):
        with st.status("正在重新解析当前文献...", expanded=True) as status_box:
            try:
                summary = reparse_document(
                    document=selected,
                    folder=folder_path,
                    config=config,
                )
            except Exception as exc:
                status_box.update(label="重新解析失败", state="error")
                st.error(str(exc))
            else:
                state = "complete" if summary.get("status") == "success" else "error"
                status_box.update(label="重新解析完成" if state == "complete" else "重新解析失败", state=state)
                st.json(summary, expanded=False)

    if action_col2.button("单篇重建当前索引", key=f"rebuild_{selected.get('document_id')}", type="secondary"):
        with st.status("正在重建当前文献索引...", expanded=True) as status_box:
            try:
                parsed = parse_single_pdf(
                    selected.get("filepath"),
                    root_dir=folder_path,
                    timeout_sec=config.get("performance", {}).get("pdf_parse_timeout_sec", 60),
                    tesseract_cmd=config.get("ocr", {}).get("tesseract_cmd", ""),
                    write_report=False,
                )
                paper = parsed.get("paper")
                if not paper:
                    raise RuntimeError(parsed.get("error") or "当前文献没有可索引文本")
                paper["document_id"] = selected.get("document_id")
                index = LiteratureIndex(config)
                summary = rebuild_document_index(paper, config, index=index)
            except Exception as exc:
                status_box.update(label="当前索引重建失败", state="error")
                st.error(str(exc))
            else:
                state = "complete" if summary.get("status") == "success" else "error"
                status_box.update(label="当前索引重建完成" if state == "complete" else "当前索引重建失败", state=state)
                st.json(summary, expanded=False)

    if action_col3.button("全量重建索引", key="full_rebuild_index", type="secondary"):
        if not folder_path or not os.path.isdir(folder_path):
            st.error("全量重建需要先选择有效的文献文件夹。")
        else:
            progress_bar = st.progress(0)
            progress_text = st.empty()

            def _progress(done: int, total: int, result: dict) -> None:
                progress_bar.progress(done / max(total, 1))
                progress_text.text(
                    f"全量重建进度：{done}/{total}，"
                    f"{result.get('filename', '')} -> {result.get('status', '')}"
                )

            with st.status("正在全量重建索引...", expanded=True) as status_box:
                try:
                    papers = load_folder(
                        folder_path,
                        timeout_sec=config.get("performance", {}).get("pdf_parse_timeout_sec", 60),
                        tesseract_cmd=config.get("ocr", {}).get("tesseract_cmd", ""),
                    )
                    for paper in papers:
                        paper.setdefault("document_id", selected.get("document_id") if paper.get("filename") == selected.get("filename") else None)
                    index = LiteratureIndex(config)
                    summary = rebuild_all_documents_index(papers, config, index=index, progress_cb=_progress)
                except Exception as exc:
                    status_box.update(label="全量重建失败", state="error")
                    st.error(str(exc))
                else:
                    status_box.update(label="全量重建完成", state="complete")
                    st.json(summary, expanded=False)


st.set_page_config(page_title="CO2RR 文献 RAG Agent", layout="wide")
inject_css()
st.title("CO2RR 文献 RAG Agent")
st.caption("从本地文献库中检索证据，并基于检索到的 context 生成可追溯回答。")

config = load_config()

with st.sidebar:
    st.header("配置")

    # 这里仅用于临时覆盖，长期配置建议写入 .env，避免把 API Key 写进代码。
    api_key_input = st.text_input(
        "LLM API Key（可选临时覆盖）",
        value="",
        type="password",
        help="建议写入 .env；这里填写后会按当前 LLM_PROVIDER 临时覆盖。",
    )
    if api_key_input:
        provider, _ = get_provider_and_model(config)
        if provider == "anthropic":
            config["anthropic_api_key"] = api_key_input
        else:
            config["openai_api_key"] = api_key_input

    folder_path = st.text_input(
        "文献文件夹路径",
        value="",
        placeholder="例如：D:/CO2RR_PDFs/AgNPs",
    )

    page = st.radio(
        "入口",
        ["文献查询", "文献库管理"],
        index=0,
        help="文献库管理只读取本地状态文件，不会触发解析、索引重建或删除。",
    )

    provider, model = get_provider_and_model(config)
    st.divider()
    st.caption(f"LLM Provider：{provider}")
    st.caption(f"模型：{model or '未配置'}")
    st.caption(f"嵌入：{config.get('embedding_model', '')}")


if page == "文献库管理":
    render_document_library_page(folder_path, config)
    st.stop()


llm = get_llm_client(config)
if llm is None:
    st.error("LLM 配置不完整：请检查 .env 中的 LLM_PROVIDER、API Key、Base URL 和模型名。")
    st.stop()

index = get_index(config)

st.header("文献索引")

col1, col2 = st.columns([3, 1])
with col1:
    st.write(f"索引路径：`{config.get('chroma_db_path', './data/chroma_db')}`")
with col2:
    force_rebuild = st.checkbox("强制重建", value=False)

if st.button("建立 / 更新索引", type="primary", disabled=not folder_path):
    if not os.path.isdir(folder_path):
        st.error(f"文件夹不存在：{folder_path}")
    else:
        manifest = load_manifest(config.get("index_manifest_path", "./data/index_manifest.json"))
        files_manifest = manifest.get("files", {})

        if force_rebuild:
            added = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
            removed = []
        else:
            added, removed = get_changed_files(folder_path, manifest)

        if not added and not removed:
            st.success("索引已经是最新，无需更新。")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 删除已经移除的文献索引。
            for fname in removed:
                status_text.text(f"从索引删除：{fname}")
                index.remove_by_filename(fname)
                files_manifest.pop(fname, None)

            papers = load_folder(
                folder_path,
                timeout_sec=config.get("performance", {}).get("pdf_parse_timeout_sec", 60),
                tesseract_cmd=config.get("ocr", {}).get("tesseract_cmd", ""),
            )
            added_papers = [p for p in papers if p["filename"] in added]

            for i, paper in enumerate(added_papers):
                fname = paper["filename"]
                status_text.text(f"正在处理文献 ({i + 1}/{len(added_papers)})：{fname}")
                progress_bar.progress((i + 1) / max(len(added_papers), 1))

                chunks = chunk_paper(
                    paper,
                    child_max=config.get("chunking", {}).get("child_chunk_max_size", 300),
                    parent_max=config.get("chunking", {}).get("parent_chunk_size", 800),
                )
                try:
                    index.add_chunks(chunks["children"], chunks["parents"])
                except RuntimeError as e:
                    st.error(str(e))
                    st.info("本次索引已停止。修复 API 额度或配置后，可以重新点击建立 / 更新索引。")
                    st.stop()

                files_manifest[fname] = build_manifest_entry(
                    folder_path,
                    fname,
                    chunk_count=len(chunks["children"]),
                    status="indexed",
                    error=None,
                )

            manifest["files"] = files_manifest
            save_manifest(config.get("index_manifest_path", "./data/index_manifest.json"), manifest)
            progress_bar.progress(1.0)
            status_text.text("索引完成。")
            st.success(f"索引完成：新增 {len(added_papers)} 篇，删除 {len(removed)} 篇，共 {index._collection.count()} 个 chunk。")


st.divider()
st.header("文献查询")

query = st.text_area(
    "输入问题",
    placeholder="例如：AgNPs 的合成方法有哪些？\n咪唑类添加剂在 CO2RR 中的作用是什么？\n对比 Ag 基催化剂的 CO2RR 测试条件。",
    height=100,
)

mode_label = "结构化抽取"
if v2_mode_enabled(config):
    mode_label = st.selectbox(
        "查询模式",
        options=list(MODE_LABELS),
        index=1,
        help="默认保持结构化抽取；自动模式会根据问题判断是否进入文献综合或精读解释。",
    )

if st.button("开始查询", type="primary", disabled=not query.strip()):
    if index._collection.count() == 0:
        st.warning("文献索引为空，请先建立索引。")
    else:
        query_mode = selected_query_mode(query, mode_label, config)
        if query_mode == QueryMode.SYNTHESIS:
            with st.status("文献综合中...", expanded=True) as status_box:
                st.write("**[1/6]** 本地检索...")
                st.write("**[2/6]** rerank...")
                st.write("**[3/6]** 构建引用上下文...")
                st.write("**[4/6]** 生成综合回答...")
                st.write("**[5/6]** claim verification...")
                st.write("**[6/6]** 生成报告...")
                try:
                    result = run_synthesis_pipeline(query, index, llm, config)
                except RuntimeError as e:
                    status_box.update(label="文献综合失败", state="error")
                    st.error(str(e))
                    st.stop()
                status_box.update(label="文献综合完成", state="complete")

            markdown_path = result.metadata.get("markdown_path")
            if markdown_path:
                st.caption(f"已保存到：`{markdown_path}`")
                try:
                    st.markdown(Path(markdown_path).read_text(encoding="utf-8"))
                except OSError:
                    st.warning("报告已生成，但无法读取保存的 Markdown 文件。")
            else:
                st.warning("文献综合完成，但未返回报告保存路径。")
            st.stop()

        if query_mode == QueryMode.DEEP_READING:
            st.info("精读解释模式尚未完整实现。本阶段仅完成模式选择与路由。")
            st.stop()

        with st.status("查询中...", expanded=True) as status_box:
            st.write("**[1/4]** 检索相关段落...")
            try:
                chunks = hybrid_retrieve(query, index, llm, config)
            except RuntimeError as e:
                status_box.update(label="查询失败", state="error")
                st.error(str(e))
                st.stop()

            if not chunks:
                status_box.update(label="查询完成", state="complete")
                st.warning("当前知识库中未检索到足够证据。")
                st.stop()

            st.write(f"**[2/4]** 调用 LLM 抽取结构化信息（命中 {len(chunks)} 个段落）...")
            query_type = detect_query_type(query)
            extractors = {
                "synthesis": extract_synthesis_info,
                "test": extract_test_conditions,
                "mechanism": extract_mechanism_info,
            }
            try:
                records = extractors[query_type](query, chunks, llm)
            except RuntimeError as e:
                status_box.update(label="查询失败", state="error")
                st.error(str(e))
                st.stop()

            st.write("**[3/4]** 校验原文证据...")
            verified = verify_batch(
                records,
                source_chunks=chunks,
                threshold=config.get("evidence_verify", {}).get("fuzzy_threshold", 0.85),
            )

            st.write("**[4/4]** 生成 Markdown 回答...")
            status_box.update(label="查询完成", state="complete")

        md_table = generate_markdown_output(verified, query=query, query_type=query_type)
        st.markdown(md_table)

        st.divider()
        st.subheader("AI 分析")
        with st.chat_message("assistant"):
            try:
                # RAG 最终回答统一走 llm.generate_answer，上层无需关心 OpenAI/Anthropic。
                full_response = llm.generate_answer(
                    system_prompt="请用中文回答，面向材料/电化学研究者，保持审慎、可追溯。",
                    user_prompt=query,
                    context_chunks=chunks,
                )
                st.markdown(full_response)
            except RuntimeError as e:
                st.error(str(e))
                full_response = ""

        full_output = md_table + "\n\n---\n\n## AI 分析\n\n" + full_response
        saved_path = save_output(
            full_output,
            query=query,
            output_dir=config.get("output_dir", "./data/output"),
        )
        st.caption(f"已保存到：`{saved_path}`")
