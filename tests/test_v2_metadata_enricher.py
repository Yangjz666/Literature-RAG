import json

import app.pipeline_v2 as pipeline_v2
from app.metadata_enricher import build_cache_key, enrich_metadata
from app.schemas_v2 import SourceCitation
from tests.test_v2_pipeline import FakeIndex, FakeLLM


class FakeHttpClient:
    def __init__(self, payload=None, exc=None):
        self.payload = payload or {}
        self.exc = exc
        self.calls = 0

    def get_metadata(self, identifier):
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.payload


def test_external_metadata_disabled_does_not_call_http_client():
    http_client = FakeHttpClient({"title": "Should not be fetched"})

    metadata = enrich_metadata("10.123/example", {"external_metadata": {"enabled": False}}, http_client=http_client)

    assert metadata is None
    assert http_client.calls == 0


def test_doi_cache_hit_returns_cache_without_network():
    http_client = FakeHttpClient({"title": "Network"})
    cache = {
        "doi:10.123/example": {
            "title": "Cached title",
            "doi": "10.123/example",
            "source": "cache",
        }
    }

    metadata = enrich_metadata("10.123/example", {"external_metadata": {"enabled": True}}, http_client=http_client, cache=cache)

    assert metadata.title == "Cached title"
    assert metadata.doi == "10.123/example"
    assert "external metadata cache hit" in metadata.notes
    assert http_client.calls == 0


def test_title_cache_key_is_normalized():
    assert build_cache_key("  Ag   Nanoparticles: CO2RR!  ") == "title:ag nanoparticles co2rr"
    assert build_cache_key("title:Ag   Nanoparticles") == "title:ag nanoparticles"


def test_enabled_true_fake_http_client_response_parses_metadata(tmp_path):
    http_client = FakeHttpClient(
        {
            "title": "Ag synthesis",
            "authors": ["A. Author", "B. Author"],
            "year": 2024,
            "venue": "Journal",
            "abstract": "External abstract for display only.",
            "citation_count": 12,
            "doi": "10.123/example",
            "source": "fake",
        }
    )

    metadata = enrich_metadata(
        "10.123/example",
        {"external_metadata": {"enabled": True, "cache_path": str(tmp_path / "metadata.json")}},
        http_client=http_client,
    )

    assert metadata.title == "Ag synthesis"
    assert metadata.authors == ["A. Author", "B. Author"]
    assert metadata.citation_count == 12
    assert http_client.calls == 1


def test_network_exception_does_not_crash():
    metadata = enrich_metadata(
        "10.123/example",
        {"external_metadata": {"enabled": True}},
        http_client=FakeHttpClient(exc=TimeoutError("timeout")),
        cache={},
    )

    assert metadata is not None
    assert metadata.notes == ["external metadata failed: timeout"]


def test_external_metadata_does_not_write_source_citation_evidence_text():
    citation = SourceCitation(citation_id="S1", evidence_text="Local PDF evidence.")
    metadata = enrich_metadata(
        "10.123/example",
        {"external_metadata": {"enabled": True}},
        http_client=FakeHttpClient({"abstract": "External abstract must not become evidence."}),
        cache={},
    )

    assert metadata.abstract == "External abstract must not become evidence."
    assert citation.evidence_text == "Local PDF evidence."


def test_pipeline_default_config_does_not_call_metadata_enricher(monkeypatch, tmp_path):
    called = {"value": False}

    def fake_enrich_metadata(*args, **kwargs):
        called["value"] = True
        raise AssertionError("metadata enricher should not be called when disabled")

    monkeypatch.setattr(pipeline_v2, "enrich_metadata", fake_enrich_metadata)
    llm = FakeLLM(json.dumps({"answer": "Answer. [S1]", "claims": []}))

    result = pipeline_v2.run_synthesis_pipeline("query", FakeIndex(), llm, {"output_dir": str(tmp_path)})

    assert called["value"] is False
    assert "external_metadata" not in result.metadata
