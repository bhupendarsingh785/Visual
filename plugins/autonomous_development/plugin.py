"""VISUAL Autonomous Development tools: durable planning, research ledger and artifact workspaces."""
import json
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


@tool("Task workspace ke Python syntax, JSON validity aur secret-like token patterns ki static validation chalao. Generated code execute nahi hota.",
      {"task_id":S("task id")})
def dev_task_validate(task_id):
    return json.dumps(validate_artifacts(task_id,globals().get("HOME")),ensure_ascii=False,indent=2)


@tool("Validated development task ko owner approval ke baad completed mark karo. Ye approval-gated action hai.",
      {"task_id":S("task id"),"approval_note":S("owner review/approval note")},risky=True)
def dev_task_approve(task_id,approval_note):
    return transition(task_id,"completed",approval_note,actor="owner",home=globals().get("HOME"))
