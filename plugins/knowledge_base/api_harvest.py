"""Bounded metadata harvesting from allowlisted public research/data APIs.

Only public search metadata is indexed here. Dataset files and full texts require
separate item-level rights checks and the explicit bulk-download workflow.
"""
import time
import urllib.error
import urllib.parse
from knowledge_engine import add_source, ingest_source

_LAST_REQUEST = {}

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
        "delay": 1.1,  # public query pool: keep below 1 request/second
        "license": "CC0 bibliographic metadata; abstracts/full text may have separate rights",
        "topic": "research-metadata",
        "build": lambda q, n: {"query.bibliographic": q, "rows": n,
            "select": "DOI,title,author,published,type,URL,license,abstract"},
    },
    "zenodo": {
        "base": "https://zenodo.org/api/records/",
        "delay": 2.1,  # search REST API: conservative 30 requests/minute
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
    "huggingface": {
        "base": "https://huggingface.co/api/datasets",
        "license": "Dataset metadata public; each dataset card/file has its own license",
        "topic": "machine-learning-datasets-metadata",
        "build": lambda q, n: {"search": q, "limit": n},
    },
    "pubmed": {
        "base": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        "delay": 0.4,  # remain below the unauthenticated NCBI E-utilities rate
        "license": "PubMed bibliographic metadata; article full-text rights vary",
        "topic": "biomedical-literature-metadata",
        "build": lambda q, n: {"db": "pubmed", "term": q, "retmax": n, "retmode": "json"},
    },
    "stackoverflow": {
        "base": "https://api.stackexchange.com/2.3/search/advanced",
        "license": "Stack Exchange content is CC BY-SA; preserve attribution and applicable version",
        "topic": "programming-qa-metadata",
        "build": lambda q, n: {"site": "stackoverflow", "q": q, "pagesize": n,
            "order": "desc", "sort": "relevance", "filter": "default"},
    },
    "arxiv": {
        "base": "https://export.arxiv.org/api/query",
        "license": "arXiv metadata CC0; paper files have per-paper licenses",
        "topic": "scientific-preprint-metadata",
        "delay": 3.0,
        "build": lambda q, n: {"search_query": "all:" + q, "start": 0, "max_results": n},
    },
    "europe_pmc": {
        "base": "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        "license": "Publication metadata public; full text and article reuse rights vary by record",
        "topic": "biomedical-publication-metadata",
        "delay": 0.5,
        "build": lambda q, n: {"query": q, "format": "json", "pageSize": n, "resultType": "lite"},
    },
    "wikidata": {
        "base": "https://www.wikidata.org/w/api.php",
        "license": "Wikidata structured data CC0; follow API usage policy",
        "topic": "structured-knowledge-graph-metadata",
        "delay": 1.0,
        "build": lambda q, n: {"action": "wbsearchentities", "search": q, "language": "en", "format": "json", "limit": n},
    },
}

def harvest_public_metadata(provider, query, limit=10, home=None, topic=None):
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
    queued = add_source(url, cfg["license"], str(topic or cfg["topic"]), home)
    if queued["status"] == "indexed":
        return {"provider": key, "status": "already_indexed",
                "source_id": queued["source_id"], "url": url}
    # Respect conservative per-provider pacing.
    delay = float(cfg.get("delay", 0.25))
    now = time.monotonic()
    last = _LAST_REQUEST.get(key, 0.0)
    if now - last < delay:
        time.sleep(delay - (now - last))
    _LAST_REQUEST[key] = time.monotonic()
    # These explicit API connectors follow API terms and rate limits, not website crawling.
    # General page ingestion still checks robots.txt by default.
    for attempt in range(3):
        try:
            result = ingest_source(queued["source_id"], home, respect_robots=False)
            break
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            try:
                wait = min(30.0, max(1.0, float(retry_after)))
            except (TypeError, ValueError):
                wait = 2.0 ** (attempt + 1)
            time.sleep(wait)
    return {
        "provider": key, "query": query, "requested_records_max": limit,
        "status": result.get("status"), "source_id": queued["source_id"],
        "indexed_characters": result.get("characters", 0),
        "duplicate": result.get("duplicate", False), "url": url,
        "scope": "Search-result metadata only; not full-text or complete repository download.",
        "license_note": cfg["license"],
    }
