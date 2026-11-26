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
import urllib.error
import uuid
from html.parser import HTMLParser
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
CHUNK_CHARS = 1800
CHUNK_OVERLAP = 180
USER_AGENT = "VISUAL-KnowledgeBot/1.0 (+user-initiated public-source indexing)"
SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header"}
SECRET_RE = re.compile(r"(?i)(api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*[^\s<]{8,}")

class _ClosingConnection(sqlite3.Connection):
    """Commit/rollback and always close SQLite handles when used with 'with'."""
    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()

class _PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow redirects only when the destination remains public HTTPS."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        clean, _ = _public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, clean)

def _open_public(req, timeout):
    # Re-resolve and validate immediately before every outbound request, not only
    # when a source is first queued. Redirect destinations are checked separately.
    _public_url(req.full_url)
    opener = urllib.request.build_opener(_PublicRedirectHandler())
    return opener.open(req, timeout=timeout)

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
    db = sqlite3.connect(str(_db_path(home)), timeout=20, factory=_ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS sources(
      id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL, domain TEXT NOT NULL,
      title TEXT NOT NULL DEFAULT '', license TEXT NOT NULL DEFAULT 'unknown',
      topic TEXT NOT NULL DEFAULT 'general', status TEXT NOT NULL, added_at REAL NOT NULL, fetched_at REAL,
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
    columns = {row[1] for row in db.execute("PRAGMA table_info(sources)")}
    if "topic" not in columns:
        db.execute("ALTER TABLE sources ADD COLUMN topic TEXT NOT NULL DEFAULT 'general'")
    return db

def _public_url(url):
    p = urllib.parse.urlsplit(str(url).strip())
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise ValueError("Sirf credential-free HTTPS public URLs allowed hain.")
    try:
        port = p.port
    except ValueError as exc:
        raise ValueError("Invalid HTTPS port.") from exc
    if port not in (None, 443):
        raise ValueError("Only standard HTTPS port 443 is allowed.")
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
    """Check robots.txt with a hard network timeout; fail closed on network errors."""
    parts = urllib.parse.urlsplit(url)
    robots = urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots)
    request = urllib.request.Request(robots, headers={"User-Agent": USER_AGENT})
    try:
        with _open_public(request, timeout=8) as response:
            raw = response.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024:
                return False
            parser.parse(raw.decode("utf-8", errors="replace").splitlines())
    except urllib.error.HTTPError as exc:
        # A missing robots.txt means there are no published crawl restrictions.
        if exc.code == 404:
            parser.parse([])
        else:
            return False
    except Exception:
        return False
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
    license = str(license or "unknown")
    topic = str(topic or "general")
    if len(license) > 100 or len(topic) > 120: raise ValueError("Metadata bahut lamba hai.")
    sid = "src_" + uuid.uuid4().hex[:16]
    with _connect(home) as db:
        db.execute("INSERT OR IGNORE INTO sources(id,url,domain,license,topic,status,added_at) VALUES(?,?,?,?,?,?,?)",
                   (sid, clean, domain, license[:100], topic[:120], "queued", time.time()))
        row = db.execute("SELECT id,status FROM sources WHERE url=?", (clean,)).fetchone()
    return {"source_id": row["id"], "status": row["status"], "url": clean}

def ingest_source(source_id, home=None, respect_robots=True):
    with _connect(home) as db:
        src = db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if not src: raise KeyError("Unknown source_id")
        url = src["url"]
    # Explicit allowlisted APIs follow their API terms/rate limits; website-page ingestion still checks robots.txt.
    if respect_robots and not _robots_allowed(url):
        with _connect(home) as db: db.execute("UPDATE sources SET status='blocked',error=? WHERE id=?", ("robots.txt disallows or unavailable", source_id))
        return {"status":"blocked","reason":"robots.txt"}
    req = urllib.request.Request(url, headers={"User-Agent":USER_AGENT, "Accept":"text/html,text/plain,application/json"})
    try:
        with _open_public(req, timeout=15) as response:
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
    if len(text) < 80:
        with _connect(home) as db:
            db.execute("UPDATE sources SET status='error',error=? WHERE id=?",
                       ("Readable content bahut kam mila; page ko index nahi kiya.", source_id))
        raise ValueError("Readable content bahut kam mila; page ko index nahi kiya.")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    with _connect(home) as db:
        existing = db.execute("SELECT id FROM documents WHERE content_hash=?", (digest,)).fetchone()
        if not existing:
            did = "doc_" + uuid.uuid4().hex[:16]
            db.execute("INSERT INTO documents(id,source_id,title,text,content_hash,topic,created_at) VALUES(?,?,?,?,?,?,?)",
                       (did, source_id, title[:300], text, digest, src["topic"], time.time()))
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
        stats = {
            "sources": db.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "indexed_sources": db.execute("SELECT COUNT(*) FROM sources WHERE status='indexed'").fetchone()[0],
            "documents": db.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
            "chunks": db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
            "source_status_counts": {row["status"]: row["count"] for row in
                                     db.execute("SELECT status,COUNT(*) AS count FROM sources GROUP BY status")},
            "document_topic_counts": {row["topic"]: row["count"] for row in
                                      db.execute("SELECT topic,COUNT(*) AS count FROM documents GROUP BY topic ORDER BY count DESC")},
        }
    path = _db_path(home)
    stats["db_bytes"] = sum(p.stat().st_size for p in
                            (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")) if p.exists())
    stats["storage_note"] = "Local device storage is finite; export/backup or attach larger storage for growth."
    return stats


def collect_queued(limit=10, home=None):
    """Fetch a bounded batch of already queued public sources; never crawls links recursively."""
    limit = max(1, min(int(limit), 30))
    with _connect(home) as db:
        rows = db.execute("SELECT id,url FROM sources WHERE status IN ('queued','error') ORDER BY added_at LIMIT ?", (limit,)).fetchall()
    results = []
    for row in rows:
        try:
            results.append({"source_id": row["id"], "url": row["url"], **ingest_source(row["id"], home)})
        except Exception as exc:
            results.append({"source_id": row["id"], "url": row["url"], "status": "error", "error": str(exc)[:240]})
        time.sleep(1.0)
    return {"processed": len(results), "results": results, "stats": knowledge_stats(home),
            "note": "Batch limited to 30 sources; robots.txt, HTTPS, public-IP and 2 MiB/page limits apply."}
