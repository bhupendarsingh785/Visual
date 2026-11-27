#!/usr/bin/env python3
"""Incremental HEPData physics-table acquisition for VISUAL.

Downloads machine-readable CSV tables from HEPData for a rotating set of
particle/high-energy physics queries. This is one source-specific tranche,
not a claim of complete Physics coverage.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from hepdata_cli.api import Client

ROOT = Path(os.environ.get("VISUAL_PHYSICS_RAW_DIR", "physics-raw-data/hepdata"))
MAX_RECORDS = int(os.environ.get("VISUAL_HEPDATA_MAX_RECORDS", "60"))
MAX_BYTES = int(os.environ.get("VISUAL_HEPDATA_MAX_BYTES", str(1024 * 1024 * 1024)))
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

def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    client = Client(verbose=True)
    cursor_file = ROOT / "query_cursor.json"
    cursor = json.loads(cursor_file.read_text()) if cursor_file.exists() else {"next_query": 0}
    start = int(cursor.get("next_query", 0)) % len(QUERIES)
    selected = QUERIES[start:] + QUERIES[:start]

    found = []
    query_log = []
    seen = set()
    for name, query in selected:
        try:
            ids = client.find(query, ids="hepdata", format=list)
            ids = [str(x) for x in (ids or [])]
            fresh = [x for x in ids if x not in seen]
            seen.update(fresh)
            found.extend((name, x) for x in fresh)
            query_log.append({"topic": name, "query": query, "ids_found": len(ids), "new_ids": len(fresh), "status": "ok"})
        except Exception as exc:
            query_log.append({"topic": name, "query": query, "status": "error", "error": str(exc)[:500]})
        if len(found) >= MAX_RECORDS:
            break
        time.sleep(1.0)

    found = found[:MAX_RECORDS]
    ids = [record_id for _, record_id in found]
    downloads = {}
    errors = []
    if ids:
        try:
            downloads = client.download(
                ids, ids="hepdata", file_format="csv",
                download_dir=str(ROOT / "tables")
            ) or {}
        except Exception as exc:
            errors.append({"stage": "download", "error": str(exc)[:1000]})

    files = []
    total_bytes = 0
    for path in sorted(set(flatten_files(downloads))):
        size = path.stat().st_size
        total_bytes += size
        if total_bytes > MAX_BYTES:
            path.unlink(missing_ok=True)
            errors.append({"stage": "budget", "file": str(path), "error": "Per-run byte budget exceeded; remaining files omitted"})
            continue
        files.append({"path": str(path), "bytes": size, "sha256": sha256(path), "format": path.suffix.lstrip(".")})

    manifest = {
        "schema_version": 1,
        "source": "HEPData",
        "source_url": "https://www.hepdata.net/",
        "source_docs": "https://hepdata.readthedocs.io/",
        "collection_type": "machine_readable_published_particle_physics_tables",
        "query_log": query_log,
        "requested_record_ids": ids,
        "downloaded_file_count": len(files),
        "total_bytes": total_bytes,
        "files": files,
        "errors": errors,
        "license_policy": "HEPData is an open-access repository; individual record licenses and citation instructions must be retained and checked before redistribution. This workflow downloads research tables for local research use and does not relicense them.",
        "limitations": [
            "HEPData covers publication-associated high-energy/particle physics tables, not every Physics discipline.",
            "A search match is not proof that every table in a publication was deposited.",
            "This run is bounded by record and byte budgets; it is incremental, not a complete mirror."
        ]
    }
    out = ROOT / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    cursor_file.write_text(json.dumps({"next_query": (start + max(1, len(query_log))) % len(QUERIES)}, indent=2))
    print(json.dumps({k: manifest[k] for k in ("requested_record_ids", "downloaded_file_count", "total_bytes", "errors")}, indent=2))
    return 0 if not errors and (not ids or files) else 1

if __name__ == "__main__":
    sys.exit(main())
