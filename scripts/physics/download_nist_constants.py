#!/usr/bin/env python3
"""Acquire NIST CODATA machine-readable fundamental constants reference table."""
from __future__ import annotations
import hashlib, json, os, sys, urllib.request
from pathlib import Path

URL = "https://physics.nist.gov/cuu/Constants/Table/allascii.txt"
ROOT = Path(os.environ.get("VISUAL_PHYSICS_RAW_DIR", "physics-raw-data/nist-codata"))
MAX_BYTES = 8 * 1024 * 1024

def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "VISUAL-Open-Science-Collector/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        if response.status != 200: raise RuntimeError(f"NIST HTTP {response.status}")
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES: raise RuntimeError("NIST table exceeds 8 MiB safety limit")
    text = payload.decode("utf-8", errors="strict")
    if "speed of light in vacuum" not in text.lower() or "Planck constant" not in text:
        raise RuntimeError("Downloaded response does not look like the NIST constants table")
    if len(text.splitlines()) < 20: raise RuntimeError("NIST table unexpectedly short")
    path = ROOT / "codata_fundamental_constants_2022_ascii.txt"
    path.write_bytes(payload)
    manifest = {
        "schema_version": 1, "collection_type": "scientific_reference_data",
        "topic": "fundamental_physical_constants", "dataset": "NIST CODATA 2022 recommended values",
        "source": "National Institute of Standards and Technology (NIST)",
        "url": URL, "reference_page": "https://physics.nist.gov/cuu/Constants/",
        "version": "CODATA 2022", "last_content_update": "2024-05",
        "license": "NIST data reuse terms apply; retain source attribution",
        "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
        "file": str(path), "format": "ASCII text",
        "validation": {"utf8": True, "minimum_lines": 20, "required_markers": ["speed of light in vacuum", "Planck constant"]},
        "limitations": "Recommended reference constants with uncertainties, not raw laboratory time-series measurements."
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
