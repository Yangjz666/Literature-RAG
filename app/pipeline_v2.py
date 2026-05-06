from __future__ import annotations

from pathlib import Path
from typing import Any

from app.claim_verifier import verify_claims
from app.context_builder import build_v2_context
from app.report_v2 import generate_markdown_v2, save_markdown_v2
from app.reranker import rerank_candidates
from app.retriever import hybrid_retrieve_candidates
from app.schemas_v2 import SynthesisResult
from app.synthesizer import synthesize_with_citations


def _output_dir(config: dict) -> str:
    value = (config or {}).get("output_dir")
    if value:
        return str(value)
    v2_value = ((config or {}).get("v2") or {}).get("output_dir")
    if v2_value:
        return str(v2_value)
    return str(Path("data") / "output")


def run_synthesis_pipeline(
    query: str,
    index: Any,
    llm_client: Any,
    config: dict | None = None,
) -> SynthesisResult:
    config = config or {}
    candidates = hybrid_retrieve_candidates(query, index, llm_client, config)
    ranked = rerank_candidates(query, candidates, config)
    context_text, citations = build_v2_context(query, ranked, config)
    result = synthesize_with_citations(query, context_text, citations, llm_client, config)
    result.claims = verify_claims(result.claims, result.citations, llm_client=None, config=config)

    markdown = generate_markdown_v2(result)
    markdown_path = save_markdown_v2(markdown, query, _output_dir(config))
    result.metadata = {
        **result.metadata,
        "markdown_path": markdown_path,
        "candidate_count": len(candidates),
        "context_citation_count": len(citations),
        "claims_verified": True,
    }
    return result
