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
from app.indexer import LiteratureIndex, get_changed_files, get_file_fingerprint, load_manifest, save_manifest
from app.ingest import load_folder
from app.llm_client import LLMClient
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

    provider, model = get_provider_and_model(config)
    st.divider()
    st.caption(f"LLM Provider：{provider}")
    st.caption(f"模型：{model or '未配置'}")
    st.caption(f"嵌入：{config.get('embedding_model', '')}")


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

                fp = get_file_fingerprint(os.path.join(folder_path, fname))
                files_manifest[fname] = {
                    "fingerprint": fp,
                    "chunk_count": len(chunks["children"]),
                    "status": "indexed",
                    "error": None,
                }

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

if st.button("开始查询", type="primary", disabled=not query.strip()):
    if index._collection.count() == 0:
        st.warning("文献索引为空，请先建立索引。")
    else:
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
