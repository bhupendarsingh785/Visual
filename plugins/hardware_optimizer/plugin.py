"""Hardware-aware runtime tools for VISUAL."""
import json
from engine import hardware_profile, optimization_plan, create_onnx_session
_SESSIONS = {}

@tool("Inspect CPU, RAM, Android SoC, accelerator device nodes, ONNX Runtime providers and local inference runtimes.")
def hardware_status():
    return json.dumps(hardware_profile(),ensure_ascii=False,indent=2)

@tool("Create a measured-safe optimization plan for LLM, vision, audio, speech or robotics workloads.",
      {"workload":S("llm, vision, audio, speech, robotics or general"),
       "ram_budget_mb":N("RAM budget MB; 0 uses a conservative automatic budget")})
def hardware_optimization_plan(workload="llm",ram_budget_mb=0):
    return json.dumps(optimization_plan(workload,ram_budget_mb),ensure_ascii=False,indent=2)[:14000]

@tool("Initialize a local ONNX model with optimized graph and actually available execution providers. This creates a session but does not execute or benchmark inference.",
      {"model_path":S("absolute .onnx path inside ~/.visual/models, Android Download or Documents"),
       "intra_threads":N("0=runtime default; otherwise CPU intra-op thread limit")},risky=True)
def hardware_load_onnx_model(model_path,intra_threads=0):
    session,report=create_onnx_session(model_path,globals().get("HOME"),intra_threads)
    _SESSIONS[report["model"]]=session
    report["session_lifetime"]="Current VISUAL process only; restart clears loaded sessions."
    return json.dumps(report,ensure_ascii=False,indent=2)
