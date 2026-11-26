"""Persistent, privacy-conscious self-intelligence ledger for VISUAL.

This module observes the running installation and records auditable improvement
proposals. It never edits executable source or grants itself permissions.
"""
import hashlib
import contextlib
import json
import os
import re
import sqlite3
import time
import uuid
from pathlib import Path


SCHEMA_VERSION = 1
_SECRET = re.compile(r"(api[_-]?key|token|password|secret|credential)", re.I)
_SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}


def _db_path(home=None):
    root = Path(home or os.environ.get("VISUAL_HOME") or Path.home() / ".visual")
    root.mkdir(parents=True, exist_ok=True)
    return root / "self_intelligence.sqlite3"


@contextlib.contextmanager
def _db(home=None):
    conn = _connect(home)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _connect(home=None):
    db = sqlite3.connect(str(_db_path(home)), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY, value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS snapshots (
        id TEXT PRIMARY KEY, created_at REAL NOT NULL, payload TEXT NOT NULL,
        digest TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS findings (
        id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL, severity TEXT NOT NULL,
        area TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
        FOREIGN KEY(snapshot_id) REFERENCES snapshots(id)
    );
    CREATE TABLE IF NOT EXISTS improvement_plans (
        id TEXT PRIMARY KEY, created_at REAL NOT NULL, updated_at REAL NOT NULL,
        status TEXT NOT NULL, title TEXT NOT NULL, scope TEXT NOT NULL,
        rationale TEXT NOT NULL, risk TEXT NOT NULL, acceptance TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT ''
    );
    CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(created_at);
    CREATE INDEX IF NOT EXISTS idx_plans_status ON improvement_plans(status, updated_at);
    """)
    db.execute("INSERT OR IGNORE INTO metadata(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
    return db


def _safe_file_inventory(root, max_files=12000):
    root = Path(root)
    files, skipped = [], 0
    if not root.exists():
        return {"count": 0, "files": [], "truncated": False}
    for base, dirs, names in os.walk(str(root)):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in names:
            path = Path(base) / name
            try:
                rel = str(path.relative_to(root))
                if _SECRET.search(name):
                    skipped += 1
                    continue
                st = path.stat()
                if not path.is_file():
                    continue
                files.append({"path": rel, "size": st.st_size, "mtime": int(st.st_mtime)})
                if len(files) >= max_files:
                    return {"count": len(files), "files": files, "truncated": True, "secret_named_skipped": skipped}
            except (OSError, ValueError):
                skipped += 1
    files.sort(key=lambda x: x["path"])
    return {"count": len(files), "files": files, "truncated": False, "secret_named_skipped": skipped}


def collect_snapshot(context=None):
    context = context or {}
    root = Path(context.get("root") or os.environ.get("VISUAL_ROOT") or Path.cwd()).resolve()
    providers = context.get("providers") or {}
    tasks = context.get("tasks") or {}
    tools = context.get("tools") or {}
    plugins = context.get("plugins") or {}
    plugin_errors = context.get("plugin_errors") or {}
    cfg = context.get("config") or {}
    provider_status = {}
    for name, meta in providers.items():
        provider_status[name] = {
            "configured": bool((cfg.get("keys") or {}).get(name)),
            "vision": bool(meta.get("vision")),
            "tools": bool(meta.get("tools")),
            "model_configured": bool((cfg.get("models") or {}).get(name) or meta.get("model")),
        }
    task_status = {}
    for tid, task in tasks.items():
        state = str(task.get("status", "unknown"))
        task_status[state] = task_status.get(state, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": time.time(),
        "app_root": str(root),
        "runtime": {"python": context.get("python", ""), "platform": context.get("platform", "")},
        "tool_count": len(tools),
        "tool_names": sorted(str(k) for k in tools),
        "plugins": sorted(str(k) for k in plugins),
        "plugin_errors": {str(k): str(v)[:500] for k, v in plugin_errors.items()},
        "providers": provider_status,
        "task_status_counts": task_status,
        "file_inventory": _safe_file_inventory(root),
        "config_profile": {
            "language": cfg.get("language", ""),
            "live_mode": bool(cfg.get("live_mode")),
            "confirm_risky": bool(cfg.get("confirm_risky", True)),
            "provider_count": len(providers),
        },
    }


def assess_snapshot(snapshot):
    findings = []
    errors = snapshot.get("plugin_errors") or {}
    if errors:
        findings.append(("high", "plugins", "Plugin load errors present", json.dumps(errors, ensure_ascii=False)[:1000]))
    if snapshot.get("tool_count", 0) == 0:
        findings.append(("critical", "tools", "No tools registered", "The runtime reported an empty tool registry."))
    if not snapshot.get("providers"):
        findings.append(("high", "providers", "No provider adapters discovered", "No provider definitions were visible to the self-intelligence observer."))
    if not snapshot.get("file_inventory", {}).get("count"):
        findings.append(("medium", "inventory", "Repository inventory is empty", "Check the configured app root and filesystem permissions."))
    if snapshot.get("file_inventory", {}).get("truncated"):
        findings.append(("low", "inventory", "Repository inventory reached its safety limit", "Inventory is capped to avoid unbounded scans."))
    failed_tasks = snapshot.get("task_status_counts", {}).get("fail", 0) + snapshot.get("task_status_counts", {}).get("failed", 0)
    if failed_tasks:
        findings.append(("medium", "agents", "Failed agent tasks are recorded", str(failed_tasks) + " failed tasks were visible at snapshot time."))
    if not snapshot.get("config_profile", {}).get("confirm_risky", True):
        findings.append(("high", "security", "Risky-action confirmation is disabled", "Review whether this setting is intentional before enabling device or external actions."))
    if not findings:
        findings.append(("info", "health", "No deterministic self-audit findings", "This is a static runtime inventory, not proof that every feature works."))
    return findings


def save_snapshot(snapshot, findings, home=None):
    sid = "s" + uuid.uuid4().hex[:12]
    payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    with _db(home) as db:
        db.execute("INSERT INTO snapshots(id,created_at,payload,digest) VALUES(?,?,?,?)",
                   (sid, time.time(), payload, digest))
        db.executemany(
            "INSERT INTO findings(id,snapshot_id,severity,area,title,detail) VALUES(?,?,?,?,?,?)",
            [(uuid.uuid4().hex[:12], sid, *f) for f in findings],
        )
    return {"snapshot_id": sid, "digest": digest, "findings": len(findings)}


def latest_report(home=None):
    with _connect(home) as db:
        rows = db.execute("SELECT * FROM snapshots ORDER BY created_at DESC LIMIT 2").fetchall()
        if not rows:
            return {"snapshot": None, "findings": [], "plans": [], "change_summary": None}
        row = rows[0]
        snapshot = json.loads(row["payload"])
        previous = json.loads(rows[1]["payload"]) if len(rows) > 1 else None
        change_summary = None
        if previous is not None:
            old = {x["path"]: (x.get("size"), x.get("mtime")) for x in previous.get("file_inventory", {}).get("files", [])}
            new = {x["path"]: (x.get("size"), x.get("mtime")) for x in snapshot.get("file_inventory", {}).get("files", [])}
            change_summary = {
                "added": sorted(set(new) - set(old))[:500],
                "removed": sorted(set(old) - set(new))[:500],
                "changed": sorted(k for k in set(old) & set(new) if old[k] != new[k])[:500],
                "truncated": bool(previous.get("file_inventory", {}).get("truncated") or snapshot.get("file_inventory", {}).get("truncated")),
            }
        findings = [dict(x) for x in db.execute(
            "SELECT severity,area,title,detail FROM findings WHERE snapshot_id=? ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END",
            (row["id"],))]
        plans = [dict(x) for x in db.execute(
            "SELECT id,status,title,scope,rationale,risk,acceptance,updated_at FROM improvement_plans ORDER BY updated_at DESC LIMIT 20")]
        return {"snapshot": {"id": row["id"], "created_at": row["created_at"], "digest": row["digest"], "data": snapshot},
                "findings": findings, "plans": plans, "change_summary": change_summary}


def create_plan(title, scope, rationale, risk, acceptance, home=None):
    values = [str(x).strip() for x in (title, scope, rationale, risk, acceptance)]
    if any(not x for x in values):
        raise ValueError("title, scope, rationale, risk and acceptance are all required")
    if len(values[0]) > 180 or len(values[1]) > 1200 or len(values[2]) > 2000 or len(values[3]) > 500 or len(values[4]) > 2000:
        raise ValueError("plan field exceeds safe length")
    pid = "p" + uuid.uuid4().hex[:12]
    now = time.time()
    with _connect(home) as db:
        db.execute("INSERT INTO improvement_plans(id,created_at,updated_at,status,title,scope,rationale,risk,acceptance) VALUES(?,?,?,?,?,?,?,?,?)",
                   (pid, now, now, "proposed", *values))
    return pid


def update_plan(plan_id, status, notes="", home=None):
    allowed = {"proposed", "approved", "in_progress", "needs_review", "rejected"}
    if status == "completed":
        raise ValueError("completion is reserved for an independent verifier; a planning tool cannot self-certify")
    if status not in allowed:
        raise ValueError("status must be one of: " + ", ".join(sorted(allowed)))
    with _connect(home) as db:
        row = db.execute("SELECT id FROM improvement_plans WHERE id=?", (plan_id,)).fetchone()
        if not row:
            raise KeyError("unknown improvement plan id")
        db.execute("UPDATE improvement_plans SET status=?,updated_at=?,notes=? WHERE id=?",
                   (status, time.time(), str(notes)[:3000], plan_id))
    return plan_id


def plan_history(home=None, limit=20):
    limit = max(1, min(int(limit), 100))
    with _connect(home) as db:
        return [dict(x) for x in db.execute(
            "SELECT id,status,title,scope,rationale,risk,acceptance,notes,created_at,updated_at FROM improvement_plans ORDER BY updated_at DESC LIMIT ?",
            (limit,))]
