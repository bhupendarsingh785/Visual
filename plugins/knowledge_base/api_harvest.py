"""Bounded API metadata harvesting from selected public scholarly registries.

This is metadata collection, not full-text harvesting. Each provider's API and
reuse terms remain authoritative. Requests are bounded and indexed locally.
"""
import json
import urllib.parse

from knowledge_engine import add_source, ingest_source

PROVIDERS = {
    "openalex": {
        "base": "https://api.openalex.org/works",
        "license": "CC0 metadata; linked full text has separate rights",
        "topic": "research-metadata",
        "build": lambda q, n: {
            "search": q, "per-page": n,
            "select": "id,doi,title,publication_year,type,authorships,primary_location,open_access",
        },
    },
    "crossref": {
        "base": "https://api.crossref.org/works",
        "license": "CC0 bibliographic metadata; abstracts/full text may have separate rights",
        "topic": "research-metadata",
        "build": lambda q, n: {
            "query.bibliographic": q, "rows": n,
            "select": "DOI,title,author,published,type,URL,license,abstract",
        },
    },
    "zenodo": {
        "base": "https://zenodo.org/api/records/",
        "license": "Metadata CC0; files have item-level access and licenses",
        "topic": "research-datasets-metadata",
        "build": lambda q, n: {"q": q, "size": n, "sort": "mostrecent"},
    },
}

def harvest_public_metadata(provider, query, limit=10, home=None):
    """Search one allowlisted public metadata API and index its bounded JSON response."""
    key = str(provider).strip().lower()
    if key not in PROVIDERS:
        raise ValueError("Provider must be one of: " + ", ".join(sorted(PROVIDERS)))
    query = str(query).strip()
    if not query or len(query) > 240:
        raise ValueError("Query is required and must be at most 240 characters.")
    limit = max(1, min(int(limit), 25))
    cfg = PROVIDERS[key]
    params = urllib.parse.urlencode(cfg["build"](query, limit), doseq=True)
    url = cfg["base"] + "?" + params
    queued = add_source(url, cfg["license"], cfg["topic"], home)
    if queued["status"] == "indexed":
        return {"provider": key, "status": "already_indexed", "source_id": queued["source_id"], "url": url}
    result = ingest_source(queued["source_id"], home)
    return {
        "provider": key,
        "query": query,
        "requested_records_max": limit,
        "status": result.get("status"),
        "source_id": queued["source_id"],
        "indexed_characters": result.get("characters", 0),
        "duplicate": result.get("duplicate", False),
        "url": url,
        "scope": "Search-result metadata only; not full-text or complete repository download.",
        "license_note": cfg["license"],
    }
