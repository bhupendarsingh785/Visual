"""Durable, approval-aware development workspace for VISUAL.

This module manages task state, research provenance, source artifacts and static
validation. It does not execute generated code or modify the live VISUAL install.
"""
import ast
import contextlib
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

SCHEMA_VERSION = 1
STATUSES = {"queued", "planning", "researching", "designing", "implementing",
            "validating", "awaiting_approval", "completed", "failed", "cancelled"}
_TRANSITIONS = {
    "queued": {"planning", "cancelled", "failed"},
    "planning": {"researching", "designing", "implementing", "failed", "cancelled"},
    "researching": {"designing", "implementing", "failed", "cancelled"},
    "designing": {"implementing", "failed", "cancelled"},
    "implementing": {"validating", "failed", "cancelled"},
    "validating": {"implementing", "awaiting_approval", "failed", "cancelled"},
    "awaiting_approval": {"implementing", "completed", "failed", "cancelled"},
    "completed": set(), "failed": {"planning", "cancelled"}, "cancelled": set(),
}
_SECRET = re.compile(r"(AIza[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|gsk_[A-Za-z0-9]{30,}|nvapi-[A-Za-z0-9_-]{30,}|hf_[A-Za-z0-9]{30,})")
_MAX_FILE = 1_000_000
_MAX_TOTAL = 12_000_000


def _root(home=None):
    base = Path(home or os.environ.get("VISUAL_HOME") or Path.home() / ".visual").expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def _connect(home=None):
    db = sqlite3.connect(str(_root(home) / "development.sqlite3"), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS tasks(
      id TEXT PRIMARY KEY, title TEXT NOT NULL, goal TEXT NOT NULL, kind TEXT NOT NULL,
      status TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
      notes TEXT NOT NULL DEFAULT '', workspace TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, at REAL NOT NULL,
      actor TEXT NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL,
      FOREIGN KEY(task_id) REFERENCES tasks(id)
    );
    CREATE TABLE IF NOT EXISTS research(
      id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, at REAL NOT NULL,
      url TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL, evidence TEXT NOT NULL,
      FOREIGN KEY(task_id) REFERENCES tasks(id)
    );
    CREATE TABLE IF NOT EXISTS artifacts(
      task_id TEXT NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL,
      size INTEGER NOT NULL, updated_at REAL NOT NULL,
      PRIMARY KEY(task_id,path), FOREIGN KEY(task_id) REFERENCES tasks(id)
    );
    CREATE INDEX IF NOT EXISTS idx_dev_tasks_status ON tasks(status,updated_at);
    CREATE INDEX IF NOT EXISTS idx_dev_events_task ON events(task_id,at);
    """)
    db.execute("INSERT OR IGNORE INTO tasks(id,title,goal,kind,status,created_at,updated_at,workspace) VALUES('__schema__','schema','schema','system','completed',0,0,'')")
    return db


@contextlib.contextmanager
def _db(home=None):
    db = _connect(home)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _task(db, task_id):
    row = db.execute("SELECT * FROM tasks WHERE id=?", (str(task_id),)).fetchone()
    if not row or row["id"] == "__schema__":
        raise KeyError("development task nahi mila")
    return dict(row)


def _event(db, task_id, actor, event, detail=""):
    db.execute("INSERT INTO events(task_id,at,actor,event,detail) VALUES(?,?,?,?,?)",
               (task_id, time.time(), actor[:60], event[:80], detail[:3000]))


def create_task(title, goal, kind="build", home=None):
    title, goal, kind = str(title).strip(), str(goal).strip(), str(kind).strip().lower()
    if not title or not goal:
        raise ValueError("title aur goal zaroori hain")
    if len(title) > 180 or len(goal) > 6000 or kind not in {"build","upgrade","debug","research","tool"}:
        raise ValueError("title/goal bahut lamba hai ya kind galat hai")
    tid = "d" + uuid.uuid4().hex[:12]
    ws = _root(home) / "development" / tid
    ws.mkdir(parents=True, exist_ok=False)
    now = time.time()
    with _db(home) as db:
        db.execute("INSERT INTO tasks(id,title,goal,kind,status,created_at,updated_at,workspace) VALUES(?,?,?,?,?,?,?,?)",
                   (tid,title,goal,kind,"queued",now,now,str(ws)))
        _event(db,tid,"owner","created",f"{kind}: {title}")
    return {"id":tid,"status":"queued","workspace":str(ws)}


def get_task(task_id, home=None):
    with _db(home) as db:
        t = _task(db,task_id)
        t["events"] = [dict(x) for x in db.execute("SELECT at,actor,event,detail FROM events WHERE task_id=? ORDER BY id DESC LIMIT 30",(task_id,))]
        t["research"] = [dict(x) for x in db.execute("SELECT at,url,title,summary,evidence FROM research WHERE task_id=? ORDER BY id",(task_id,))]
        t["artifacts"] = [dict(x) for x in db.execute("SELECT path,sha256,size,updated_at FROM artifacts WHERE task_id=? ORDER BY path",(task_id,))]
        return t


def list_tasks(home=None, limit=30):
    limit = max(1,min(int(limit),100))
    with _db(home) as db:
        return [dict(x) for x in db.execute("SELECT id,title,kind,status,created_at,updated_at FROM tasks WHERE id!='__schema__' ORDER BY updated_at DESC LIMIT ?",(limit,))]


def transition(task_id, status, notes="", actor="agent", home=None):
    status = str(status).strip().lower()
    if status not in STATUSES:
        raise ValueError("unknown status")
    with _db(home) as db:
        t = _task(db,task_id)
        if status == "completed" and actor != "owner":
            raise PermissionError("sirf owner approval completed status de sakta hai")
        if status == "awaiting_approval":
            last = db.execute("SELECT detail FROM events WHERE task_id=? AND event='static_validation' ORDER BY id DESC LIMIT 1",(task_id,)).fetchone()
            if not last or not json.loads(last["detail"]).get("ok"):
                raise ValueError("approval se pehle successful static validation zaroori hai")
        if status == "completed" and t["status"] != "awaiting_approval":
            raise ValueError("owner approval se pehle task awaiting_approval hona chahiye")
        if status not in _TRANSITIONS[t["status"]]:
            raise ValueError(f"invalid transition: {t['status']} -> {status}")
        db.execute("UPDATE tasks SET status=?,updated_at=?,notes=? WHERE id=?",
                   (status,time.time(),str(notes)[:3000],task_id))
        _event(db,task_id,actor,"status",f"{t['status']} -> {status}; {str(notes)[:1800]}")
    return status


def add_research(task_id, url, title, summary, evidence="", home=None):
    u = urlparse(str(url).strip())
    if u.scheme != "https" or not u.netloc or len(summary) > 6000 or len(evidence) > 4000:
        raise ValueError("research ke liye valid HTTPS URL aur bounded evidence zaroori hai")
    with _db(home) as db:
        _task(db,task_id)
        db.execute("INSERT INTO research(task_id,at,url,title,summary,evidence) VALUES(?,?,?,?,?,?)",
                   (task_id,time.time(),url[:1500],str(title)[:300],str(summary),str(evidence)))
        _event(db,task_id,"agent","research_added",str(title)[:250])
    return True


def _workspace(task_id, home=None):
    with _db(home) as db:
        t = _task(db,task_id)
    ws = Path(t["workspace"]).resolve()
    base = (_root(home) / "development").resolve()
    if not ws.is_relative_to(base) or ws.is_symlink():
        raise ValueError("workspace boundary violation")
    ws.mkdir(parents=True,exist_ok=True)
    # Non-root container UID needs to traverse the task bind mount; HOME remains private.
    try:
        ws.chmod(0o755)
    except OSError:
        pass
    return ws


def _safe_file(task_id, rel, home=None):
    rel = str(rel).replace("\\","/")
    p = Path(rel)
    if not rel or p.is_absolute() or any(x in ("..","") for x in p.parts) or len(rel)>240:
        raise ValueError("unsafe relative path")
    ws = _workspace(task_id,home)
    target = ws.joinpath(*p.parts)
    # Reject symlinks in every existing path component.
    cur = ws
    for part in p.parts:
        cur = cur / part
        if cur.is_symlink():
            raise ValueError("symlink paths are not allowed")
    resolved = target.resolve()
    if not resolved.is_relative_to(ws):
        raise ValueError("path escapes task workspace")
    return ws,target


def write_artifact(task_id, rel, content, home=None):
    raw = str(content).encode("utf-8")
    if len(raw) > _MAX_FILE:
        raise ValueError("single artifact limit is 1 MB")
    if _SECRET.search(raw.decode("utf-8","ignore")):
        raise ValueError("secret-looking API key/token found; remove it before saving")
    ws,target = _safe_file(task_id,rel,home)
    total = sum(p.stat().st_size for p in ws.rglob("*") if p.is_file() and not p.is_symlink())
    old = target.stat().st_size if target.exists() and target.is_file() else 0
    if total - old + len(raw) > _MAX_TOTAL:
        raise ValueError("task workspace total limit is 12 MB")
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(raw)
    os.replace(tmp,target)
    digest = hashlib.sha256(raw).hexdigest()
    with _db(home) as db:
        _task(db,task_id)
        db.execute("INSERT INTO artifacts(task_id,path,sha256,size,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(task_id,path) DO UPDATE SET sha256=excluded.sha256,size=excluded.size,updated_at=excluded.updated_at",
                   (task_id,str(rel),digest,len(raw),time.time()))
        _event(db,task_id,"agent","artifact_written",f"{rel} sha256={digest}")
    return {"path":str(rel),"size":len(raw),"sha256":digest}


def list_artifacts(task_id, home=None):
    ws = _workspace(task_id,home)
    return sorted(str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file() and not p.is_symlink())


def validate_artifacts(task_id, home=None):
    ws = _workspace(task_id,home)
    report = {"files":0,"python_syntax_ok":0,"json_ok":0,"errors":[],"secret_hits":[]}
    for p in ws.rglob("*"):
        if not p.is_file() or p.is_symlink() or any(x in {".git","node_modules",".venv","__pycache__"} for x in p.parts):
            continue
        if p.stat().st_size > _MAX_FILE:
            report["errors"].append(f"{p.relative_to(ws)}: file exceeds 1 MB")
            continue
        report["files"] += 1
        data = p.read_bytes()
        text = data.decode("utf-8","ignore")
        if _SECRET.search(text):
            report["secret_hits"].append(str(p.relative_to(ws)))
        if p.suffix == ".py":
            try:
                ast.parse(text,filename=str(p)); report["python_syntax_ok"] += 1
            except SyntaxError as e:
                report["errors"].append(f"{p.relative_to(ws)}:{e.lineno}: {e.msg}")
        elif p.suffix == ".json":
            try:
                json.loads(text); report["json_ok"] += 1
            except Exception as e:
                report["errors"].append(f"{p.relative_to(ws)}: invalid JSON: {e}")
    if report["secret_hits"]:
        report["errors"].append("secret-looking token patterns found in: "+", ".join(report["secret_hits"][:20]))
    report["ok"] = not report["errors"]
    with _db(home) as db:
        _task(db,task_id)
        _event(db,task_id,"validator","static_validation",json.dumps(report,ensure_ascii=False)[:2500])
    return report
