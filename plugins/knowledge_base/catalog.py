"""Curated public knowledge source catalog; queuing is not the same as bulk permission."""
import json
from pathlib import Path
from knowledge_engine import add_source

CATALOG = Path(__file__).with_name("sources_catalog.json")

def queue_catalog(home=None, topics=None):
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    allowed = {str(x).lower() for x in topics or []}
    added, skipped = [], []
    for item in data["sources"]:
        if allowed and not any(item["topic"].lower().startswith(x) for x in allowed):
            continue
        try:
            result = add_source(item["url"], item["license"], item["topic"], home)
            added.append({**result, "topic": item["topic"], "license": item["license"]})
        except Exception as exc:
            skipped.append({"url": item["url"], "error": str(exc)[:240]})
    return {"catalog_version": data["catalog_version"], "queued_or_existing": added, "skipped": skipped,
            "note": "Queue only. Ingest separately after checking each source's terms and robots.txt."}
