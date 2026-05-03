import re
import uuid
from typing import Any


def _split_sentences(text: str) -> list[str]:
    """按句子边界切分，保留标点。"""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _make_child_chunks(
    sentences: list[str],
    max_size: int = 300,
    target_size: int = 150,
) -> list[str]:
    """将句子列表合并为子 chunk，每个子 chunk 不超过 max_size 字符。"""
    chunks = []
    current = ""
    for sent in sentences:
        if not current:
            current = sent
        elif len(current) + 1 + len(sent) <= max_size:
            current += " " + sent
        else:
            chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return chunks


def split_to_child_chunks(
    text: str,
    metadata: dict | None = None,
    max_chars: int = 300,
    target_chars: int = 150,
) -> list[dict]:
    """将文本切分为子 chunk 列表，每个 chunk 携带元数据。"""
    metadata = metadata or {}
    sentences = _split_sentences(text)
    raw_chunks = _make_child_chunks(sentences, max_size=max_chars, target_size=target_chars)
    result = []
    offset = 0
    for i, chunk_text in enumerate(raw_chunks):
        char_start = text.find(chunk_text, offset)
        if char_start == -1:
            char_start = offset
        char_end = char_start + len(chunk_text)
        offset = char_end
        result.append({
            "chunk_id": f"{metadata.get('filename', 'doc')}_{metadata.get('page', 0)}_c{i}",
            "text": chunk_text,
            "char_start": char_start,
            "char_end": char_end,
            **metadata,
        })
    return result


def split_with_parent_child(
    text: str,
    metadata: dict | None = None,
    child_max: int = 300,
    parent_max: int = 800,
    overlap_sentences: int = 1,
) -> dict:
    """
    返回 {"parents": [...], "children": [...]}。
    父 chunk 是段落级别，子 chunk 是句子级别。
    子 chunk 携带 parent_chunk_id 指向所属父 chunk。
    """
    metadata = metadata or {}
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

    parents = []
    children = []

    for para_idx, para in enumerate(paragraphs):
        parent_id = (
            f"{metadata.get('filename', 'doc')}"
            f"_p{metadata.get('page', 0)}"
            f"_parent_{para_idx}"
        )
        parent = {
            "chunk_id": parent_id,
            "text": para[:parent_max],
            "child_ids": [],
            **metadata,
        }

        child_chunks = split_to_child_chunks(
            para,
            metadata={**metadata, "parent_chunk_id": parent_id},
            max_chars=child_max,
        )
        for c in child_chunks:
            c["parent_chunk_id"] = parent_id
            parent["child_ids"].append(c["chunk_id"])
            children.append(c)

        parents.append(parent)

    return {"parents": parents, "children": children}


def chunk_paper(paper: dict, child_max: int = 300, parent_max: int = 800) -> dict:
    """
    将 ingest.load_folder 返回的单篇文献切分为父子 chunk。
    返回 {"parents": [...], "children": [...]}。
    """
    all_parents: list[dict] = []
    all_children: list[dict] = []

    for page_info in paper.get("pages", []):
        base_meta = {
            "filename": paper["filename"],
            "paper_name": paper["paper_name"],
            "doi": paper.get("doi"),
            "page": page_info["page"],
            "section": "",
            "is_si": paper.get("is_si", False),
        }
        result = split_with_parent_child(
            page_info["text"],
            metadata=base_meta,
            child_max=child_max,
            parent_max=parent_max,
        )
        all_parents.extend(result["parents"])
        all_children.extend(result["children"])

    return {"parents": all_parents, "children": all_children}
