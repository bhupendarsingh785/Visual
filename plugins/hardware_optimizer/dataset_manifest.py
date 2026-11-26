"""Local dataset inventory with provenance, licensing and privacy gates.

This module indexes files only; it never downloads, opens archives, executes data,
or uploads content. Callers must supply source and license metadata.
"""
import hashlib
import json
import os
from pathlib import Path

DEFAULT_EXTENSIONS = {".txt", ".jsonl", ".csv", ".tsv", ".parquet", ".wav",
                      ".flac", ".mp3", ".png", ".jpg", ".jpeg", ".webp",
                      ".mp4", ".json", ".npy", ".npz"}


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _sha256(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def build_dataset_manifest(dataset_dir, *, source, license_name,
                           consent_status="not_applicable",
                           allowed_extensions=None, max_files=100000,
                           max_total_bytes=50 * 1024**3):
    """Create a deterministic manifest for local files; no content is emitted."""
    if not str(source).strip():
        raise ValueError("source provenance is required")
    if not str(license_name).strip():
        raise ValueError("license_name is required; use 'unknown' to quarantine")
    if consent_status not in {"not_applicable", "verified", "pending", "denied"}:
        raise ValueError("invalid consent_status")
    if int(max_files) < 1 or int(max_files) > 1000000:
        raise ValueError("max_files must be in [1, 1000000]")
    if int(max_total_bytes) < 1:
        raise ValueError("max_total_bytes must be positive")

    root = Path(dataset_dir).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("dataset_dir must be a directory")
    extensions = {x.lower() if x.startswith(".") else "." + x.lower()
                  for x in (allowed_extensions or DEFAULT_EXTENSIONS)}
    entries = []
    total = 0
    for candidate in sorted(root.rglob("*")):
        if candidate.is_symlink():
            continue
        if not candidate.is_file() or candidate.suffix.lower() not in extensions:
            continue
        path = candidate.resolve(strict=True)
        if not _inside(path, root):
            continue
        size = path.stat().st_size
        total += size
        if len(entries) >= int(max_files):
            raise ValueError("file limit exceeded; narrow the dataset directory")
        if total > int(max_total_bytes):
            raise ValueError("dataset byte limit exceeded")
        entries.append({
            "relative_path": path.relative_to(root).as_posix(),
            "size_bytes": size,
            "sha256": _sha256(path),
            "format": path.suffix.lower().lstrip("."),
        })

    consent_ok = consent_status in {"not_applicable", "verified"}
    license_ok = license_name.strip().lower() not in {"unknown", "unverified", "none"}
    return {
        "schema_version": 1,
        "dataset_root": str(root),
        "source": str(source).strip(),
        "license": str(license_name).strip(),
        "consent_status": consent_status,
        "training_eligible": bool(entries) and consent_ok and license_ok,
        "quarantine_reason": None if entries and consent_ok and license_ok else
            ("empty_dataset" if not entries else
             "license_unverified" if not license_ok else "consent_not_verified"),
        "file_count": len(entries),
        "total_bytes": total,
        "files": entries,
    }


def write_dataset_manifest(manifest, output_path):
    """Write manifest atomically outside the dataset tree if possible."""
    target = Path(output_path).expanduser().resolve()
    root = Path(manifest["dataset_root"]).resolve()
    if _inside(target, root):
        raise ValueError("manifest output must be outside the dataset directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    temporary.write_text(payload + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return str(target)
