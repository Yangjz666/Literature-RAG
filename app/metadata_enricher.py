from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.schemas_v2 import ExternalMetadata


DEFAULT_CACHE_PATH = Path("data") / "external_metadata_cache.json"


def _external_metadata_config(config: dict | None) -> dict[str, Any]:
    return ((config or {}).get("external_metadata") or {}) if isinstance(config, dict) else {}


def _is_enabled(config: dict | None) -> bool:
    return bool(_external_metadata_config(config).get("enabled", False))


def _normalize_title(title: str) -> str:
    normalized = re.sub(r"\s+", " ", title.strip().lower())
    normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", "", normalized)
    return normalized


def build_cache_key(identifier: str) -> str:
    value = (identifier or "").strip()
    if not value:
        return "title:"
    lowered = value.lower()
    if lowered.startswith("doi:"):
        return f"doi:{value[4:].strip().lower()}"
    if lowered.startswith("title:"):
        return f"title:{_normalize_title(value[6:])}"
    if "/" in value and not re.search(r"\s", value):
        return f"doi:{value.lower()}"
    return f"title:{_normalize_title(value)}"


def _load_cache(config: dict | None, cache: dict[str, Any] | None) -> tuple[dict[str, Any], Path | None]:
    if cache is not None:
        return cache, None

    cache_path = Path(_external_metadata_config(config).get("cache_path") or DEFAULT_CACHE_PATH)
    if not cache_path.exists():
        return {}, cache_path
    try:
        return json.loads(cache_path.read_text(encoding="utf-8")), cache_path
    except (OSError, json.JSONDecodeError):
        return {}, cache_path


def _save_cache(cache_data: dict[str, Any], cache_path: Path | None) -> None:
    if cache_path is None:
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")


def _coerce_metadata(data: Any, note: str | None = None) -> ExternalMetadata | None:
    if data is None:
        return None
    if isinstance(data, ExternalMetadata):
        metadata = data
    elif isinstance(data, dict):
        payload = data.get("message") if isinstance(data.get("message"), dict) else data
        metadata = ExternalMetadata(
            title=payload.get("title"),
            authors=payload.get("authors") or payload.get("author") or [],
            year=payload.get("year") or payload.get("published_year"),
            venue=payload.get("venue") or payload.get("container-title"),
            abstract=payload.get("abstract"),
            citation_count=payload.get("citation_count") or payload.get("is-referenced-by-count"),
            doi=payload.get("doi") or payload.get("DOI"),
            source=payload.get("source"),
        )
    else:
        return None

    if note:
        metadata.notes.append(note)
    return metadata


def _http_get_json(http_client: Any, identifier: str, config: dict | None) -> Any:
    if hasattr(http_client, "get_metadata"):
        return http_client.get_metadata(identifier)
    if hasattr(http_client, "get"):
        endpoint = _external_metadata_config(config).get("endpoint", "")
        response = http_client.get(endpoint, params={"q": identifier}, timeout=_external_metadata_config(config).get("timeout", 10))
        if hasattr(response, "json"):
            return response.json()
        return response
    if callable(http_client):
        return http_client(identifier)
    return None


def enrich_metadata(
    identifier: str,
    config: dict | None,
    http_client: Any = None,
    cache: dict[str, Any] | None = None,
) -> ExternalMetadata | None:
    if not _is_enabled(config):
        return None

    cache_data, cache_path = _load_cache(config, cache)
    cache_key = build_cache_key(identifier)
    cached = cache_data.get(cache_key)
    if cached is not None:
        return _coerce_metadata(cached, note="external metadata cache hit")

    if http_client is None:
        return ExternalMetadata(source="external_metadata", notes=["external metadata enabled but no http_client provided"])

    try:
        raw_metadata = _http_get_json(http_client, identifier, config)
        metadata = _coerce_metadata(raw_metadata)
        if metadata is None:
            return ExternalMetadata(source="external_metadata", notes=["external metadata response was empty or invalid"])
        metadata.source = metadata.source or "external_metadata"
        cache_data[cache_key] = metadata.model_dump()
        _save_cache(cache_data, cache_path)
        return metadata
    except Exception as exc:
        return ExternalMetadata(source="external_metadata", notes=[f"external metadata failed: {exc}"])
