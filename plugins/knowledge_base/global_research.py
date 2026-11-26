"""One-command, bounded multi-domain public metadata collection for VISUAL.

This discovers/indexes metadata from allowlisted APIs. It does not claim to
mirror all global data or train a neural model.
"""
import time
from api_harvest import harvest_public_metadata

DOMAIN_QUERIES = {
    "medicine": ["clinical medicine systematic review", "public health epidemiology", "medical imaging open dataset"],
    "biology": ["molecular biology genomics", "proteomics biodiversity"],
    "history": ["ancient history archaeology historical archive", "manuscripts epigraphy cultural heritage"],
    "education": ["teacher education pedagogy open educational resources", "mathematics education curriculum"],
    "coding": ["software engineering programming languages", "open source software code dataset"],
    "ai": ["machine learning deep learning foundation models", "natural language processing computer vision"],
    "agents": ["AI agents tool use benchmark", "multi agent systems planning reasoning"],
    "tools": ["developer tools compilers databases operating systems", "robotics automation engineering"],
    "physics": ["physics astronomy materials science", "particle physics open data"],
    "chemistry": ["chemistry chemical materials research", "drug discovery molecular datasets"],
    "mathematics": ["pure mathematics applied mathematics statistics", "theorem proving mathematical datasets"],
    "agriculture": ["agriculture crop science soil food security", "livestock plant pathology"],
    "climate": ["climate change meteorology weather", "oceanography hydrology earth observation"],
    "space": ["astronomy astrophysics planetary science NASA", "satellite earth observation"],
    "engineering": ["civil mechanical electrical engineering", "electronics semiconductor manufacturing"],
    "energy": ["renewable energy power grids batteries", "nuclear energy energy systems"],
    "economics": ["economics finance development statistics", "labor markets trade public policy"],
    "law": ["law legal scholarship human rights legislation", "comparative law public legal information"],
    "languages": ["linguistics language documentation multilingual corpora", "Hindi language NLP speech"],
    "culture": ["music art anthropology folklore cultural heritage", "literature archives oral history"],
    "geography": ["geography geospatial maps population", "urban planning transportation infrastructure"],
    "environment": ["ecology conservation pollution environmental science", "biodiversity species occurrence"],
    "oceans": ["marine biology fisheries ocean data", "coral reefs ocean circulation"],
    "disasters": ["earthquake flood wildfire disaster risk", "emergency management resilience"],
    "security": ["cybersecurity cryptography vulnerability research", "software security threat intelligence"],
    "business": ["management entrepreneurship industry supply chains", "operations research logistics"],
    "sports": ["sports science biomechanics exercise physiology", "sports analytics open data"],
    "india": ["India public health agriculture census education", "India history languages geography"],
}

PROVIDERS = ("openalex", "crossref", "zenodo", "gbif", "nasa_cmr")

def collect_global_research(topics=None, per_request=5, max_requests=20, home=None):
    """Harvest bounded public metadata across many domains in one controlled run."""
    selected = [x.strip().lower() for x in (topics or []) if x.strip()]
    unknown = sorted(set(selected) - set(DOMAIN_QUERIES))
    if unknown:
        raise ValueError("Unknown topics: " + ", ".join(unknown) + ". Available: " + ", ".join(DOMAIN_QUERIES))
    chosen = selected or list(DOMAIN_QUERIES)
    per_request = max(1, min(int(per_request), 25))
    max_requests = max(1, min(int(max_requests), 30))
    results, errors = [], []
    attempted = 0
    for topic in chosen:
        for query in DOMAIN_QUERIES[topic]:
            for provider in PROVIDERS:
                if attempted >= max_requests:
                    stats = _summary(results, errors, attempted, chosen)
                    stats["stopped_reason"] = "per-run request safety cap reached"
                    return stats
                attempted += 1
                try:
                    item = harvest_public_metadata(provider, query, per_request, home)
                    results.append({"topic": topic, **item})
                except Exception as exc:
                    errors.append({"topic": topic, "provider": provider,
                                   "query": query, "error": str(exc)[:240]})
                time.sleep(0.4)
    return _summary(results, errors, attempted, chosen)

def _summary(results, errors, attempted, topics):
    return {
        "topics": topics,
        "requests_attempted": attempted,
        "successful_requests": len(results),
        "failed_requests": len(errors),
        "indexed_characters": sum(int(x.get("indexed_characters", 0)) for x in results),
        "results": results,
        "errors": errors,
        "scope": "Public API metadata only; no blanket full-text or bulk-dump download.",
        "next_step": "Use verified metadata manifests and item-level rights to select bulk files; then stream, checksum, deduplicate, and index them.",
    }
