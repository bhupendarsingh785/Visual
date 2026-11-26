"""Durable Planner -> Coder -> Tester -> Security Reviewer workflow."""
import json
from autonomous_development_engine import _db, _task, _event, get_task, transition, validate_artifacts, workspace_fingerprint

ROLES = ("planner", "coder", "tester", "security_reviewer")
MAX_CYCLES = 5

def start(task_id, home=None):
    t = get_task(task_id, home)
    if t["status"] == "queued":
        transition(task_id, "planning", "orchestrated workflow started", home=home)
    with _db(home) as db:
        _task(db, task_id)
        row = db.execute("SELECT detail FROM events WHERE task_id=? AND event='orchestration' ORDER BY id DESC LIMIT 1", (task_id,)).fetchone()
        if row:
            return json.loads(row["detail"])
        state = {"role": "planner", "cycle": 0, "status": "running", "workspace_sha256": None}
        _event(db, task_id, "orchestrator", "orchestration", json.dumps(state))
        return state

def current(task_id, home=None):
    with _db(home) as db:
        _task(db, task_id)
        row = db.execute("SELECT detail FROM events WHERE task_id=? AND event='orchestration' ORDER BY id DESC LIMIT 1", (task_id,)).fetchone()
        return json.loads(row["detail"]) if row else None

def record(task_id, role, outcome, notes="", home=None):
    if role not in ROLES or outcome not in {"pass", "revise", "fail", "blocked"}:
        raise ValueError("invalid role or outcome")
    state = current(task_id, home)
    if not state or state["status"] != "running" or state["role"] != role:
        raise ValueError("role is not the active workflow stage")
    t = get_task(task_id, home)
    if role == "planner" and outcome == "pass":
        if t["status"] == "planning":
            transition(task_id, "designing", "planner plan recorded", home=home)
        state["role"] = "coder"
    elif role == "coder" and outcome == "pass":
        if t["status"] in {"planning", "designing"}:
            if t["status"] == "planning":
                transition(task_id, "designing", "plan accepted", home=home)
            transition(task_id, "implementing", "coder implementation recorded", home=home)
        state["role"] = "tester"
    elif role == "tester":
        if outcome == "pass":
            validation = validate_artifacts(task_id, home)
            if validation.get("errors") or not validation.get("files"):
                outcome = "revise"
                notes = (str(notes) + "\nStatic validation failed or no artifacts: " + "; ".join(validation.get("errors", [])[:5]))[:2500]
            else:
                state["workspace_sha256"] = workspace_fingerprint(task_id, home)
                state["role"] = "security_reviewer"
        if outcome in {"revise", "fail", "blocked"}:
            state["cycle"] += 1
            state["role"] = "coder" if state["cycle"] < MAX_CYCLES else "blocked"
            if state["role"] == "blocked": state["status"] = "blocked"
    elif role == "security_reviewer":
        if outcome == "pass":
            if t["status"] == "implementing":
                transition(task_id, "validating", "security review accepted; final validation", home=home)
            validation = validate_artifacts(task_id, home)
            digest = workspace_fingerprint(task_id, home)
            if validation.get("errors") or not validation.get("files") or digest != state.get("workspace_sha256"):
                state["cycle"] += 1
                state["role"] = "coder"
                state["workspace_sha256"] = None
                outcome = "revise"
                notes = (str(notes) + "\nFinal validation/hash mismatch; rerun tester and security review.")[:2500]
            else:
                state["status"], state["role"], state["workspace_sha256"] = "awaiting_owner_approval", "owner", digest
        else:
            state["cycle"] += 1
            state["role"] = "coder" if state["cycle"] < MAX_CYCLES else "blocked"
            if state["role"] == "blocked": state["status"] = "blocked"
    with _db(home) as db:
        _event(db, task_id, role, "role_result", json.dumps({"outcome": outcome, "notes": str(notes)[:2500]}))
        _event(db, task_id, "orchestrator", "orchestration", json.dumps(state))
    return state

def approve(task_id, note, actor="owner", home=None):
    if actor != "owner": raise PermissionError("only owner can approve")
    state = current(task_id, home)
    if not state or state["status"] != "awaiting_owner_approval":
        raise ValueError("workflow is not awaiting owner approval")
    if workspace_fingerprint(task_id, home) != state.get("workspace_sha256"):
        raise ValueError("workspace changed after review; rerun tester and security reviewer")
    t = get_task(task_id, home)
    if t["status"] == "validating":
        transition(task_id, "awaiting_approval", "orchestration evidence complete", home=home)
    transition(task_id, "completed", note, actor="owner", home=home)
    state.update(status="completed", role="done")
    with _db(home) as db: _event(db, task_id, "owner", "orchestration", json.dumps(state))
    return state
