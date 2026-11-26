"""GitHub Actions entry point for VISUAL's resumable metadata collection."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from global_research import collect_global_research
from knowledge_engine import knowledge_stats

home = Path(os.environ.get("VISUAL_HOME", Path.home() / ".visual"))
home.mkdir(parents=True, exist_ok=True)
topics = [x.strip() for x in os.environ.get("VISUAL_TOPICS", "").split(",") if x.strip()]
result = collect_global_research(
    topics=topics or None,
    per_request=int(os.environ.get("VISUAL_PER_REQUEST", "25")),
    max_requests=int(os.environ.get("VISUAL_MAX_REQUESTS", "300")),
    home=home,
    offset=int(os.environ.get("VISUAL_TASK_OFFSET", str((datetime.now(timezone.utc).timetuple().tm_yday * 400) + ((datetime.now(timezone.utc).hour // 6) * 100)))),
)
result["local_index_stats"] = knowledge_stats(home)
out = Path(os.environ.get("GITHUB_WORKSPACE", ".")) / "visual-collection-report.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "requests_attempted": result["requests_attempted"],
    "successful_requests": result["successful_requests"],
    "failed_requests": result["failed_requests"],
    "indexed_characters": result["indexed_characters"],
    "index": result["local_index_stats"],
    "report": str(out),
}, ensure_ascii=False, indent=2))
