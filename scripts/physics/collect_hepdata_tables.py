#!/usr/bin/env python3
"""Rate-limited, resumable HEPData CSV acquisition for VISUAL."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from hepdata_cli.api import Client

ROOT = Path(os.environ.get("VISUAL_PHYSICS_RAW_DIR", "physics-raw-data/hepdata")).resolve()
MAX_RECORDS = int(os.environ.get("VISUAL_HEPDATA_MAX_RECORDS", "20"))
MAX_BYTES = int(os.environ.get("VISUAL_HEPDATA_MAX_BYTES", str(1024 * 1024 * 1024)))
MAX_MATCHES_PER_QUERY = int(os.environ.get("VISUAL_HEPDATA_MAX_MATCHES_PER_QUERY", "100"))
QUERIES = [
    ("particle_collisions", 'collision'),
    ("standard_model", '"standard model"'),
    ("higgs_boson", 'Higgs'),
    ("top_quark", '"top quark"'),
    ("electroweak", 'electroweak'),
    ("quantum_chromodynamics", '"quantum chromodynamics"'),
    ("heavy_ions_quark_gluon_plasma", '"heavy ion"'),
    ("neutrinos", 'neutrino'),
    ("dark_matter", '"dark matter"'),
    ("supersymmetry", 'supersymmetry'),
    ("jets_and_qcd", 'jets'),
    ("beyond_standard_model", '"beyond standard model"'),
    ("precision_measurements", '"precision measurement"'),
    ("scattering_cross_sections", 'scattering'),
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def flatten_files(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from flatten_files(v)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from flatten_files(v)
    elif isinstance(value, str):
        p = Path(value)
        if p.is_file():
            yield p

def sanitize_artifact_paths(root: Path, records: list[dict]) -> None:
    """Rename downloaded paths to portable names before artifact upload.

    File contents and SHA-256 digests are unchanged. The original HEPData
    filenames remain recorded in each manifest entry for provenance.
    """
    invalid = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    used = set()
    for record in records:
        root = Path(root).resolve()
        old = Path(record["path"]).resolve()
        try:
            relative = old.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"HEPData download path escapes collection root: {old} (root: {root})"
            ) from exc
        safe_parts = []
        for part in relative.parts:
            safe = invalid.sub("_", part).rstrip(" .") or "unnamed"
            if safe.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
                safe = "_" + safe
            safe_parts.append(safe)
        target = root.joinpath(*safe_parts)
        key = str(target).casefold()
        if key in used or (target.exists() and target != old):
            target = target.with_name(f"{target.stem}_{sha256(old)[:10]}{target.suffix}")
            key = str(target).casefold()
        used.add(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target != old:
            shutil.move(str(old), str(target))
        record["original_path"] = relative.as_posix()
        record["path"] = target.relative_to(root).as_posix()
        record["sha256"] = sha256(target)

def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    client = Client(verbose=True)
    cursor_file = ROOT / "query_cursor.json"
    cursor = json.loads(cursor_file.read_text()) if cursor_file.exists() else {"next_query": 0, "pending_retry": [], "completed_ids": []}
    start = int(cursor.get("next_query", 0)) % len(QUERIES)
    selected = QUERIES[start:] + QUERIES[:start]

    # Retry records that failed in the previous run before discovering new IDs.
    completed = set(str(x) for x in cursor.get("completed_ids", []))
    pending = [(str(x.get("topic", "retry")), str(x["id"]))
               for x in cursor.get("pending_retry", []) if x.get("id")]
    found = [(topic, record_id) for topic, record_id in pending if record_id not in completed]
    query_log = []
    seen = {record_id for _, record_id in found} | completed
    for name, query in selected:
        if len(found) >= MAX_RECORDS:
            break
        try:
            ids = client.find(
                query, ids="hepdata", format=list,
                max_matches=MAX_MATCHES_PER_QUERY, matches_per_page=10
            )
            ids = [str(x) for x in (ids or [])]
            fresh = [x for x in ids if x and x not in seen]
            seen.update(fresh)
            found.extend((name, x) for x in fresh)
            query_log.append({"topic": name, "query": query, "ids_found": len(ids), "new_ids": len(fresh), "status": "ok"})
        except Exception as exc:
            query_log.append({"topic": name, "query": query, "status": "error", "error": str(exc)[:500]})
        if len(found) >= MAX_RECORDS:
            break
        time.sleep(2.0)

    found = found[:MAX_RECORDS]
    requested_ids = [record_id for _, record_id in found]
    errors = []
    files = []
    total_bytes = 0
    downloaded_ids = []
    failed_ids = []

    # Download records individually so one HTTP 429 does not discard all
    # successful records. Backoff is deliberately conservative.
    for topic, record_id in found:
        success = False
        for attempt in range(3):
            try:
                result = client.download(
                    [record_id], ids="hepdata", file_format="csv",
                    download_dir=str(ROOT / "tables")
                ) or {}
                paths = list(flatten_files(result))
                if not paths:
                    raise RuntimeError("HEPData returned no local table files")
                record_files = []
                record_bytes = 0
                for path in sorted(set(paths)):
                    size = path.stat().st_size
                    record_bytes += size
                    record_files.append({
                        "path": str(path), "bytes": size, "sha256": sha256(path),
                        "format": path.suffix.lstrip("."), "hepdata_record_id": record_id,
                        "topic": topic
                    })
                if total_bytes + record_bytes > MAX_BYTES:
                    for item in record_files:
                        Path(item["path"]).unlink(missing_ok=True)
                    errors.append({"stage": "budget", "record_id": record_id, "error": "Per-run byte budget reached"})
                    success = True
                    break
                files.extend(record_files)
                total_bytes += record_bytes
                downloaded_ids.append(record_id)
                success = True
                break
            except Exception as exc:
                message = str(exc)
                if attempt == 2:
                    errors.append({"stage": "download", "record_id": record_id, "error": message[:700]})
                else:
                    delay = min(10, 2 * (2 ** attempt))
                    print(f"Retrying HEPData record {record_id} after {delay}s: {message[:200]}", flush=True)
                    time.sleep(delay)
        if not success:
            failed_ids.append(record_id)
        time.sleep(1.0)

    # GitHub artifact paths must be portable across Windows/Linux filesystems.
    # HEPData titles can contain angle brackets, colons, and other forbidden
    # characters. Sanitize names while preserving originals and file hashes.
    sanitize_artifact_paths(ROOT, files)

    manifest = {
        "schema_version": 3,
        "source": "HEPData",
        "source_url": "https://www.hepdata.net/",
        "source_docs": "https://hepdata.readthedocs.io/",
        "collection_type": "machine_readable_published_particle_physics_tables",
        "query_log": query_log,
        "requested_record_ids": requested_ids,
        "downloaded_record_ids": downloaded_ids,
        "failed_record_ids": failed_ids,
        "downloaded_file_count": len(files),
        "total_bytes": total_bytes,
        "files": files,
        "errors": errors,
        "license_policy": "Retain each record's license and citation metadata; check record-level reuse terms before redistribution. This collector does not relicense source data.",
        "limitations": [
            "HEPData covers publication-associated high-energy and particle-physics tables, not every Physics discipline.",
            "Search results do not guarantee every table from a publication is deposited.",
            "This is a bounded incremental acquisition run, not a complete HEPData mirror."
        ]
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pending_retry = [{"topic": topic, "id": record_id}
                     for topic, record_id in found if record_id not in set(downloaded_ids)]
    completed_ids = list(dict.fromkeys(list(completed) + downloaded_ids))[-5000:]
    cursor_file.write_text(json.dumps({
        "next_query": (start + max(1, len(query_log))) % len(QUERIES),
        "pending_retry": pending_retry,
        "completed_ids": completed_ids
    }, indent=2))
    print(json.dumps({
        "requested_records": len(requested_ids),
        "downloaded_records": len(downloaded_ids),
        "downloaded_files": len(files),
        "total_bytes": total_bytes,
        "failed_records": len(failed_ids),
        "errors": errors
    }, indent=2), flush=True)
    return 0 if files else 1

if __name__ == "__main__":
    sys.exit(main())
