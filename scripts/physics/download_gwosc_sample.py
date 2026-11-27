#!/usr/bin/env python3
"""Download a small, real LIGO strain-data sample from GWOSC."""
from __future__ import annotations
import hashlib, json, os, sys, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse
from gwosc.locate import get_event_urls

ROOT = Path(os.environ.get("VISUAL_PHYSICS_RAW_DIR", "physics-raw-data/gwosc"))
EVENT = "GW150914"
DETECTORS = ("H1", "L1")
MAX_FILE_BYTES = 25 * 1024 * 1024
USER_AGENT = "VISUAL-Open-Science-Collector/1.0"

def download(url: str, target: Path) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    digest, total = hashlib.sha256(), 0
    temp = target.with_suffix(target.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temp.open("wb") as out:
            if getattr(response, "status", 200) != 200:
                raise RuntimeError(f"HTTP failure for {url}")
            while True:
                block = response.read(1024 * 1024)
                if not block: break
                total += len(block)
                if total > MAX_FILE_BYTES:
                    raise RuntimeError(f"File exceeds {MAX_FILE_BYTES} byte safety ceiling")
                digest.update(block); out.write(block)
        with temp.open("rb") as handle: magic = handle.read(8)
        if magic != b"\x89HDF\r\n\x1a\n":
            raise RuntimeError(f"Payload is not HDF5: {url}")
        temp.replace(target)
        return {"url": url, "file": str(target), "bytes": total,
                "sha256": digest.hexdigest(), "format": "HDF5",
                "validation": "HDF5 signature verified"}
    except Exception:
        temp.unlink(missing_ok=True)
        raise

def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    records, errors = [], []
    for detector in DETECTORS:
        try:
            urls = get_event_urls(EVENT, detector=detector, duration=32,
                                  sample_rate=4096, format="hdf5")
            url = next((u for u in urls if "-32.hdf5" in u), None)
            if not url: raise RuntimeError(f"No 32-second HDF5 file for {detector}: {urls}")
            target = ROOT / Path(urlparse(url).path).name
            if target.exists() and target.stat().st_size:
                payload = target.read_bytes()
                if payload[:8] == b"\x89HDF\r\n\x1a\n":
                    records.append({"url": url, "file": str(target), "bytes": len(payload),
                                    "sha256": hashlib.sha256(payload).hexdigest(),
                                    "format": "HDF5", "validation": "existing payload revalidated"})
                    continue
            records.append(download(url, target))
            time.sleep(0.5)
        except Exception as exc:
            errors.append({"detector": detector, "error": str(exc)})
    manifest = {
        "schema_version": 1, "collection_type": "real_observational_physics_data",
        "topic": "gravitational_waves", "event": EVENT, "event_gps_seconds": 1126259462.4,
        "detectors": list(DETECTORS), "source": "Gravitational Wave Open Science Center (GWOSC)",
        "source_api": "https://gwosc.org/api/",
        "source_documentation": "https://gwosc.readthedocs.io/en/stable/locate.html",
        "license": "CC BY 4.0", "attribution": "GWOSC; cite the event/data release and follow acknowledgement guidance.",
        "data_description": "Measured LIGO detector strain time series around GW150914; 4096 Hz, 32-second HDF5 event files.",
        "files": records, "errors": errors,
        "total_bytes": sum(r["bytes"] for r in records), "actual_file_count": len(records),
        "complete_for_requested_detectors": len(records) == len(DETECTORS) and not errors,
        "validation_policy": ["HTTP success", "25 MiB per-file ceiling", "HDF5 signature", "SHA-256"],
        "limitations": "Small verified sample, not the complete LIGO archive or raw detector electronics output."
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["complete_for_requested_detectors"] else 1

if __name__ == "__main__":
    sys.exit(main())
