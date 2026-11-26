"""Owner-authenticated GitHub issue queue for ChatGPT -> VISUAL phone execution.

The phone is the executor. This bridge intentionally exposes only two read/research
Knowledge Base tools; it is not a shell, general tool proxy, or arbitrary RPC server.
"""
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

BRIDGE_REPO = "bhupendarsingh785/visual-data"
BRIDGE_OWNER = "bhupendarsingh785"
BRIDGE_LABEL = "visual-command"
BRIDGE_STATE = Path(os.path.expanduser("~/.visual/chatgpt_bridge_state.json"))
BRIDGE_ALLOWED = {"knowledge_collect_global_research", "knowledge_status"}
BRIDGE_MAX_OUTPUT = 6000
BRIDGE_POLL_SECONDS = 20
_BRIDGE_STOP = threading.Event()
_BRIDGE_LOCK = threading.RLock()
_BRIDGE_THREAD = None
_BRIDGE_KEY_PAT = re.compile(
    r"(AIza[0-9A-Za-z_-]{30,}|AQ\\.[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|gsk_[A-Za-z0-9]{30,}|"
    r"nvapi-[A-Za-z0-9_-]{30,}|csk-[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,})"
)

def _bridge_cfg():
    return globals().get("CFG", {})

def _bridge_save_state(state):
    BRIDGE_STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = BRIDGE_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, BRIDGE_STATE)
    try:
        os.chmod(BRIDGE_STATE, 0o600)
    except OSError:
        pass

def _bridge_load_state():
    if not BRIDGE_STATE.exists():
        return {"version": 1, "handled": {}, "updated_at": time.time()}
    try:
        state = json.loads(BRIDGE_STATE.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("version") != 1 or not isinstance(state.get("handled"), dict):
            raise ValueError("invalid bridge ledger")
        return state
    except Exception as exc:
        # Fail closed: never reset a corrupt idempotency ledger and replay old commands.
        raise RuntimeError("bridge state corrupt; manual repair required: " + type(exc).__name__)

def _gh(args, timeout=20):
    p = subprocess.run(["gh"] + list(args), capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout or "gh failed").strip()[:500])
    return p.stdout.strip()

def _bridge_check():
    if not shutil_which("gh"):
        raise RuntimeError("GitHub CLI (gh) missing; install gh in Termux.")
    login = _gh(["api", "user", "--jq", ".login"])
    if login.lower() != BRIDGE_OWNER:
        raise RuntimeError("wrong GitHub account; expected owner account " + BRIDGE_OWNER)
    private = _gh(["api", "repos/" + BRIDGE_REPO, "--jq", ".private"])
    if private.lower() != "true":
        raise RuntimeError("queue repository is not private; refusing to use it")
    # Create the queue label once; tolerate only the expected already-exists response.
    try:
        _gh(["api", "repos/" + BRIDGE_REPO + "/labels", "-f", "name=" + BRIDGE_LABEL,
             "-f", "color=1d76db", "-f", "description=Owner-approved VISUAL command queue"], timeout=20)
    except Exception as exc:
        if "already_exists" not in str(exc).lower() and "422" not in str(exc):
            raise
    return {"github_login": login, "repository": BRIDGE_REPO, "private": True}

def shutil_which(name):
    import shutil
    return shutil.which(name)

def _bridge_comment(number, body):
    _gh(["api", "repos/" + BRIDGE_REPO + "/issues/" + str(int(number)) + "/comments",
         "-f", "body=" + body[:BRIDGE_MAX_OUTPUT]], timeout=30)

def _bridge_close(number):
    _gh(["api", "-X", "PATCH", "repos/" + BRIDGE_REPO + "/issues/" + str(int(number)),
         "-f", "state=closed"], timeout=30)

def _bridge_parse(issue):
    labels = {x.get("name") for x in issue.get("labels", []) if isinstance(x, dict)}
    if BRIDGE_LABEL not in labels:
        return None
    if (issue.get("user") or {}).get("login", "").lower() != BRIDGE_OWNER:
        return None
    title = str(issue.get("title") or "")
    if not title.startswith("[VISUAL-CMD]"):
        return None
    body = issue.get("body") or ""
    if len(body) > 4000:
        raise ValueError("command body too large")
    data = json.loads(body)
    if not isinstance(data, dict) or set(data) != {"action", "args", "nonce", "expires_at"}:
        raise ValueError("body must contain exactly action,args,nonce,expires_at")
    action, args = data["action"], data["args"]
    if action not in BRIDGE_ALLOWED or not isinstance(args, dict):
        raise ValueError("action not allowlisted or args invalid")
    nonce = data["nonce"]
    if not isinstance(nonce, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", nonce):
        raise ValueError("nonce must be 16-80 safe characters")
    expires = data["expires_at"]
    if not isinstance(expires, (int, float)) or isinstance(expires, bool):
        raise ValueError("expires_at must be Unix timestamp")
    if expires <= time.time() or expires > time.time() + 86400:
        raise ValueError("command expired or expiry exceeds 24 hours")
    if action == "knowledge_collect_global_research":
        if set(args) - {"topics", "per_request", "max_requests"}:
            raise ValueError("unexpected research argument")
        topics = args.get("topics", "")
        if not isinstance(topics, str) or len(topics) > 1000:
            raise ValueError("invalid topics")
        for key, lo, hi, default in (("per_request", 1, 25, 25), ("max_requests", 1, 300, 300)):
            val = args.get(key, default)
            if not isinstance(val, int) or isinstance(val, bool) or not lo <= val <= hi:
                raise ValueError(key + " outside allowed bounds")
    elif args:
        raise ValueError("knowledge_status takes no arguments")
    return {"action": action, "args": args, "nonce": nonce, "expires_at": expires}

def _bridge_execute(command):
    runner = globals().get("run_tool")
    if not callable(runner):
        raise RuntimeError("VISUAL tool dispatcher unavailable")
    result = runner(command["action"], command["args"])
    # Remove common API-key patterns and keep the issue response bounded.
    return _BRIDGE_KEY_PAT.sub("[REDACTED]", str(result))[:BRIDGE_MAX_OUTPUT]

def _bridge_once():
    _bridge_check()
    state = _bridge_load_state()
    raw = _gh(["api", "repos/" + BRIDGE_REPO + "/issues?state=open&per_page=50"], timeout=30)
    issues = json.loads(raw or "[]")
    processed = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        try:
            command = _bridge_parse(issue)
        except Exception as exc:
            # Malformed owner-authored queue items are closed with a reason, never executed.
            labels = {x.get("name") for x in issue.get("labels", []) if isinstance(x, dict)}
            if BRIDGE_LABEL in labels and (issue.get("user") or {}).get("login", "").lower() == BRIDGE_OWNER:
                _bridge_comment(number, "VISUAL bridge: command rejected (" + type(exc).__name__ + "). No action was run.")
                _bridge_close(number)
                processed.append({"issue": number, "status": "rejected"})
            continue
        if not command:
            continue
        key = str(number)
        if key in state["handled"]:
            continue
        if any(v.get("nonce") == command["nonce"] for v in state["handled"].values()):
            _bridge_comment(number, "VISUAL bridge: duplicate nonce rejected. No action was run.")
            _bridge_close(number)
            processed.append({"issue": number, "status": "rejected_duplicate_nonce"})
            continue
        # Persist before execution: crash after this point is UNKNOWN and is never replayed.
        state["handled"][key] = {"status": "running", "nonce": command["nonce"], "started_at": time.time()}
        _bridge_save_state(state)
        try:
            result = _bridge_execute(command)
            state["handled"][key].update(status="completed", completed_at=time.time())
            _bridge_save_state(state)
            _bridge_comment(number, "VISUAL result (phone-local execution):\\n\\n" + result)
            _bridge_close(number)
            processed.append({"issue": number, "status": "completed"})
        except Exception as exc:
            state["handled"][key].update(status="failed", completed_at=time.time(), error=type(exc).__name__)
            _bridge_save_state(state)
            _bridge_comment(number, "VISUAL bridge: execution failed (" + type(exc).__name__ + "). It will not be replayed automatically.")
            _bridge_close(number)
            processed.append({"issue": number, "status": "failed"})
    return {"status": "ok", "checked": len(issues), "processed": processed,
            "ledger_entries": len(state["handled"]), "repository_private": True}

def _bridge_loop():
    while not _BRIDGE_STOP.is_set():
        try:
            _bridge_once()
        except Exception as exc:
            logger = globals().get("log_error")
            if callable(logger):
                logger("chatgpt_bridge", exc)
        _BRIDGE_STOP.wait(BRIDGE_POLL_SECONDS)

@tool("ChatGPT-to-VISUAL bridge ka GitHub private queue, owner identity aur phone-local executor check karo. Koi command execute nahi hota.")
def chatgpt_bridge_status():
    try:
        info = _bridge_check()
        state = _bridge_load_state()
        return json.dumps({"status": "ready", **info, "polling": bool(_BRIDGE_THREAD and _BRIDGE_THREAD.is_alive()),
                           "handled_commands": len(state["handled"]), "allowed_actions": sorted(BRIDGE_ALLOWED),
                           "queue_label": BRIDGE_LABEL}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"status": "not_ready", "reason": str(exc)[:400]}, ensure_ascii=False)

@tool("Phone par ChatGPT Control Bridge polling chalu karo. Sirf private visual-data repo ke owner-authored visual-command issues aur allowlisted Knowledge Base tools process honge.", {}, risky=True)
def chatgpt_bridge_start():
    global _BRIDGE_THREAD
    info = _bridge_check()
    _bridge_load_state()
    with _BRIDGE_LOCK:
        if _BRIDGE_THREAD and _BRIDGE_THREAD.is_alive():
            return "Bridge pehle se chalu hai: " + info["repository"]
        cfg = _bridge_cfg()
        cfg["chatgpt_bridge_enabled"] = True
        saver = globals().get("save_json")
        conf_path = globals().get("CONF")
        if not callable(saver) or not conf_path:
            raise RuntimeError("VISUAL config writer unavailable")
        saver(conf_path, cfg)
        try:
            os.chmod(conf_path, 0o600)
        except OSError:
            pass
        _BRIDGE_STOP.clear()
        _BRIDGE_THREAD = threading.Thread(target=_bridge_loop, name="visual-chatgpt-bridge", daemon=True)
        _BRIDGE_THREAD.start()
    return "Bridge polling chalu. Phone VISUAL executor hai; allowlisted research/status actions only."

@tool("ChatGPT Control Bridge polling band karo. Already-running command ko beech mein zabardasti nahi roka jaata.")
def chatgpt_bridge_stop():
    _BRIDGE_STOP.set()
    cfg = _bridge_cfg()
    cfg["chatgpt_bridge_enabled"] = False
    saver = globals().get("save_json")
    conf_path = globals().get("CONF")
    if callable(saver) and conf_path:
        saver(conf_path, cfg)
        try:
            os.chmod(conf_path, 0o600)
        except OSError:
            pass
    return "Bridge stop signal bhej diya; restart ke baad bhi band rahega."

@tool("Private GitHub queue se ek baar commands check karo. Bridge status/test ke liye; command allowlist aur owner checks lagu rahenge.", {}, risky=True)
def chatgpt_bridge_poll_once():
    return json.dumps(_bridge_once(), ensure_ascii=False)

# Re-enable polling after VISUAL restarts only if the owner previously opted in.
try:
    if _bridge_cfg().get("chatgpt_bridge_enabled") is True:
        _BRIDGE_THREAD = threading.Thread(target=_bridge_loop, name="visual-chatgpt-bridge", daemon=True)
        _BRIDGE_THREAD.start()
except Exception:
    pass
