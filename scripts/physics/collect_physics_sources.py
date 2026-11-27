#!/usr/bin/env python3
"""Bounded multi-source Physics acquisition with per-source provenance and validation.

This is an incremental public-data collector, not a claim to mirror entire archives.
Every source is isolated: a failed/blocked source does not erase successful downloads.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import requests

ROOT = Path(os.environ.get("VISUAL_PHYSICS_RAW_DIR", "physics-raw-data/source-collections")).resolve()
MAX_FILE = int(os.environ.get("VISUAL_PHYSICS_MAX_FILE_BYTES", str(128 * 1024 * 1024)))
MAX_TOTAL = int(os.environ.get("VISUAL_PHYSICS_MAX_TOTAL_BYTES", str(512 * 1024 * 1024)))
TOTAL = 0
UA = "VISUAL-Physics-Knowledge-Base/1.0 (research data acquisition; contact via repository)"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save_bytes(topic: str, name: str, url: str, payload: bytes, *, license_text: str,
               citation: str, source_type: str, validation: dict | None = None) -> dict:
    global TOTAL
    if not payload:
        raise ValueError("empty response")
    if len(payload) > MAX_FILE:
        raise ValueError(f"file exceeds per-file budget ({len(payload)} > {MAX_FILE})")
    if TOTAL + len(payload) > MAX_TOTAL:
        raise ValueError("collection total byte budget reached")
    folder = ROOT / topic
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(payload)
    TOTAL += len(payload)
    return {
        "path": path.relative_to(ROOT).as_posix(), "url": url,
        "bytes": len(payload), "sha256": digest(path),
        "format": path.suffix.lstrip(".").lower() or "binary",
        "license": license_text, "citation": citation,
        "source_type": source_type, "validation": validation or {},
    }


def get_bytes(url: str, *, timeout=90, headers=None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        data = response.read(MAX_FILE + 1)
    if len(data) > MAX_FILE:
        raise RuntimeError("response exceeds per-file safety ceiling")
    return data


def post_bytes(url: str, body: dict, timeout=180) -> bytes:
    response = requests.post(url, json=body, headers={"User-Agent": UA}, timeout=timeout)
    response.raise_for_status()
    data = response.content
    if len(data) > MAX_FILE:
        raise RuntimeError("response exceeds per-file safety ceiling")
    return data


def validate_zip(payload: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f"ZIP CRC failure: {bad}")
        names = z.namelist()
        if not names:
            raise RuntimeError("ZIP contains no members")
        for name in names:
            p = Path(name)
            if p.is_absolute() or ".." in p.parts:
                raise RuntimeError(f"unsafe ZIP member path: {name}")
        return {"zip_crc": "ok", "members": len(names), "member_sample": names[:20]}


def validate_csv(payload: bytes) -> dict:
    text = payload.decode("utf-8-sig", errors="strict")
    rows = list(csv.reader(io.StringIO(text), strict=True))
    useful = [r for r in rows if any(c.strip() for c in r)]
    if not useful:
        raise RuntimeError("CSV has no non-empty rows")
    return {"utf8": True, "csv_parse": "ok", "rows_including_header": len(useful),
            "columns_header": len(useful[0])}


def attempt(results: list, topic: str, source: str, fn) -> None:
    started = time.time()
    try:
        files, details = fn()
        results.append({
            "topic": topic, "source": source, "status": "downloaded" if files else "metadata_only",
            "files": files, "details": details, "elapsed_seconds": round(time.time()-started, 2)
        })
        print(json.dumps({"topic": topic, "source": source, "status": results[-1]["status"],
                          "files": len(files), "details": details}, ensure_ascii=False), flush=True)
    except Exception as exc:
        results.append({"topic": topic, "source": source, "status": "failed_or_blocked",
                        "files": [], "error": str(exc)[:1200],
                        "elapsed_seconds": round(time.time()-started, 2)})
        print(json.dumps({"topic": topic, "source": source, "status": "failed_or_blocked",
                          "error": str(exc)[:500]}, ensure_ascii=False), flush=True)



def collect_cern_open_data():
    query = "experiment:CMS AND type:Dataset"
    url = "https://opendata.cern.ch/api/records/?" + urllib.parse.urlencode({"q": query, "size": 20})
    payload = get_bytes(url, timeout=120)
    obj = json.loads(payload.decode("utf-8"))
    hits = obj.get("hits", {}).get("hits", [])
    if not hits:
        raise RuntimeError("CERN Open Data API returned no CMS dataset records")
    metadata_file = save_bytes("cern-open-data", "cms_dataset_search_records.json", url, payload,
        license_text="Portal datasets are generally released under open licenses; verify each record's exact license before reuse",
        citation="CERN Open Data Portal, CMS dataset records API; query: " + query,
        source_type="CERN CMS collision-data record metadata",
        validation={"json": True, "records": len(hits)})
    files = [metadata_file]
    downloaded = []
    for hit in hits:
        record_id = hit.get("id")
        source = hit.get("metadata") or hit.get("_source", {}).get("metadata") or {}
        license_items = source.get("rights") or source.get("license") or []
        license_text = json.dumps(license_items, ensure_ascii=False) if license_items else ""
        # Dataset file licenses are record-specific; only acquire files where
        # the record metadata explicitly identifies a CC0/open data license.
        license_lower = license_text.lower()
        if not any(token in license_lower for token in ("cc0", "creative commons zero", "public domain")):
            continue
        file_list = hit.get("files") or hit.get("_source", {}).get("files") or []
        if isinstance(file_list, dict):
            file_list = file_list.get("entries", [])
        for entry in file_list:
            key = entry.get("key") or entry.get("filename")
            size = int(entry.get("size") or 0)
            if not key or size <= 0 or size > 15 * 1024 * 1024:
                continue
            file_url = f"https://opendata.cern.ch/api/records/{record_id}/files/{urllib.parse.quote(key, safe='')}/content"
            try:
                data = get_bytes(file_url, timeout=180)
                if size and len(data) != size:
                    raise RuntimeError(f"CERN file size mismatch for {key}: {len(data)} != {size}")
                files.append(save_bytes("cern-open-data", f"record-{record_id}-{Path(key).name}",
                    file_url, data, license_text=license_text,
                    citation=source.get("title", "CERN Open Data CMS dataset") + f"; record {record_id}",
                    source_type="CERN released CMS dataset file",
                    validation={"nonempty": True, "expected_size": size, "size_matches": len(data) == size}))
                downloaded.append({"record_id": record_id, "file": key, "bytes": len(data)})
                break
            except Exception:
                continue
        if downloaded:
            break
    return files, {"query": query, "records_found": len(hits), "dataset_files_downloaded": len(downloaded),
                   "downloaded": downloaded, "note": "Metadata saved for all hits; only first small record file with explicit CC0/public-domain metadata is acquired"}



def collect_nist_asd():
    files = []
    details = {"database": "NIST Atomic Spectra Database", "query_type": "spectral lines",
               "spectra": ["H I", "He I", "Fe I"], "wavelength_nm": [200, 1000]}
    for species in details["spectra"]:
        params = {
            "spectra": species, "limits_type": "0", "low_w": "200", "upp_w": "1000",
            "unit": "1", "format": "3", "submit": "Retrieve Data", "de": "0",
            "line_out": "0", "show_obs_wl": "1", "show_calc_wl": "1",
            "bibrefs": "1", "intens_out": "on", "A_out": "0", "no_spaces": "on",
            "output_type": "0"
        }
        url = "https://physics.nist.gov/cgi-bin/ASD/lines1.pl?" + urllib.parse.urlencode(params)
        payload = get_bytes(url, timeout=120)
        text = payload.decode("utf-8", errors="strict")
        if "error" in text[:1000].lower() and "spectra" in text[:1000].lower():
            raise RuntimeError(f"NIST ASD returned a query error for {species}: {text[:300]}")
        if len(text.splitlines()) < 3:
            raise RuntimeError(f"NIST ASD output unexpectedly short for {species}")
        files.append(save_bytes("nist-atomic-spectra", species.replace(" ", "_") + "_200-1000nm.tsv",
            url, payload, license_text="NIST ASD terms; cite ASD version and retrieval date; verify reuse terms",
            citation="NIST Atomic Spectra Database, spectral lines query; retrieved by VISUAL",
            source_type="evaluated atomic transition reference data",
            validation={"utf8": True, "minimum_lines": 3, "format": "NIST tab-delimited output"}))
        time.sleep(1)
    return files, {"species_queried": len(files), "note": "Line query subset, not a full ASD mirror"}


def collect_iaea():
    url = "https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=all"
    payload = get_bytes(url, timeout=120, headers={"User-Agent": "Livechart/1.0"})
    check = validate_csv(payload)
    files = [save_bytes("iaea-nuclear", "livechart_ground_states_all.csv", url, payload,
        license_text="IAEA LiveChart/ENSDF data; retain source and citation; check field-specific terms",
        citation="IAEA Nuclear Data Services, LiveChart of Nuclides, ground_states dataset",
        source_type="evaluated nuclear ground-state reference data", validation=check)]
    return files, {"dataset": "all ground states", **check}


def collect_pdg():
    url = "https://pdg.lbl.gov/2026/api/pdg-2026.0.sqlite"
    payload = get_bytes(url, timeout=180)
    if not payload.startswith(b"SQLite format 3\x00"):
        raise RuntimeError("PDG response is not a SQLite 3 database")
    path = ROOT / "pdg" / "pdg-2026.0.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    global TOTAL
    if len(payload) > MAX_FILE or TOTAL + len(payload) > MAX_TOTAL:
        path.unlink(missing_ok=True)
        raise RuntimeError("PDG SQLite exceeds collection budget")
    TOTAL += len(payload)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        edition = con.execute("SELECT * FROM pdginfo LIMIT 5").fetchall() if "pdginfo" in tables else []
    finally:
        con.close()
    if integrity != "ok" or not {"pdgid", "pdgdata", "pdgparticle"}.issubset(tables):
        path.unlink(missing_ok=True)
        raise RuntimeError(f"PDG database integrity/schema validation failed: {integrity}")
    files = [{"path": path.relative_to(ROOT).as_posix(), "url": url, "bytes": len(payload),
              "sha256": digest(path), "format": "sqlite",
              "license": "PDG 2026 Review: CC BY 4.0 except where otherwise noted",
              "citation": "F. Takahashi et al. (Particle Data Group), Review of Particle Physics, 2026",
              "source_type": "evaluated particle properties, measurements and references",
              "validation": {"sqlite_integrity_check": integrity, "tables": len(tables), "table_names": tables}}]
    return files, {"edition": "2026.0", "tables": len(tables), "pdginfo_sample": str(edition)[:500]}


def collect_nomad():
    url = "https://nomad-lab.eu/prod/v1/api/v1/entries/archive/download/query"
    body = {
        "query": {"results.material.elements": {"all": ["Ti", "O"]}},
        "required": {
            "metadata": {"entry_id": "*", "mainfile": "*", "upload_id": "*"},
            "results": {"material": "*"},
            "run": {"system[-1]": {"atoms": "*"}}
        },
        "pagination": {"page_size": 10}
    }
    payload = post_bytes(url, body, timeout=240)
    zcheck = validate_zip(payload)
    files = [save_bytes("nomad", "tio2_processed_archives_sample.zip", url, payload,
        license_text="NOMAD entry/dataset-specific license; inspect included manifest and each entry's terms",
        citation="NOMAD Repository, public Ti-O computational materials entries; query preserved in manifest",
        source_type="processed first-principles computational materials archives", validation=zcheck)]
    return files, {"query": body["query"], "required_fields": body["required"], **zcheck}


def collect_icecube():
    doi = "doi:10.7910/DVN/MMIIZA"
    api = "https://dataverse.harvard.edu/api/datasets/:persistentId/versions/:latest/files?persistentId=" + urllib.parse.quote(doi, safe="")
    meta_payload = get_bytes(api, timeout=90)
    meta = json.loads(meta_payload.decode("utf-8"))
    if meta.get("status") != "OK":
        raise RuntimeError(f"Dataverse metadata API status: {meta.get('status')}")
    data = meta["data"]
    selected = []
    for item in data:
        df = item.get("dataFile", {})
        label = item.get("label") or df.get("filename") or ""
        size = int(df.get("filesize") or 0)
        if label.lower().endswith("readme.txt") or (label.endswith("_exp.csv") and size <= 20*1024*1024):
            selected.append({"id": df.get("id"), "label": label, "size": size, "md5": (df.get("md5") or {})})
    selected = selected[:8]
    files = []
    for item in selected:
        if not item["id"]:
            continue
        url = f"https://dataverse.harvard.edu/api/access/datafile/{item['id']}"
        payload = get_bytes(url, timeout=120)
        check = {"nonempty": bool(payload), "dataverse_expected_size": item["size"],
                 "size_matches": len(payload) == item["size"]}
        if not check["size_matches"]:
            raise RuntimeError(f"IceCube file size mismatch for {item['label']}")
        files.append(save_bytes("icecube-neutrino", Path(item["label"]).name, url, payload,
            license_text="IceTracks-DR2 dataset CC0 1.0; cite DOI 10.7910/DVN/MMIIZA",
            citation="IceCube Collaboration (2026), IceTracks-DR2, Harvard Dataverse, DOI:10.7910/DVN/MMIIZA",
            source_type="observed neutrino candidate sample and release documentation", validation=check))
        time.sleep(0.5)
    if not files:
        raise RuntimeError("No eligible IceCube files found within per-file budget")
    return files, {"doi": doi, "version": data[0].get("versionNumber") if data else None,
                   "available_files": len(data), "selected_files": len(files),
                   "selection": "Readme plus experimental event CSV files <=20 MiB; not full 3.4 GB release"}


def collect_gaia():
    query = "SELECT TOP 100 source_id,ra,dec,parallax,pmra,pmdec,phot_g_mean_mag FROM gaiadr3.gaia_source WHERE parallax IS NOT NULL ORDER BY source_id"
    params = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query})
    url = "https://gea.esac.esa.int/tap-server/tap/sync?" + params
    payload = get_bytes(url, timeout=180)
    check = validate_csv(payload)
    files = [save_bytes("esa-gaia", "gaia_dr3_100_sources.csv", url, payload,
        license_text="ESA Gaia archive reuse and acknowledgement policy; cite Gaia DR3",
        citation="Gaia Collaboration et al., Gaia Data Release 3; ESA Gaia Archive TAP",
        source_type="astronomical astrometric and photometric catalogue sample", validation=check)]
    return files, {"query": query, **check}


def collect_mast():
    from astroquery.mast import Observations
    obs = Observations.query_criteria(objectname="M31", obs_collection="HST", dataproduct_type="image")
    if len(obs) == 0:
        raise RuntimeError("MAST returned no public HST image observations for M31")
    table = obs[:50]
    out = io.StringIO()
    table.write(out, format="csv")
    payload = out.getvalue().encode("utf-8")
    files = [save_bytes("nasa-mast", "mast_hst_m31_observations_top50.csv",
        "https://mast.stsci.edu/api/", payload,
        license_text="MAST product-specific data rights and mission citation; check each downloaded product",
        citation="Mikulski Archive for Space Telescopes (MAST), HST public observation metadata for M31",
        source_type="NASA astronomy archive observation metadata", validation=validate_csv(payload))]
    return files, {"observations_returned": len(obs), "metadata_rows_saved": len(table),
                   "note": "Observation metadata only; image products are not included in this tranche"}


def collect_optimade_mp():
    # Public OPTIMADE interface gives a bounded materials-structure route without MP API credentials.
    base = "https://optimade.materialsproject.org/v1/structures"
    params = urllib.parse.urlencode({"filter": 'elements HAS "Si"', "page_limit": "20"})
    url = base + "?" + params
    payload = get_bytes(url, timeout=120)
    obj = json.loads(payload.decode("utf-8"))
    data = obj.get("data", [])
    if not data:
        raise RuntimeError("Materials Project OPTIMADE returned no structures")
    files = [save_bytes("materials-project", "optimade_si_structures_top20.json", url, payload,
        license_text="Materials Project OPTIMADE data license/citation: CC BY 4.0 per provider listing; verify current record metadata",
        citation="Materials Project, OPTIMADE structures API, Si-containing structures",
        source_type="computed materials crystal structures", validation={"json": True, "records": len(data)})]
    return files, {"records": len(data), "note": "OPTIMADE public subset; full Materials Project API endpoints require a user API key"}


def collect_ukaea_catalog_docs():
    """Acquire public MAST metadata plus a real Level-2 diagnostic signal sample."""
    import pandas as pd
    import xarray as xr

    base = "https://s3.echo.stfc.ac.uk/mast/fairmast-meta"
    files = []
    for name in ("l2_shots.parquet", "l2_sources.parquet", "l2_signals/signals_30421.parquet"):
        url = f"{base}/{name}"
        payload = get_bytes(url, timeout=180)
        # Read the Parquet footer/schema before accepting the original file.
        frame = pd.read_parquet(io.BytesIO(payload))
        if frame.empty:
            raise RuntimeError(f"FAIR-MAST metadata table is empty: {name}")
        files.append(save_bytes("ukaea-fair-mast", name.replace("/", "__"), url, payload,
            license_text="FAIR-MAST archive and metadata: CC BY-SA 4.0; cite FAIR-MAST and linked papers",
            citation="UKAEA FAIR-MAST MAST Data Catalog; public Level-2 metadata",
            source_type="tokamak shot/source/signal metadata in Parquet",
            validation={"parquet_readable": True, "rows": len(frame), "columns": list(frame.columns)}))

    shot_id = 30421
    shot_url = f"https://s3.echo.stfc.ac.uk/mast/level2/shots/{shot_id}.zarr"
    ds = xr.open_zarr(shot_url, group="summary", consolidated=False)
    selected = [name for name in ("ip", "plasma_current", "beta_pol", "beta_normal") if name in ds.data_vars]
    if not selected:
        selected = list(ds.data_vars)[:5]
    if not selected:
        raise RuntimeError("FAIR-MAST Zarr summary group has no data variables")
    frame = ds[selected].to_dataframe().reset_index()
    csv_payload = frame.to_csv(index=False).encode("utf-8")
    if len(csv_payload) > 30 * 1024 * 1024:
        raise RuntimeError("FAIR-MAST extracted signal table exceeds 30 MiB")
    check = validate_csv(csv_payload)
    files.append(save_bytes("ukaea-fair-mast", f"shot_{shot_id}_level2_summary_signals.csv",
        shot_url, csv_payload,
        license_text="FAIR-MAST archive data: CC BY-SA 4.0; cite FAIR-MAST and linked papers",
        citation="UKAEA FAIR-MAST MAST Data Catalog, Level-2 shot 30421 summary diagnostics",
        source_type="processed experimental tokamak diagnostic measurements",
        validation={"zarr_opened": True, "shot_id": shot_id, "variables": selected, **check}))
    return files, {"metadata_files": 3, "shot_id": shot_id, "actual_signal_csv": True,
                   "signal_variables": selected, "csv_rows": len(frame),
                   "level": "Level 2 processed/calibrated/interpolated data",
                   "license": "CC BY-SA 4.0",
                   "citation": "FAIR-MAST; Jackson et al., SoftwareX 27 (2024) 101869; Jackson et al., IEEE TPS (2025), DOI:10.1109/TPS.2025.3583419"}


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    tasks = [
        ("particle_physics", "CERN Open Data Portal", collect_cern_open_data),
        ("atomic_physics", "NIST Atomic Spectra Database", collect_nist_asd),
        ("nuclear_physics", "IAEA LiveChart / ENSDF", collect_iaea),
        ("particle_physics", "Particle Data Group 2026", collect_pdg),
        ("condensed_matter", "NOMAD public processed archives", collect_nomad),
        ("neutrino_physics", "IceCube IceTracks-DR2", collect_icecube),
        ("astronomy_cosmology", "ESA Gaia DR3 TAP", collect_gaia),
        ("astronomy_cosmology", "NASA MAST", collect_mast),
        ("condensed_matter", "Materials Project OPTIMADE", collect_optimade_mp),
        ("plasma_fusion", "UKAEA FAIR-MAST", collect_ukaea_catalog_docs),
    ]
    for topic, source, fn in tasks:
        attempt(results, topic, source, fn)
    manifest = {
        "schema_version": 1,
        "collection": "VISUAL Physics Knowledge Base multi-source tranche",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": results,
        "successful_sources": sum(x["status"] == "downloaded" for x in results),
        "metadata_only_sources": sum(x["status"] == "metadata_only" for x in results),
        "failed_or_blocked_sources": sum(x["status"] == "failed_or_blocked" for x in results),
        "downloaded_file_count": sum(len(x["files"]) for x in results),
        "downloaded_bytes": TOTAL,
        "limits": {"per_file_bytes": MAX_FILE, "total_bytes": MAX_TOTAL},
        "limitations": [
            "This is a bounded, source-specific tranche, not a complete mirror of any provider's entire archive.",
            "Materials Project OPTIMADE subset is not the full Materials Project API; full API access requires a user API key.",
            "IceTracks-DR2 is 3.4 GB; this run only takes README and selected experimental CSV files under 20 MiB each.",
            "NASA MAST tranche stores observation metadata only; image products need separate selection and size/license review.",
            "UKAEA README confirms public S3 access documentation; it is not itself experimental MAST diagnostic data.",
            "PDG edition is versioned and must not be merged silently with historical editions.",
            "NIST ASD line subsets are selected spectra and wavelength range, not the entire atomic spectra database."
        ]
    }
    path = ROOT / "physics_sources_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("successful_sources", "metadata_only_sources",
          "failed_or_blocked_sources", "downloaded_file_count", "downloaded_bytes")}, indent=2), flush=True)
    return 0 if manifest["downloaded_file_count"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
