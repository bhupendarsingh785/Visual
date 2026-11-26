"""Tool adapters for durable multi-role development workflow."""
import json
from orchestration_engine import start, current, record, approve

@tool("Start or resume the durable Planner-Coder-Tester-Security Reviewer workflow.", {"task_id":S("development task id")})
def dev_orchestration_start(task_id):
    return json.dumps(start(task_id, globals().get("HOME")), ensure_ascii=False)

@tool("Read current active orchestration role, cycle and approval state.", {"task_id":S("development task id")})
def dev_orchestration_status(task_id):
    return json.dumps(current(task_id, globals().get("HOME")), ensure_ascii=False)

@tool("Record a role result; roles planner/coder/tester/security_reviewer and outcomes pass/revise/fail/blocked.", {"task_id":S("task id"),"role":S("active role"),"outcome":S("pass | revise | fail | blocked"),"notes":S("evidence and findings",optional=True)})
def dev_orchestration_record(task_id, role, outcome, notes=""):
    return json.dumps(record(task_id, role, outcome, notes, globals().get("HOME")), ensure_ascii=False)

@tool("Owner-only final approval after current workspace hash and review evidence are verified.", {"task_id":S("task id"),"approval_note":S("owner approval note")}, risky=True)
def dev_orchestration_approve(task_id, approval_note):
    return json.dumps(approve(task_id, approval_note, actor="owner", home=globals().get("HOME")), ensure_ascii=False)
