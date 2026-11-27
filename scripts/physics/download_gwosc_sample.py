#!/usr/bin/env python3
"""Download verified 32-second measured LIGO strain files for GW150914."""
from __future__ import annotations
import hashlib, json, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("VISUAL_PHYSICS_RAW_DIR", "physics-raw-data/gwosc"))
MAX_FILE_BYTES = 25 * 1024 * 1024
FILES = {
    "H1": "https://gwosc.org/eventapi/json/GWTC-1-confident/GW150914/v3/H-H1_GWOSC_4KHZ_R1-1126259447-32.hdf5",
    "L1": "https://gwosc.org/eventapi/json/GWTC-1-confident/GW150914/v3/L-L1_GWOSC_4KHZ_R1-1126259447-32.hdf5",
}
MAGIC = b"\x89HDF\r\n\x1a\n"

def fetch(detector: str, url: str) -> dict:
    target = ROOT / url.rsplit("/", 1)[-1]
    temp = target.with_suffix(target.suffix + ".part")
    digest, total = hashlib.sha256(), 0
    request = urllib.request.Request(url, headers={"User-Agent": "VISUAL-Open-Science-Collector/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temp.open("wb") as out:
            if response.status != 200:
                raise RuntimeError(f"{detector}: HTTP {response.status}")
            while True:
                block = response.read(1024 * 1024)
                if not block: break
                total += len(block)
                if total > MAX_FILE_BYTES:
                    raise RuntimeError(f"{detector}: file exceeds 25 MiB safety limit")
                digest.update(block)
                out.write(block)
        with temp.open("rb") as handle:
            if handle.read(8) != MAGIC:
                raise RuntimeError(f"{detector}: HDF5 signature mismatch")
        temp.replace(target)
        return {"detector": detector, "url": url, "file": str(target),
                "bytes": total, "sha256": digest.hexdigest(),
                "format": "HDF5", "validation": "HTTP 200; HDF5 signature; SHA-256"}
    except Exception:
        temp.unlink(missing_ok=True)
        raise

def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    records, errors = [], []
    for detector, url in FILES.items():
        try:
            records.append(fetch(detector, url))
            time.sleep(0.5)
        except Exception as exc:
            errors.append({"detector": detector, "error": str(exc)})
    manifest = {
        "schema_version": 1, "collection_type": "real_observational_physics_data",
        "topic": "gravitational_waves", "event": "GW150914",
        "event_gps_seconds": 1126259462.4, "sample_rate_hz": 4096,
        "duration_seconds": 32, "source": "Gravitational Wave Open Science Center (GWOSC)",
        "source_api": "https://gwosc.org/api/",
        "source_documentation": "https://gwosc.readthedocs.io/en/stable/locate.html",
        "license": "CC BY 4.0",
        "attribution": "Gravitational Wave Open Science Center (GWOSC); cite GW150914 GWTC-1-confident v3 and follow acknowledgement guidance.",
        "data_description": "Measured LIGO H1 and L1 detector strain time series around the GW150914 event.",
        "files": records, "errors": errors,
        "total_bytes": sum(x["bytes"] for x in records),
        "actual_file_count": len(records),
        "complete_for_requested_detectors": len(records) == len(FILES) and not errors,
        "limitations": "Two 32-second event-centred strain files; not the full LIGO archive or raw detector electronics output."
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["complete_for_requested_detectors"] else 1

if __name__ == "__main__":
    sys.exit(main())
