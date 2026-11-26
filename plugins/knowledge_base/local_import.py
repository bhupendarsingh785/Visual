"""Incremental local dataset importer for VISUAL's offline knowledge store.

Supports text/Markdown/HTML/CSV/JSON/XML and line-oriented JSONL, including .gz.
Reads incrementally; never loads a multi-GB dataset into memory.
"""
import csv
import gzip
import hashlib
import html
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path
from html.parser import HTMLParser

from knowledge_engine import _connect, _chunks, _db_path, SECRET_RE

SUPPORTED = {".txt", ".md", ".rst", ".html", ".htm", ".csv", ".json", ".jsonl", ".ndjson", ".xml"}
MAX_RECORD_CHARS = 1_000_000


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def _safe_file(path, home=None):
    p = Path(path).expanduser().resolve(strict=True)
    if not p.is_file():
        raise ValueError("Path ek file hona chahiye.")
    roots = [Path(home or Path.home() / ".visual").expanduser().resolve()]
    # Android shared storage and common import folder; user must pass an exact file.
    roots += [Path("/storage/emulated/0/Download"), Path("/storage/emulated/0/Documents")]
    if not any(p == r or r in p.parents for r in roots if r.exists()):
        raise ValueError("Security: file sirf ~/.visual, Android Download ya Documents ke andar se import hogi.")
    if p.suffix.lower() not in SUPPORTED and not p.name.lower().endswith(tuple(x + ".gz" for x in SUPPORTED)):
        raise ValueError("Unsupported format. Supported: " + ", ".join(sorted(SUPPORTED)) + " and .gz variants.")
    return p


def _open_text(path):
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return path.open("r", encoding="utf-8", errors="replace", newline="")


def _to_text(value):
    if isinstance(value, str):
        out = value
    else:
        out = json.dumps(value, ensure_ascii=False, sort_keys=True)
    out = SECRET_RE.sub("[REDACTED_SECRET]", out)
    return out[:MAX_RECORD_CHARS]


def _records(path):
    name = path.name.lower().removesuffix(".gz")
    suffix = Path(name).suffix
    with _open_text(path) as f:
        if suffix in {".jsonl", ".ndjson"}:
            for line_no, line in enumerate(f, 1):
                if line.strip():
                    try:
                        yield line_no, _to_text(json.loads(line))
                    except json.JSONDecodeError:
                        yield line_no, _to_text(line)
        elif suffix == ".csv":
            reader = csv.DictReader(f)
            for row_no, row in enumerate(reader, 2):
                yield row_no, _to_text(row)
        elif suffix == ".json":
            # JSON arrays/objects can be big; standard parser is acceptable only for
            # moderate files. JSONL is the recommended path for very large datasets.
            data = json.load(f)
            if isinstance(data, list):
                for i, item in enumerate(data, 1):
                    yield i, _to_text(item)
            else:
                yield 1, _to_text(data)
        elif suffix in {".html", ".htm"}:
            parser = _HTMLText()
            for block in iter(lambda: f.read(65536), ""):
                parser.feed(block)
            yield 1, _to_text("\n".join(parser.parts))
        else:
            buf, line_no = [], 0
            for line_no, line in enumerate(f, 1):
                buf.append(line)
                if sum(map(len, buf)) >= 16000:
                    yield line_no, _to_text("".join(buf))
                    buf = []
            if buf:
                yield line_no, _to_text("".join(buf))


def import_local_file(path, topic="local-dataset", home=None, max_records=0):
    """Index one local file. max_records=0 means continue until EOF; reruns deduplicate."""
    p = _safe_file(path, home)
    digest = hashlib.sha256()
    with p.open("rb") as raw:
        for block in iter(lambda: raw.read(1024 * 1024), b""):
            digest.update(block)
    file_hash = digest.hexdigest()
    source_url = "local://" + file_hash
    db_path = _db_path(home)
    indexed = skipped = errors = chars = 0
    with _connect(home) as db:
        db.execute("INSERT OR IGNORE INTO sources(id,url,domain,title,license,status,added_at,fetched_at,content_hash) VALUES(?,?,?,?,?,?,?,?,?)",
                   ("local_" + file_hash[:20], source_url, "local-import", p.name[:300],
                    "user-provided-local-file; reuse terms remain user's responsibility",
                    "indexed", time.time(), time.time(), file_hash))
        source = db.execute("SELECT id FROM sources WHERE url=?", (source_url,)).fetchone()
        source_id = source["id"]
    for ordinal, text in _records(p):
        if max_records and indexed + skipped >= int(max_records):
            break
        text = text.strip()
        if len(text) < 20:
            skipped += 1
            continue
        record_hash = hashlib.sha256((file_hash + ":" + str(ordinal) + ":" + text).encode("utf-8")).hexdigest()
        title = f"{p.name} · record {ordinal}"
        with _connect(home) as db:
            if db.execute("SELECT 1 FROM documents WHERE content_hash=?", (record_hash,)).fetchone():
                skipped += 1
                continue
            doc_id = "doc_" + uuid.uuid4().hex[:16]
            db.execute("INSERT INTO documents(id,source_id,title,text,content_hash,topic,created_at) VALUES(?,?,?,?,?,?,?)",
                       (doc_id, source_id, title[:300], text, record_hash, str(topic)[:120], time.time()))
            for i, chunk in enumerate(_chunks(text)):
                chunk_id = "chk_" + uuid.uuid4().hex[:16]
                db.execute("INSERT INTO chunks(id,document_id,ordinal,text) VALUES(?,?,?,?)",
                           (chunk_id, doc_id, i, chunk))
                db.execute("INSERT INTO chunks_fts(chunk_id,text) VALUES(?,?)", (chunk_id, chunk))
        indexed += 1
        chars += len(text)
    return {"file": str(p), "sha256": file_hash, "indexed_records": indexed,
            "skipped_or_duplicate": skipped, "errors": errors, "characters": chars,
            "database": str(db_path), "note": "Large datasets: prefer .jsonl.gz; each record is processed incrementally. File remains on device."}
