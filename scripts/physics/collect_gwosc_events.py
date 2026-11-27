#!/usr/bin/env python3
"""Acquire a bounded, reproducible multi-event sample of measured GWOSC strain."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import requests
from urllib.parse import urlparse

import h5py
import numpy as np
from gwosc.locate import get_event_urls

ROOT = Path(os.environ.get("VISUAL_PHYSICS_RAW_DIR", "physics-raw-data/gwosc-events")).resolve()
EVENTS = [
    "GW150914", "GW151226", "GW170104", "GW170608",
    "GW170814", "GW170817",
]
DETECTORS = {"H1", "L1", "V1"}
SAMPLE_RATE_HZ = 4096
DURATION_SECONDS = 32
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 250 * 1024 * 1024
MAGIC = b"\x89HDF\r\n\x1a\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_hdf5(path: Path) -> dict:
    """Read the HDF5 structure and require a substantial numeric 1-D strain-like array."""
    candidates = []
    with h5py.File(path, "r") as handle:
        def visitor(name, obj):
            if isinstance(obj, h5py.Dataset) and obj.ndim == 1 and obj.size >= 1000:
                if np.issubdtype(obj.dtype, np.number):
                    candidates.append({"dataset": name, "samples": int(obj.size), "dtype": str(obj.dtype)})
        handle.visititems(visitor)
        if not candidates:
            raise RuntimeError("HDF5 is readable but contains no substantial numeric 1-D dataset")
    candidates.sort(key=lambda item: item["samples"], reverse=True)
    return {"numeric_1d_datasets": len(candidates), "primary_dataset": candidates[0]}


def download(event: str, detector: str, url: str) -> dict:
    filename = Path(urlparse(url).path).name
    target = ROOT / event / detector / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    request = urllib.request.Request(url, headers={"User-Agent": "VISUAL-Open-Science-Collector/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temp.open("wb") as out:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_FILE_BYTES:
                    raise RuntimeError(f"file exceeds {MAX_FILE_BYTES} byte safety limit")
                digest.update(block)
                out.write(block)
        with temp.open("rb") as handle:
            if handle.read(8) != MAGIC:
                raise RuntimeError("HDF5 signature mismatch")
        validation = inspect_hdf5(temp)
        temp.replace(target)
        return {
            "event": event, "detector": detector, "url": url,
            "path": target.relative_to(ROOT).as_posix(), "bytes": total,
            "sha256": digest.hexdigest(), "format": "HDF5",
            "sample_rate_hz": SAMPLE_RATE_HZ, "duration_seconds": DURATION_SECONDS,
            "validation": {"http_status": 200, "hdf5_signature": True, "hdf5_readable": True, **validation},
        }
    except Exception:
        temp.unlink(missing_ok=True)
        raise


class BoundedTimeoutSession(requests.Session):
    """Ensure every GWOSC API request has a finite connect/read timeout."""
    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (10, 45))
        return super().request(method, url, **kwargs)


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    files, errors, event_results = [], [], []
    total_bytes = 0
    session = BoundedTimeoutSession()
    for event in EVENTS:
        print(f"Discovering GWOSC strain files for {event}", flush=True)
        try:
            urls = get_event_urls(
                event, duration=DURATION_SECONDS, sample_rate=SAMPLE_RATE_HZ,
                format="hdf5", session=session, pagesize=100
            )
            selected = []
            for url in urls:
                base = Path(urlparse(url).path).name
                detector = "H1" if base.startswith("H-") else "L1" if base.startswith("L-") else "V1" if base.startswith("V-") else None
                if detector in DETECTORS and detector not in {x["detector"] for x in selected}:
                    selected.append({"detector": detector, "url": url})
            print(f"{event}: {len(selected)} detector files discovered", flush=True)
            if not selected:
                errors.append({"event": event, "stage": "discovery", "error": "No matching 32-second 4 kHz HDF5 files returned"})
                event_results.append({"event": event, "status": "no_matching_files"})
                continue
            succeeded = []
            for item in selected:
                if total_bytes >= MAX_TOTAL_BYTES:
                    errors.append({"event": event, "stage": "budget", "error": "Collection byte budget reached"})
                    break
                try:
                    record = download(event, item["detector"], item["url"])
                    if total_bytes + record["bytes"] > MAX_TOTAL_BYTES:
                        (ROOT / record["path"]).unlink(missing_ok=True)
                        errors.append({"event": event, "detector": item["detector"], "stage": "budget", "error": "Would exceed total byte budget"})
                        continue
                    files.append(record)
                    succeeded.append(item["detector"])
                    print(f"Downloaded {event} {item['detector']}: {record['bytes']} bytes; HDF5 and SHA-256 validated", flush=True)
                    total_bytes += record["bytes"]
                except Exception as exc:
                    errors.append({"event": event, "detector": item["detector"], "stage": "download_or_validation", "error": str(exc)[:500]})
                time.sleep(0.5)
            event_results.append({"event": event, "status": "downloaded" if succeeded else "failed", "detectors": succeeded})
        except Exception as exc:
            errors.append({"event": event, "stage": "discovery", "error": str(exc)[:500]})
            event_results.append({"event": event, "status": "discovery_failed"})

    manifest = {
        "schema_version": 2,
        "collection_type": "real_observational_gravitational_wave_strain",
        "source": "Gravitational Wave Open Science Center (GWOSC)",
        "source_api": "https://gwosc.org/api/",
        "source_documentation": "https://gwosc.readthedocs.io/en/stable/locate.html",
        "license": "CC BY 4.0",
        "attribution": "Gravitational Wave Open Science Center (GWOSC); cite the corresponding event/catalog data releases and follow GWOSC acknowledgement guidance.",
        "requested_events": EVENTS,
        "detectors_requested": sorted(DETECTORS),
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "duration_seconds": DURATION_SECONDS,
        "events": event_results,
        "files": files,
        "actual_file_count": len(files),
        "total_bytes": total_bytes,
        "errors": errors,
        "validation_summary": {
            "all_downloaded_files_http_200": all(x["validation"]["http_status"] == 200 for x in files),
            "all_hdf5_signatures_valid": all(x["validation"]["hdf5_signature"] for x in files),
            "all_hdf5_files_readable": all(x["validation"]["hdf5_readable"] for x in files),
            "all_files_have_sha256": all(len(x["sha256"]) == 64 for x in files),
        },
        "limitations": [
            "This is a bounded event-centred sample, not the full GWOSC archive or continuous observing-run data.",
            "Only 32-second, 4096 Hz HDF5 files are requested; detector availability differs by event.",
            "A readable HDF5 container and numeric array are structural checks, not a scientific re-analysis of each event."
        ]
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "requested_events": len(EVENTS), "downloaded_files": len(files),
        "total_bytes": total_bytes, "errors": len(errors),
        "validation_summary": manifest["validation_summary"]
    }, indent=2), flush=True)
    return 0 if files and all(manifest["validation_summary"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
