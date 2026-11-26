"""GitHub Actions entry point for VISUAL's resumable metadata collection."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from global_research import collect_global_research
from knowledge_engine import knowledge_stats

home = Path(os.environ.get("VISUAL_HOME", Path.home() / ".visual"))
home.mkdir(parents=True, exist_ok=True)
topics = [x.strip() for x in os.environ.get("VISUAL_TOPICS", "").split(",") if x.strip()]
before_stats = knowledge_stats(home)
result = collect_global_research(
    topics=topics or None,
    per_request=int(os.environ.get("VISUAL_PER_REQUEST", "25")),
    max_requests=int(os.environ.get("VISUAL_MAX_REQUESTS", "300")),
    home=home,
    offset=int(os.environ.get("VISUAL_TASK_OFFSET", str((datetime.now(timezone.utc).timetuple().tm_yday * 2400) + ((datetime.now(timezone.utc).hour // 6) * 300)))),
)
after_stats = knowledge_stats(home)
result["collection_delta"] = {
    "sources_added": after_stats["sources"] - before_stats["sources"],
    "indexed_sources_added": after_stats["indexed_sources"] - before_stats["indexed_sources"],
    "documents_added": after_stats["documents"] - before_stats["documents"],
    "chunks_added": after_stats["chunks"] - before_stats["chunks"],
}
result["local_index_stats"] = after_stats
db_path = home / "knowledge.sqlite3"
connection = sqlite3.connect(str(db_path), timeout=30)
try:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    connection.close()
result["database_integrity"] = integrity
if integrity != "ok":
    raise RuntimeError("SQLite integrity_check failed: " + str(integrity))
out = Path(os.environ.get("GITHUB_WORKSPACE", ".")) / "visual-collection-report.json"
temp_out = out.with_suffix(out.suffix + ".tmp")
temp_out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
os.replace(temp_out, out)
print(json.dumps({
    "requests_attempted": result["requests_attempted"],
    "successful_requests": result["successful_requests"],
    "empty_results": result.get("empty_results", 0),
    "failed_requests": result["failed_requests"],
    "indexed_characters": result["indexed_characters"],
    "collection_delta": result["collection_delta"],
    "provider_status_counts": result.get("provider_status_counts", {}),
    "database_integrity": result["database_integrity"],
    "index": result["local_index_stats"],
    "report": str(out),
}, ensure_ascii=False, indent=2))
