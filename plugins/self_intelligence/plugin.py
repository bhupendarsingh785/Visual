"""VISUAL Self-Intelligence: auditable self-knowledge and controlled improvement planning."""
import json
import platform
import sys
from self_intelligence_engine import (
    assess_snapshot, collect_snapshot, create_plan, latest_report,
    plan_history, save_snapshot, update_plan,
)


def _self_context():
    return {
        "root": globals().get("HERE"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "providers": globals().get("PROVIDERS", {}),
        "tasks": globals().get("TASKS", {}),
        "tools": globals().get("TOOLS", {}),
        "plugins": {name: True for name in (globals().get("PLUGINS") and __import__("os").listdir(globals()["PLUGINS"]) or [])},
        "plugin_errors": globals().get("PLUGIN_ERRORS", {}),
        "config": globals().get("CFG", {}),
    }


@tool("VISUAL ka detailed self-audit: runtime, tools, plugins, providers, task states aur file inventory ka snapshot save karke deterministic findings deta hai.")
def self_intelligence_audit():
    snapshot = collect_snapshot(_self_context())
    findings = assess_snapshot(snapshot)
    saved = save_snapshot(snapshot, findings, globals().get("HOME"))
    return json.dumps({"saved": saved, "summary": {
        "tools": snapshot["tool_count"], "plugins": len(snapshot["plugins"]),
        "providers": len(snapshot["providers"]), "files": snapshot["file_inventory"]["count"],
        "plugin_errors": len(snapshot["plugin_errors"]),
    }, "findings": [{"severity": f[0], "area": f[1], "title": f[2], "detail": f[3]} for f in findings]}, ensure_ascii=False)


@tool("VISUAL ki saved self-information report aur pichhle improvement plans dikhao.")
def self_intelligence_report():
    return json.dumps(latest_report(globals().get("HOME")), ensure_ascii=False, indent=2)[:12000]


@tool("VISUAL ke liye measurable self-improvement proposal banao. Isse code apne aap nahi badlega; har plan ko alag approval aur test chahiye.",
      {"title": S("sudhar ka naam"), "scope": S("kaun se modules/features"), "rationale": S("evidence-based wajah"),
       "risk": S("risk aur rollback"), "acceptance": S("pass hone ke measurable tests")})
def self_improvement_propose(title, scope, rationale, risk, acceptance):
    pid = create_plan(title, scope, rationale, risk, acceptance, globals().get("HOME"))
    return "Improvement plan proposed: " + pid + ". Ab report mein review karein; bina approval code nahi badlega."


@tool("Self-improvement plan ka status badlo. Allowed: proposed, approved, in_progress, needs_review, rejected, completed. Status change audit ledger mein save hota hai.",
      {"plan_id": S("plan ID"), "status": S("allowed workflow status"), "notes": S("review/test evidence ya wajah")})
def self_improvement_update(plan_id, status, notes):
    update_plan(plan_id, status, notes, globals().get("HOME"))
    return "Plan " + plan_id + " status updated to " + status + ". 'completed' sirf tab use karein jab independent test evidence record ho."


@tool("VISUAL ke pichhle self-improvement plans aur unke acceptance criteria dekho.")
def self_improvement_history():
    return json.dumps(plan_history(globals().get("HOME")), ensure_ascii=False, indent=2)[:10000]
