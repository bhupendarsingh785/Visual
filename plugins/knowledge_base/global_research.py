"""Rotating, resumable multi-domain public metadata collection for VISUAL."""
import time
from api_harvest import harvest_public_metadata

DOMAIN_QUERIES = {
  "medicine": ["clinical medicine systematic review", "public health epidemiology", "medical imaging open dataset"],
  "biology": ["molecular biology genomics", "proteomics biodiversity"],
  "veterinary": ["veterinary medicine animal disease livestock health", "animal welfare veterinary epidemiology open research"],
  "animals_wildlife": ["wildlife species animal behaviour ecology open dataset", "mammals birds reptiles amphibians biodiversity occurrence"],
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
  "human_behavior": ["human behavior everyday activities social interaction behavioral science open dataset", "human action recognition walking running sitting standing hand movements gestures"],
  "speech_voice": ["multilingual speech corpus spontaneous conversation speech recognition open dataset", "prosody laughter crying emotion speech voice activity dataset"],
  "facial_expression": ["facial expression action units gaze head pose emotion recognition dataset", "face gesture non-identifying landmark movement research dataset"],
  "memory_cognition": ["human memory cognition attention learning decision making psychology dataset", "episodic memory autobiographical memory cognitive task open research data"],
  "social_science": ["sociology social networks demographics migration public survey dataset", "anthropology ethnography oral history community behavior open data"],
  "social_platforms": ["public social media trends platform governance content moderation research dataset", "public online communities discussion network misinformation research dataset"],
  "robotics_motion": ["robotics human robot interaction motion capture manipulation dataset", "human pose estimation gait locomotion biomechanics open dataset"],
  "manufacturing": ["manufacturing industrial engineering predictive maintenance machine sensor dataset", "factory process quality control CNC robotics semiconductor production research data"],
  "mechanical": ["mechanical engineering fluid dynamics thermodynamics vibration materials dataset", "machine components CAD finite element simulation engineering open data"],
  "electrical_electronics": ["electrical engineering power electronics circuits semiconductor devices dataset", "microelectronics chip fabrication testing reliability open research data"],
  "transport": ["transportation traffic pedestrian mobility public transit open data", "vehicle dynamics autonomous driving road safety dataset"],
  "construction": ["construction engineering building materials structural health monitoring dataset", "architecture infrastructure bridge civil engineering open data"],
  "geology": ["geology tectonics minerals volcanology geophysics open research", "earth history rocks soil groundwater geoscience datasets"],
  "paleontology": ["paleontology fossils prehistoric life evolution open research", "dinosaur fossil vertebrate invertebrate paleobiology collections"],
  "archaeology_technology": ["archaeological technology ancient engineering tools metallurgy", "history of inventions ancient machines materials construction"],
  "neuroscience": ["neuroscience brain behavior neural systems open datasets", "cognitive neuroscience motor control perception attention"],
  "psychology": ["psychology emotion behavior personality development open research", "clinical psychology social psychology experimental datasets"],
  "biomechanics": ["human biomechanics gait posture locomotion motion capture open data", "muscle skeletal movement ergonomics sports biomechanics"],
  "sign_language": ["sign language gestures handshape facial grammar open corpus", "gesture recognition sign language linguistics datasets"],
  "performing_arts": ["dance theatre acting facial expression body language movement", "music performance voice prosody rhythm gesture research"],
  "food_nutrition": ["food science nutrition public health food composition open data", "agri food processing fermentation food safety research"],
  "water_resources": ["hydrology water quality groundwater river basin open datasets", "water treatment desalination sanitation engineering research"],
  "quantum_technology": ["quantum computing quantum information devices open research", "quantum sensors materials communication technology"],
  "patents_inventions": ["patent inventions technology trends public patent metadata", "historical patents engineering inventions innovation research"],
  "standards": ["engineering technical standards interoperability public standards", "medical safety manufacturing quality measurement standards"],
  "open_hardware": ["open source hardware electronics robotics designs", "microcontroller embedded systems circuit schematics open projects"],
  "public_policy": ["public policy governance institutions development open data", "government services public administration regulatory research"],
  "discovery_frontier": ["recent scientific discoveries emerging technologies research frontiers", "interdisciplinary unexplored research questions open science"],
  "india": ["India public health agriculture census education", "India history languages geography"]
}

# Each provider returns bounded public search metadata, not unrestricted file mirrors.
PROVIDERS = ("openalex", "crossref", "zenodo", "gbif", "nasa_cmr",
             "huggingface", "pubmed", "stackoverflow", "arxiv")

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
