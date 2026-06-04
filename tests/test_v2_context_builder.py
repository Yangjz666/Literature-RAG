from app.context_builder import build_retrieval_text, build_v2_context
from app.schemas_v2 import CandidateChunk


def _chunk(**overrides) -> CandidateChunk:
    values = {
        "chunk_id": "chunk-1",
        "text": "Ag nanoparticles were synthesized by chemical reduction.",
        "paper_name": "Zhang_2023",
        "filename": "zhang_2023.pdf",
        "doi": "10.1000/example",
        "page": 3,
        "section": "Experimental",
        "is_si": False,
        "metadata": {"title": "CO2RR Ag Catalyst"},
    }
    values.update(overrides)
    return CandidateChunk(**values)


def test_empty_candidates_return_empty_context_and_citations():
    context_text, citations = build_v2_context("query", [], {})

    assert context_text == ""
    assert citations == []


def test_single_candidate_generates_s1_and_source_citation():
    context_text, citations = build_v2_context("Ag synthesis", [_chunk()], {})

    assert "[S1]" in context_text
    assert len(citations) == 1
    assert citations[0].citation_id == "S1"
    assert citations[0].source_id == "S1"
    assert citations[0].evidence_text == "Ag nanoparticles were synthesized by chemical reduction."


def test_metadata_appears_in_retrieval_text_and_context_text():
    candidate = _chunk()

    retrieval_text = build_retrieval_text(candidate)
    context_text, _ = build_v2_context("Ag synthesis", [candidate], {})

    expected_values = [
        "Title: CO2RR Ag Catalyst",
        "DOI: 10.1000/example",
        "Paper: Zhang_2023",
        "Filename: zhang_2023.pdf",
        "Section: Experimental",
        "Page: 3",
        "Supporting Information: No",
        "Text: Ag nanoparticles were synthesized by chemical reduction.",
    ]
    for value in expected_values:
        assert value in retrieval_text
        assert value in context_text


def test_duplicate_chunk_id_is_not_assigned_twice():
    chunks = [
        _chunk(chunk_id="same", text="first evidence"),
        _chunk(chunk_id="same", text="duplicate evidence"),
    ]

    context_text, citations = build_v2_context("query", chunks, {})

    assert len(citations) == 1
    assert "[S1]" in context_text
    assert "[S2]" not in context_text
    assert "duplicate evidence" not in context_text


def test_max_chunks_per_paper_is_enforced():
    chunks = [
        _chunk(chunk_id="c1", text="first", paper_name="SamePaper"),
        _chunk(chunk_id="c2", text="second", paper_name="SamePaper"),
        _chunk(chunk_id="c3", text="third", paper_name="OtherPaper"),
    ]
    config = {"context_budget": {"max_chunks_per_paper": 1}}

    context_text, citations = build_v2_context("query", chunks, config)

    assert len(citations) == 2
    assert "first" in context_text
    assert "second" not in context_text
    assert "third" in context_text


def test_max_context_tokens_skips_lower_ranked_chunks_over_budget():
    chunks = [
        _chunk(chunk_id="c1", text="a" * 16),
        _chunk(chunk_id="c2", text="b" * 16),
        _chunk(chunk_id="c3", text="c" * 4),
    ]
    config = {"context_budget": {"max_context_tokens": 5}}

    context_text, citations = build_v2_context("query", chunks, config)

    assert [citation.chunk_id for citation in citations] == ["c1", "c3"]
    assert "a" * 16 in context_text
    assert "b" * 16 not in context_text
    assert "c" * 4 in context_text


def test_is_si_true_is_rendered_as_supporting_information():
    candidate = _chunk(is_si=True)

    retrieval_text = build_retrieval_text(candidate)
    context_text, citations = build_v2_context("query", [candidate], {})

    assert "Supporting Information: Yes (SI)" in retrieval_text
    assert "Supporting Information: Yes (SI)" in context_text
    assert citations[0].is_si is True


def test_citation_id_matches_context_label():
    context_text, citations = build_v2_context(
        "query",
        [_chunk(chunk_id="c1"), _chunk(chunk_id="c2", paper_name="Other")],
        {},
    )

    for citation in citations:
        assert f"[{citation.citation_id}]" in context_text
