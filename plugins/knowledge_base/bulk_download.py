"""Resumable, bounded public dataset downloader for VISUAL (explicit URL only)."""
import hashlib
import ipaddress
import json
import os
import shutil
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHUNK = 1024 * 1024
DEFAULT_CAP = 512 * 1024 * 1024
UA = "VISUAL-DatasetFetcher/1.0 (user-initiated; resumable; bounded)"

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect blocked; verify the new official URL manually.", headers, fp)

def _validate_url(url):
    p = urllib.parse.urlsplit(str(url).strip())
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Only credential-free HTTPS dataset URLs are allowed.")
    host = p.hostname.encode("idna").decode("ascii")
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("Host resolution failed: " + str(exc))
    if not addresses:
        raise ValueError("Host has no resolved addresses.")
    for item in addresses:
        if not ipaddress.ip_address(item[4][0]).is_global:
            raise ValueError("Private, local or reserved IP blocked.")
    return urllib.parse.urlunsplit(("https", host, p.path or "/", p.query, "")), host

def _destination(path, home=None):
    p = Path(path).expanduser()
    if not p.is_absolute():
        raise ValueError("Destination must be an absolute path.")
    parent = p.parent.resolve()
    roots = [Path(home or Path.home() / ".visual").expanduser().resolve(),
             Path("/storage/emulated/0/Download"), Path("/storage/emulated/0/Documents")]
    if not any(parent == r or r in parent.parents for r in roots if r.exists()):
        raise ValueError("Destination allowed only inside VISUAL home, Android Download or Documents.")
    parent.mkdir(parents=True, exist_ok=True)
    return parent / p.name

def download_dataset(url, destination, max_bytes=DEFAULT_CAP, expected_sha256="", home=None):
    """Download one explicitly selected file; .part is retained on interruption for resume."""
    url, host = _validate_url(url)
    dest = _destination(destination, home)
    cap = max(1, min(int(max_bytes), 20 * 1024**3))
    if dest.exists():
        raise FileExistsError("Destination already exists; choose a new name or move the verified file.")
    part = dest.with_name(dest.name + ".part")
    metadata = dest.with_name(dest.name + ".download.json")
    offset = part.stat().st_size if part.exists() else 0
    if offset > cap:
        raise ValueError("Existing partial file exceeds configured max_bytes.")
    free = shutil.disk_usage(dest.parent).free
    if free < min(cap - offset, 16 * 1024 * 1024):
        raise OSError("Insufficient free storage for a safe download start.")
    headers = {"User-Agent": UA, "Accept": "*/*"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers=headers)
    started = time.time()
    digest = hashlib.sha256()
    if offset:
        with part.open("rb") as old:
            for block in iter(lambda: old.read(CHUNK), b""):
                digest.update(block)
    with opener.open(req, timeout=30) as response:
        status = getattr(response, "status", response.getcode())
        if offset and status != 206:
            raise ValueError("Server did not honor Range resume; partial file retained. Use a new destination for a fresh download.")
        if not offset and status != 200:
            raise ValueError(f"Unexpected HTTP status: {status}")
        if offset:
            content_range = response.headers.get("Content-Range", "")
            if not content_range.startswith(f"bytes {offset}-"):
                raise ValueError("Content-Range mismatch; partial file retained.")
        length = response.headers.get("Content-Length")
        expected_total = offset + int(length) if length and length.isdigit() else None
        if expected_total is not None and expected_total > cap:
            raise ValueError(f"Remote file size {expected_total} exceeds configured cap {cap}.")
        mode = "ab" if offset else "wb"
        received = offset
        with part.open(mode) as out:
            while True:
                block = response.read(CHUNK)
                if not block:
                    break
                received += len(block)
                if received > cap:
                    raise ValueError("Download reached configured size cap; partial file retained.")
                out.write(block)
                digest.update(block)
            out.flush()
            os.fsync(out.fileno())
        etag = response.headers.get("ETag", "")
        modified = response.headers.get("Last-Modified", "")
        content_type = response.headers.get("Content-Type", "")
    sha = digest.hexdigest()
    if expected_sha256 and sha.lower() != str(expected_sha256).strip().lower():
        raise ValueError("SHA-256 mismatch; downloaded .part retained for inspection.")
    if expected_total is not None and received != expected_total:
        raise ValueError(f"Incomplete transfer: expected {expected_total} bytes, received {received}; .part retained.")
    os.replace(part, dest)
    record = {"url": url, "host": host, "bytes": received, "sha256": sha,
              "etag": etag, "last_modified": modified, "content_type": content_type,
              "downloaded_at": time.time(), "elapsed_seconds": round(time.time()-started, 2),
              "license": "not inferred; user must verify publisher terms"}
    metadata.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return {"status": "downloaded", "path": str(dest), **record,
            "note": "File downloaded only; it is not yet parsed or indexed. Review its license before reuse."}
