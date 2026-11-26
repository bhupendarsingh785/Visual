"""Bounded metadata harvesting from allowlisted public research/data APIs.

Search-result metadata only; not full-text harvesting or complete bulk mirrors.
"""
import urllib.parse
from knowledge_engine import add_source, ingest_source

PROVIDERS = {
    "openalex": {
        "base": "https://api.openalex.org/works",
        "license": "CC0 metadata; linked full text has separate rights",
        "topic": "research-metadata",
        "build": lambda q, n: {"search": q, "per-page": n,
            "select": "id,doi,title,publication_year,type,authorships,primary_location,open_access"},
    },
    "crossref": {
        "base": "https://api.crossref.org/works",
        "license": "CC0 bibliographic metadata; abstracts/full text may have separate rights",
        "topic": "research-metadata",
        "build": lambda q, n: {"query.bibliographic": q, "rows": n,
            "select": "DOI,title,author,published,type,URL,license,abstract"},
    },
    "zenodo": {
        "base": "https://zenodo.org/api/records/",
        "license": "Metadata CC0; files have item-level access and licenses",
        "topic": "research-datasets-metadata",
        "build": lambda q, n: {"q": q, "size": n, "sort": "mostrecent"},
    },
    "gbif": {
        "base": "https://api.gbif.org/v1/occurrence/search",
        "license": "Occurrence rights vary by record: CC0, CC BY or CC BY-NC",
        "topic": "biodiversity-occurrence-metadata",
        "build": lambda q, n: {"q": q, "limit": n},
    },
    "nasa_cmr": {
        "base": "https://cmr.earthdata.nasa.gov/search/collections.json",
        "license": "Collection metadata public; each data product has its own terms",
        "topic": "earth-observation-metadata",
        "build": lambda q, n: {"keyword": q, "page_size": n},
    },
}

def harvest_public_metadata(provider, query, limit=10, home=None):
    """Search one allowlisted API and index a bounded response in the local KB."""
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
        return {"provider": key, "status": "already_indexed",
                "source_id": queued["source_id"], "url": url}
    result = ingest_source(queued["source_id"], home)
    return {
        "provider": key, "query": query, "requested_records_max": limit,
        "status": result.get("status"), "source_id": queued["source_id"],
        "indexed_characters": result.get("characters", 0),
        "duplicate": result.get("duplicate", False), "url": url,
        "scope": "Search-result metadata only; not full-text or complete repository download.",
        "license_note": cfg["license"],
    }
