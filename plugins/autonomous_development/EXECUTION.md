# Isolated execution and test runner

This runner is an execution adapter for the Autonomous Development subsystem. It deliberately fails closed when an isolated runtime is unavailable.

## Supported execution profiles
- Python: preloaded `python:3.12-slim`
- Node.js: preloaded `node:22-alpine`

The images must already exist locally. The agent cannot pull images or install packages as a side effect. The runner disables networking, forwards no API keys or host environment variables, drops Linux capabilities, enables no-new-privileges, uses a non-root UID, makes the root filesystem read-only, applies CPU/memory/PID limits, and mounts only the task workspace.

## Tools
- `dev_task_run_tests(task_id, profile, timeout)`: built-in test profile.
- `dev_task_run_manifest(task_id, manifest_json, timeout)`: explicit argv-only commands inside the selected profile; no shell string is accepted.

## Android / Termux limitation
Stock unrooted Termux generally does not provide a Docker daemon or Linux namespaces/cgroups required for a robust container sandbox. PRoot is not a kernel isolation boundary. Therefore this runner does not fall back to executing generated code directly on the phone. For phone-first use, connect a managed remote sandbox provider or a separately provisioned isolated host. The control plane and task ledger can remain on the phone.

## Not a universal test oracle
A passing Python or Node test profile does not prove all app types are correct. UI, browser, Android APK, database, API integration, load, accessibility, compatibility and security tests need the relevant emulators/devices/services and explicit test manifests. Missing infrastructure is reported as unavailable, not passed.

## Run tests
```bash
PYTHONPATH=plugins/autonomous_development python -m unittest discover -s plugins/autonomous_development -p 'test_*.py' -v
```


## Research basis
- OpenAI Agents SDK sandbox architecture separates the trusted orchestration/control plane from the sandbox compute plane: https://developers.openai.com/api/docs/guides/agents/sandboxes
- OpenAI human-review guidance requires pausing before sensitive side effects and resuming only after approval: https://developers.openai.com/api/docs/guides/agents/guardrails-approvals
- Android's own security guidance emphasizes app/process isolation and avoiding unnecessary privilege: https://source.android.com/docs/security/best-practices/app
- Termux PRoot documentation explicitly states that PRoot does not provide real namespaces/cgroups/seccomp isolation: https://github.com/termux/proot-distro
- OWASP Excessive Agency recommends minimum tool/permission scope, human approval, and SAST/DAST/IAST where appropriate: https://genai.owasp.org/llmrisk/llm062025-excessive-agency/

## Test coverage roadmap
The current executable profiles are Python and Node.js. The test manifest accepts argv arrays (never shell command strings) inside the isolated runner. Additional adapters must be added for:
- Web UI/E2E: pinned Playwright image plus project-matched Playwright dependency and browser tests.
- Android APK: pinned Android SDK/Gradle image, emulator/device test runner, signing kept outside the sandbox.
- API/backend: disposable test database/service fixtures, contract tests and integration tests.
- Security: dependency/SBOM checks, SAST, secret scan, DAST against an isolated staging target.
- Performance/reliability: bounded load tests, crash/restart and resource budgets.
- Device validation: real Android versions, permissions, background execution, battery and microphone tests.

A test category is "not run" until its matching adapter and infrastructure produce evidence. A green syntax or unit-test result is not a universal quality certificate.
