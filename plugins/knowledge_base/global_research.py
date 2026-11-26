"""Rotating, resumable multi-domain public metadata collection for VISUAL."""
import time
from api_harvest import harvest_public_metadata

DOMAIN_QUERIES = {
  "medicine": [
    "clinical medicine systematic review",
    "public health epidemiology",
    "medical imaging open dataset"
  ],
  "biology": [
    "molecular biology genomics",
    "proteomics biodiversity"
  ],
  "history": [
    "ancient history archaeology historical archive",
    "manuscripts epigraphy cultural heritage"
  ],
  "education": [
    "teacher education pedagogy open educational resources",
    "mathematics education curriculum"
  ],
  "coding": [
    "software engineering programming languages",
    "open source software code dataset"
  ],
  "ai": [
    "machine learning deep learning foundation models",
    "natural language processing computer vision"
  ],
  "agents": [
    "AI agents tool use benchmark",
    "multi agent systems planning reasoning"
  ],
  "tools": [
    "developer tools compilers databases operating systems",
    "robotics automation engineering"
  ],
  "physics": [
    "physics astronomy materials science",
    "particle physics open data"
  ],
  "chemistry": [
    "chemistry chemical materials research",
    "drug discovery molecular datasets"
  ],
  "mathematics": [
    "pure mathematics applied mathematics statistics",
    "theorem proving mathematical datasets"
  ],
  "agriculture": [
    "agriculture crop science soil food security",
    "livestock plant pathology"
  ],
  "climate": [
    "climate change meteorology weather",
    "oceanography hydrology earth observation"
  ],
  "space": [
    "astronomy astrophysics planetary science NASA",
    "satellite earth observation"
  ],
  "engineering": [
    "civil mechanical electrical engineering",
    "electronics semiconductor manufacturing"
  ],
  "energy": [
    "renewable energy power grids batteries",
    "nuclear energy energy systems"
  ],
  "economics": [
    "economics finance development statistics",
    "labor markets trade public policy"
  ],
  "law": [
    "law legal scholarship human rights legislation",
    "comparative law public legal information"
  ],
  "languages": [
    "linguistics language documentation multilingual corpora",
    "Hindi language NLP speech"
  ],
  "culture": [
    "music art anthropology folklore cultural heritage",
    "literature archives oral history"
  ],
  "geography": [
    "geography geospatial maps population",
    "urban planning transportation infrastructure"
  ],
  "environment": [
    "ecology conservation pollution environmental science",
    "biodiversity species occurrence"
  ],
  "oceans": [
    "marine biology fisheries ocean data",
    "coral reefs ocean circulation"
  ],
  "disasters": [
    "earthquake flood wildfire disaster risk",
    "emergency management resilience"
  ],
  "security": [
    "cybersecurity cryptography vulnerability research",
    "software security threat intelligence"
  ],
  "business": [
    "management entrepreneurship industry supply chains",
    "operations research logistics"
  ],
  "sports": [
    "sports science biomechanics exercise physiology",
    "sports analytics open data"
  ],
  "india": [
    "India public health agriculture census education",
    "India history languages geography"
  ]
}

PROVIDERS = ("openalex", "crossref", "zenodo", "gbif", "nasa_cmr")

def collect_global_research(topics=None, per_request=25, max_requests=100, home=None, offset=0):
    """Rotate through all domain/provider tasks so scheduled runs don't repeat only the first page."""
    selected = [x.strip().lower() for x in (topics or []) if x.strip()]
    unknown = sorted(set(selected) - set(DOMAIN_QUERIES))
    if unknown:
        raise ValueError("Unknown topics: " + ", ".join(unknown) + ". Available: " + ", ".join(DOMAIN_QUERIES))
    chosen = selected or list(DOMAIN_QUERIES)
    per_request = max(1, min(int(per_request), 25))
    max_requests = max(1, min(int(max_requests), 300))
    tasks = [(topic, query, provider) for topic in chosen
             for query in DOMAIN_QUERIES[topic] for provider in PROVIDERS]
    if tasks:
        start = int(offset) % len(tasks)
        tasks = tasks[start:] + tasks[:start]
    results, errors = [], []
    for topic, query, provider in tasks[:max_requests]:
        try:
            item = harvest_public_metadata(provider, query, per_request, home)
            results.append({"topic": topic, **item})
        except Exception as exc:
            errors.append({"topic": topic, "provider": provider,
                           "query": query, "error": str(exc)[:240]})
        time.sleep(0.4)
    summary = _summary(results, errors, min(len(tasks), max_requests), chosen)
    summary["task_offset"] = int(offset)
    summary["total_provider_query_tasks"] = len(tasks)
    summary["stopped_reason"] = "per-run request cap reached" if len(tasks) > max_requests else "all selected tasks processed"
    return summary

def _summary(results, errors, attempted, topics):
    return {
        "topics": topics,
        "requests_attempted": attempted,
        "successful_requests": sum(1 for x in results if x.get("status") in ("indexed", "already_indexed")),
        "failed_requests": len(errors) + sum(1 for x in results if x.get("status") not in ("indexed", "already_indexed")),
        "indexed_characters": sum(int(x.get("indexed_characters", 0)) for x in results),
        "results": results,
        "errors": errors,
        "scope": "Public API search metadata only; full-text and bulk dataset files require separate item-level rights and download workflows.",
    }
