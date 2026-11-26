"""License-gated, provenance-preserving training-corpus preparation.

This stages eligible existing KB documents; it does NOT train model weights.
Only explicit permissive license labels are accepted. Unknown, NC, ND and
restricted terms are excluded by default.
"""
import hashlib
import json
import re
from pathlib import Path

ALLOWED_LICENSES = {
    "cc0", "cc0 1.0", "cc-by", "cc-by-4.0", "cc by 4.0",
    "public domain", "us government work",
}
MIN_CHARS = 300

def _license_key(value):
    return re.sub(r"[^a-z0-9. ]+", "", str(value or "").lower()).strip()

def _split_for_id(identifier):
    bucket = int(hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "test" if bucket < 5 else "validation" if bucket < 10 else "train"

def prepare_training_corpus(home=None, output_dir=None, limit=100000):
    """Export eligible KB documents to deterministic JSONL splits with provenance."""
    from knowledge_engine import _connect
    root = Path(output_dir or (Path(home or Path.home() / ".visual") / "training_staging"))
    root.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "validation": 0, "test": 0}
    skipped = {"license": 0, "short_or_empty": 0, "duplicate": 0}
    seen = set()
    paths = {name: root / (name + ".jsonl") for name in counts}
    handles = {name: path.open("w", encoding="utf-8") for name, path in paths.items()}
    try:
        with _connect(home) as db:
            rows = db.execute("""
                SELECT d.id,d.title,d.text,d.topic,d.language,d.content_hash,
                       s.url,s.domain,s.license,s.fetched_at
                FROM documents d JOIN sources s ON s.id=d.source_id
                ORDER BY d.created_at LIMIT ?
            """, (max(1, min(int(limit), 1000000)),)).fetchall()
            for row in rows:
                license_key = _license_key(row["license"])
                if license_key not in ALLOWED_LICENSES:
                    skipped["license"] += 1
                    continue
                text = re.sub(r"\s+", " ", str(row["text"] or "")).strip()
                if len(text) < MIN_CHARS:
                    skipped["short_or_empty"] += 1
                    continue
                digest = row["content_hash"] or hashlib.sha256(text.encode("utf-8")).hexdigest()
                if digest in seen:
                    skipped["duplicate"] += 1
                    continue
                seen.add(digest)
                record = {
                    "id": row["id"], "text": text, "title": row["title"],
                    "topic": row["topic"], "language": row["language"],
                    "source_url": row["url"], "source_domain": row["domain"],
                    "license": row["license"], "fetched_at": row["fetched_at"],
                    "content_sha256": digest,
                }
                split = _split_for_id(digest)
                handles[split].write(json.dumps(record, ensure_ascii=False) + "\n")
                counts[split] += 1
    finally:
        for handle in handles.values():
            handle.close()
    report = {
        "counts": counts, "skipped": skipped,
        "total_eligible": sum(counts.values()),
        "license_policy": sorted(ALLOWED_LICENSES),
        "minimum_characters": MIN_CHARS,
        "split_policy": "deterministic hash split: 90% train, 5% validation, 5% test",
        "warning": "Prepared corpus only. No tokenizer, model training, fine-tuning or weights were run.",
        "files": {k: str(v) for k, v in paths.items()},
    }
    (root / "dataset_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
