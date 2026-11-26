"""VISUAL public knowledge base: local-first, provenance-aware, deduplicated research store.

Only explicitly submitted public URLs are fetched. No recursive crawling. SQLite + FTS5
keeps the index on-device; storage is bounded by the device, not by an imaginary unlimited quota.
"""
import hashlib
import html
import ipaddress
import json
import re
import socket
import sqlite3
import time
import urllib.parse
import urllib.request
import urllib.robotparser
import uuid
from html.parser import HTMLParser
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
CHUNK_CHARS = 1800
CHUNK_OVERLAP = 180
USER_AGENT = "VISUAL-KnowledgeBot/1.0 (+user-initiated public-source indexing)"
SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header"}
SECRET_RE = re.compile(r"(?i)(api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*[^\s<]{8,}")

class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in SKIP_TAGS: self.skip += 1
    def handle_endtag(self, tag):
        if tag.lower() in SKIP_TAGS and self.skip: self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            value = " ".join(data.split())
            if value: self.parts.append(value)

def _db_path(home=None):
    root = Path(home or Path.home() / ".visual")
    root.mkdir(parents=True, exist_ok=True)
    return root / "knowledge.sqlite3"

def _connect(home=None):
    db = sqlite3.connect(str(_db_path(home)), timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS sources(
      id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, domain TEXT NOT NULL,
      title TEXT NOT NULL DEFAULT '', license TEXT NOT NULL DEFAULT 'unknown',
      status TEXT NOT NULL, added_at REAL NOT NULL, fetched_at REAL,
      etag TEXT, last_modified TEXT, content_hash TEXT, error TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS documents(
      id TEXT PRIMARY KEY, source_id TEXT NOT NULL, title TEXT NOT NULL,
      text TEXT NOT NULL, content_hash TEXT UNIQUE NOT NULL, language TEXT NOT NULL DEFAULT 'unknown',
      topic TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL,
      FOREIGN KEY(source_id) REFERENCES sources(id)
    );
    CREATE TABLE IF NOT EXISTS chunks(
      id TEXT PRIMARY KEY, document_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
      text TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES documents(id),
      UNIQUE(document_id, ordinal)
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, text, tokenize='unicode61');
    CREATE INDEX IF NOT EXISTS idx_sources_domain ON sources(domain);
    CREATE INDEX IF NOT EXISTS idx_documents_topic ON documents(topic);
    """)
    return db

def _public_url(url):
    p = urllib.parse.urlsplit(str(url).strip())
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Sirf credential-free HTTPS public URLs allowed hain.")
    host = p.hostname.encode("idna").decode("ascii")
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("Host resolve nahi hua: " + str(exc))
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if not ip.is_global:
            raise ValueError("Private, local ya reserved network address blocked.")
    clean = urllib.parse.urlunsplit(("https", host, p.path or "/", p.query, ""))
    return clean, host

def _robots_allowed(url):
    parts = urllib.parse.urlsplit(url)
    robots = urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots)
    try: parser.read()
    except Exception: return False
    return parser.can_fetch(USER_AGENT, url)

def _extract(raw, content_type):
    charset = "utf-8"
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m: charset = m.group(1)
    decoded = raw.decode(charset, errors="replace")
    if "html" in (content_type or "").lower() or re.search(r"<html|<!doctype", decoded[:500], re.I):
        parser = _Text()
        parser.feed(decoded)
        decoded = "\n".join(parser.parts)
    decoded = html.unescape(decoded)
    decoded = SECRET_RE.sub("[REDACTED_SECRET]", decoded)
    return re.sub(r"\n{3,}", "\n\n", decoded).strip()

def _chunks(text):
    text = re.sub(r"[ \t]+", " ", text)
    out, pos = [], 0
    while pos < len(text):
        end = min(len(text), pos + CHUNK_CHARS)
        if end < len(text):
            boundary = text.rfind(" ", pos + CHUNK_CHARS // 2, end)
            if boundary > pos: end = boundary
        piece = text[pos:end].strip()
        if piece: out.append(piece)
        if end >= len(text): break
        pos = max(pos + 1, end - CHUNK_OVERLAP)
    return out

def add_source(url, license="unknown", topic="general", home=None):
    clean, domain = _public_url(url)
    if len(license) > 100 or len(topic) > 120: raise ValueError("Metadata bahut lamba hai.")
    sid = "src_" + uuid.uuid4().hex[:16]
    with _connect(home) as db:
        db.execute("INSERT OR IGNORE INTO sources(id,url,domain,license,status,added_at) VALUES(?,?,?,?,?,?)",
                   (sid, clean, domain, str(license)[:100], "queued", time.time()))
        row = db.execute("SELECT id,status FROM sources WHERE url=?", (clean,)).fetchone()
    return {"source_id": row["id"], "status": row["status"], "url": clean}

def ingest_source(source_id, home=None):
    with _connect(home) as db:
        src = db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if not src: raise KeyError("Unknown source_id")
        url = src["url"]
    if not _robots_allowed(url):
        with _connect(home) as db: db.execute("UPDATE sources SET status='blocked',error=? WHERE id=?", ("robots.txt disallows or unavailable", source_id))
        return {"status":"blocked","reason":"robots.txt"}
    req = urllib.request.Request(url, headers={"User-Agent":USER_AGENT, "Accept":"text/html,text/plain,application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            ctype = response.headers.get("Content-Type", "")
            if not any(x in ctype.lower() for x in ("text/", "json", "xml")):
                raise ValueError("Unsupported content type: " + ctype)
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES: raise ValueError("Page exceeds 2 MiB safety limit")
            title = response.headers.get("X-Page-Title") or urllib.parse.urlsplit(url).path.rsplit("/",1)[-1] or src["domain"]
            text = _extract(raw, ctype)
            etag, modified = response.headers.get("ETag"), response.headers.get("Last-Modified")
    except Exception as exc:
        with _connect(home) as db: db.execute("UPDATE sources SET status='error',error=? WHERE id=?", (str(exc)[:500], source_id))
        raise
    if len(text) < 80: raise ValueError("Readable content bahut kam mila; page ko index nahi kiya.")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    with _connect(home) as db:
        existing = db.execute("SELECT id FROM documents WHERE content_hash=?", (digest,)).fetchone()
        if not existing:
            did = "doc_" + uuid.uuid4().hex[:16]
            db.execute("INSERT INTO documents(id,source_id,title,text,content_hash,topic,created_at) VALUES(?,?,?,?,?,?,?)",
                       (did, source_id, title[:300], text, digest, "general", time.time()))
            for i, chunk in enumerate(_chunks(text)):
                cid = "chk_" + uuid.uuid4().hex[:16]
                db.execute("INSERT INTO chunks(id,document_id,ordinal,text) VALUES(?,?,?,?)",(cid,did,i,chunk))
                db.execute("INSERT INTO chunks_fts(chunk_id,text) VALUES(?,?)",(cid,chunk))
        else: did = existing["id"]
        db.execute("UPDATE sources SET status='indexed',fetched_at=?,etag=?,last_modified=?,content_hash=?,error='' WHERE id=?",
                   (time.time(),etag,modified,digest,source_id))
    return {"status":"indexed","document_id":did,"characters":len(text),"duplicate":bool(existing),"sha256":digest}

def search_knowledge(query, limit=8, home=None):
    query = str(query).strip()
    if not query: raise ValueError("Search query required")
    terms = re.findall(r"[\w.-]{2,}", query)[:12]
    if not terms: return []
    match = " OR ".join('"' + t.replace('"','') + '"' for t in terms)
    limit = max(1,min(int(limit),20))
    with _connect(home) as db:
        rows = db.execute("""SELECT c.text,d.title,d.topic,s.url,s.license,s.domain,
          bm25(chunks_fts) AS rank FROM chunks_fts
          JOIN chunks c ON c.id=chunks_fts.chunk_id
          JOIN documents d ON d.id=c.document_id
          JOIN sources s ON s.id=d.source_id
          WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?""",(match,limit)).fetchall()
    return [dict(x) for x in rows]

def knowledge_stats(home=None):
    with _connect(home) as db:
        return { "sources":db.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
          "indexed_sources":db.execute("SELECT COUNT(*) FROM sources WHERE status='indexed'").fetchone()[0],
          "documents":db.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
          "chunks":db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
          "db_bytes":_db_path(home).stat().st_size if _db_path(home).exists() else 0,
          "storage_note":"Local device storage is finite; export/backup or attach larger storage for growth." }
