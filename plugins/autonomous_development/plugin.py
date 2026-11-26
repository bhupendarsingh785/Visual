"""VISUAL Autonomous Development tools: durable planning, research ledger and artifact workspaces."""
import json
from execution_engine import run_manifest, run_profile
from autonomous_development_engine import (
    add_research, create_task, get_task, list_artifacts, list_tasks,
    transition, validate_artifacts, write_artifact,
)


@tool("Naya durable development task banao. Code live VISUAL mein nahi, alag task workspace mein banega.",
      {"title":S("task title"),"goal":S("complete objective, constraints and expected deliverables"),"kind":S("build | upgrade | debug | research | tool",optional=True)})
def dev_task_create(title,goal,kind="build"):
    return json.dumps(create_task(title,goal,kind,globals().get("HOME")),ensure_ascii=False)


@tool("Development task ki current state, research sources, artifact hashes aur event history dekho.",
      {"task_id":S("development task id")})
def dev_task_status(task_id):
    return json.dumps(get_task(task_id,globals().get("HOME")),ensure_ascii=False,indent=2)[:12000]


@tool("Recent development tasks ki list dekho.", {"limit":N("1 se 100",optional=True)})
def dev_task_list(limit=30):
    return json.dumps(list_tasks(globals().get("HOME"),limit),ensure_ascii=False,indent=2)


@tool("Development task ko valid stage mein move karo. completed sirf approval gate ke baad allowed hai.",
      {"task_id":S("task id"),"status":S("planning | researching | designing | implementing | validating | awaiting_approval | completed | failed | cancelled"),"notes":S("reason, evidence or next step")})
def dev_task_transition(task_id,status,notes=""):
    return transition(task_id,status,notes,actor="agent",home=globals().get("HOME"))


@tool("Research ka source ledger banao: HTTPS URL, title, summary aur exact supporting evidence record karo.",
      {"task_id":S("task id"),"url":S("source HTTPS URL"),"title":S("page or paper title"),"summary":S("source se nikla short summary"),"evidence":S("exact short excerpt or section reference",optional=True)})
def dev_task_add_research(task_id,url,title,summary,evidence=""):
    add_research(task_id,url,title,summary,evidence,globals().get("HOME"))
    return "Research source ledger mein save hua."


@tool("Development task workspace mein file create/update karo. Live VISUAL source files is tool se change nahi hoti.",
      {"task_id":S("task id"),"path":S("relative path, e.g. src/main.py"),"content":S("complete file content")})
def dev_task_write_file(task_id,path,content):
    return json.dumps(write_artifact(task_id,path,content,globals().get("HOME")),ensure_ascii=False)


@tool("Task workspace ki generated files aur unke naam dekho.", {"task_id":S("task id")})
def dev_task_files(task_id):
    return "\n".join(list_artifacts(task_id,globals().get("HOME"))) or "(abhi files nahi)"


@tool("Task workspace ke Python/JavaScript/shell syntax, JSON validity aur secret-like token patterns ki static validation chalao. Generated code execute nahi hota.",
      {"task_id":S("task id")})
def dev_task_validate(task_id):
    return json.dumps(validate_artifacts(task_id,globals().get("HOME")),ensure_ascii=False,indent=2)


@tool("Validated development task ko owner approval ke baad completed mark karo. Ye approval-gated action hai.",
      {"task_id":S("task id"),"approval_note":S("owner review/approval note")},risky=True)
def dev_task_approve(task_id,approval_note):
    return transition(task_id,"completed",approval_note,actor="owner",home=globals().get("HOME"))


@tool("Task code ko isolated Docker container mein Python/Node test profile se run karo. Docker/image missing ho to code phone par execute nahi hoga; tool unavailable report karega.",
      {"task_id":S("task id"),"profile":S("python ya node"),"timeout":N("seconds, max 600",optional=True)})
def dev_task_run_tests(task_id,profile,timeout=600):
    return json.dumps(run_profile(task_id,profile,globals().get("HOME"),timeout),ensure_ascii=False,indent=2)[:12000]


@tool("Task ke declared tests ko isolated container mein run karo. manifest_json mein profile aur argv arrays honge; shell command strings allowed nahi.",
      {"task_id":S("task id"),"manifest_json":S("JSON: {\"profile\":\"python|node\",\"commands\":[[\"python\",\"-m\",\"unittest\"]] }"),"timeout":N("seconds, max 600",optional=True)})
def dev_task_run_manifest(task_id,manifest_json,timeout=600):
    manifest=json.loads(manifest_json)
    return json.dumps(run_manifest(task_id,manifest,globals().get("HOME"),timeout),ensure_ascii=False,indent=2)[:12000]


# Multi-role orchestration tools
from orchestration_engine import start as _orch_start, current as _orch_current, record as _orch_record, approve as _orch_approve

@tool("Start or resume the durable Planner-Coder-Tester-Security Reviewer workflow.", {"task_id":S("development task id")})
def dev_orchestration_start(task_id):
    return json.dumps(_orch_start(task_id, globals().get("HOME")), ensure_ascii=False)

@tool("Read current active orchestration role, cycle and approval state.", {"task_id":S("development task id")})
def dev_orchestration_status(task_id):
    return json.dumps(_orch_current(task_id, globals().get("HOME")), ensure_ascii=False)

@tool("Record a role result. Tester pass requires current isolated runtime test evidence.", {"task_id":S("task id"),"role":S("active role"),"outcome":S("pass | revise | fail | blocked"),"notes":S("evidence and findings",optional=True)})
def dev_orchestration_record(task_id, role, outcome, notes=""):
    return json.dumps(_orch_record(task_id, role, outcome, notes, globals().get("HOME")), ensure_ascii=False)

@tool("Owner-only final approval after current workspace hash and review evidence are verified.", {"task_id":S("task id"),"approval_note":S("owner approval note")},risky=True)
def dev_orchestration_approve(task_id, approval_note):
    return json.dumps(_orch_approve(task_id, approval_note, actor="owner", home=globals().get("HOME")), ensure_ascii=False)
