"""Fail-closed Docker test runner for generated development workspaces.

Generated project code is never executed directly as the Termux/VISUAL user.
Docker must already be installed and running; images are local-only (no pull),
containers have no network, no secrets, bounded resources and only the task
workspace mounted. This is defense-in-depth, not a claim that containers are
perfectly secure.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

PROFILES = {
    "python": {
        "image": "python:3.12-slim",
        "commands": [
            ["python", "-m", "compileall", "-q", "."],
            ["python", "-m", "unittest", "discover", "-v"],
        ],
    },
    "node": {
        "image": "node:22-alpine",
        "commands": [
            ["node", "--test"],
        ],
    },
}
MAX_SECONDS = 600
MAX_OUTPUT = 12000


def _finish(task_id, report, home=None):
    from autonomous_development_engine import record_execution_result
    record_execution_result(task_id, report, home)
    return report


def _workspace(task_id, home=None):
    # Import lazily to keep this module independently testable.
    from autonomous_development_engine import _workspace as get_workspace
    return get_workspace(task_id, home)


def _docker_available():
    docker = shutil.which("docker")
    if not docker:
        return None, "Docker executable nahi mila; direct local execution fail-closed hai."
    try:
        r = subprocess.run([docker, "info", "--format", "{{.ServerVersion}}"],
                           capture_output=True, text=True, timeout=8,
                           env={"PATH": os.environ.get("PATH", "")})
        if r.returncode:
            return None, "Docker daemon unavailable; no code was executed."
        return docker, "Docker " + (r.stdout.strip() or "available")
    except Exception as exc:
        return None, "Docker availability check failed: " + str(exc)[:200]


def _run_one(docker, workspace, image, argv, timeout):
    # No shell, no inherited environment, no network, no host credentials.
    cmd = [
        docker, "run", "--rm", "--pull=never",
        "--network=none", "--read-only",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--pids-limit=128", "--memory=768m", "--cpus=1.0",
        "--user=65534:65534",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m",
        "-e", "HOME=/tmp", "-e", "TMPDIR=/tmp",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTEST_ADDOPTS=-p no:cacheprovider",
        "-v", str(workspace) + ":/workspace:ro",
        "-w", "/workspace", image, *argv,
    ]
    env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8"}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        out = ((r.stdout or "") + ("\nSTDERR:\n" + r.stderr if r.stderr else ""))[-MAX_OUTPUT:]
        return {"status": "passed" if r.returncode == 0 else "failed",
                "exit_code": r.returncode, "output": out}
    except subprocess.TimeoutExpired as exc:
        out = ((exc.stdout or "") + (exc.stderr or "")) if isinstance(exc.stdout, str) else ""
        return {"status": "timeout", "exit_code": None, "output": out[-MAX_OUTPUT:]}
    except Exception as exc:
        return {"status": "error", "exit_code": None, "output": str(exc)[:1000]}


def run_profile(task_id, profile, home=None, timeout=MAX_SECONDS):
    profile = str(profile).strip().lower()
    if profile not in PROFILES:
        raise ValueError("profile python ya node hona chahiye")
    timeout = max(1, min(int(timeout), MAX_SECONDS))
    ws = _workspace(task_id, home)
    docker, detail = _docker_available()
    report = {
        "task_id": task_id, "profile": profile, "environment": detail,
        "network": "disabled", "secrets_forwarded": False,
        "workspace": "task workspace only", "started_at": time.time(),
        "results": [], "status": "unavailable",
    }
    if not docker:
        report["limitations"] = "No direct execution fallback is allowed. Configure a supported isolated Docker host or managed sandbox."
        return report
    image = PROFILES[profile]["image"]
    # Never download images from an agent task; image must be preloaded by the owner.
    try:
        image_check = subprocess.run([docker, "image", "inspect", image],
                                      capture_output=True, text=True, timeout=10,
                                      env={"PATH": os.environ.get("PATH", "")})
    except Exception as exc:
        report["limitations"] = "Image check failed: " + str(exc)[:200]
        return report
    if image_check.returncode:
        report["limitations"] = f"Required local image {image} is not present. Runner will not pull it or access the network."
        return report
    for argv in PROFILES[profile]["commands"]:
        result = _run_one(docker, ws, image, argv, timeout)
        result["command"] = argv
        report["results"].append(result)
        if result["status"] != "passed":
            break
    report["status"] = "passed" if report["results"] and all(x["status"] == "passed" for x in report["results"]) else "failed"
    report["finished_at"] = time.time()
    return report


def run_manifest(task_id, manifest, home=None, timeout=MAX_SECONDS):
    """Run explicit argv-only test commands inside the same restricted container."""
    if not isinstance(manifest, dict) or manifest.get("profile") not in PROFILES:
        raise ValueError("manifest profile python ya node hona chahiye")
    commands = manifest.get("commands")
    if not isinstance(commands, list) or not commands or len(commands) > 20:
        raise ValueError("manifest mein 1 se 20 commands ki list honi chahiye")
    clean = []
    for argv in commands:
        if not isinstance(argv, list) or not argv or len(argv) > 32:
            raise ValueError("har command argv list honi chahiye")
        if any(not isinstance(x, str) or not x or len(x) > 300 or "\x00" in x for x in argv):
            raise ValueError("invalid command argument")
        clean.append(argv)
    profile = manifest["profile"]
    ws = _workspace(task_id, home)
    docker, detail = _docker_available()
    report = {"task_id": task_id, "profile": profile, "environment": detail,
              "network": "disabled", "secrets_forwarded": False,
              "results": [], "status": "unavailable", "manifest_commands": clean}
    if not docker:
        report["limitations"] = "No direct local execution fallback. Configure isolated Docker or managed sandbox."
        return report
    image = PROFILES[profile]["image"]
    check = subprocess.run([docker, "image", "inspect", image], capture_output=True,
                           text=True, timeout=10, env={"PATH": os.environ.get("PATH", "")})
    if check.returncode:
        report["limitations"] = f"Required local image {image} is missing; automatic pull is disabled."
        return report
    for argv in clean:
        result = _run_one(docker, ws, image, argv, max(1,min(int(timeout),MAX_SECONDS)))
        result["command"] = argv
        report["results"].append(result)
        if result["status"] != "passed":
            break
    report["status"] = "passed" if len(report["results"]) == len(clean) and all(x["status"] == "passed" for x in report["results"]) else "failed"
    report["finished_at"] = time.time()
    return report
