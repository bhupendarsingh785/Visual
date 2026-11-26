# VISUAL Upgrade Progress — 2026-11-26

Branch: upgrade/global-intelligence-v1  
PR: https://github.com/bhupendarsingh785/Visual/pull/1  
This is an evidence ledger, not a completion claim.

## Added in this work session
- Durable Planner/Coder/Tester/Security Reviewer state workflow in plugins/autonomous_development/orchestration_engine.py; Tester now requires runtime evidence and a current workspace hash; Security Reviewer requires a structured six-area checklist; owner approval rejects post-review workspace changes.
- VISUAL tool adapters registered in the existing autonomous_development plugin entry. The legacy Engineer quality gate now records the durable task ID and consults orchestration state instead of obsolete spec/tests_ok/critic fields.
- Tester stage requires successful isolated-runner evidence whose workspace hash matches the current artifact tree.
- Final approval is owner-only; a changed workspace invalidates the prior security review.
- New tests cover role sequencing, skipped roles, approval denial, missing security checklist, runtime evidence and post-review workspace mutation. Added tests/test_plugin_loader_isolation.py for private plugin namespaces and atomic tool publication.
- provider_live_check performs a low-token authenticated chat-completion smoke test for configured provider keys only; keys are never returned.
- device_runtime_diagnostics reports Android/Termux environment and command availability without claiming permissions, audio, Doze or reboot success.
- DEVICE_AND_ADAPTER_TEST_PLAN.md defines evidence contracts for device, provider, app, browser, API, database and deployment checks.

## Important limitations found during recheck
1. Plugin loading now uses per-plugin Python namespaces and atomic tool publication, with collision checks and no partial tool registration on import failure. This is NOT process/OS isolation: plugin code still runs in the VISUAL interpreter and inherits its capabilities. A dedicated restricted worker process with narrow RPC capabilities remains required before loading untrusted plugins.
2. The orchestration module is a durable state/evidence gate. It does not yet invoke four independent LLM role agents automatically, provide typed role-specific tool grants, or run an independent SAST/DAST security reviewer. Do not describe it as a completed multi-agent autonomous pipeline.
3. Android diagnostics have not been run on the owner's physical phone. Screen-off, Doze, microphone permission, foreground-service behavior, reboot recovery, battery and thermal tests remain unverified.
4. No live provider smoke test was run in this session because owner credentials are stored on the phone and are not available to this repository session. The new tool must be run locally; a successful request can consume quota.
5. App/browser/database/deployment adapters are specified but not implemented as executable adapters. Playwright, Android emulator, service database fixtures and staging deployment credentials are not configured here.
6. CI for the latest branch head has not been verified. The GitHub connector's commit-run lookup returned no PR workflow runs and the combined commit status returned an empty status list. Prior successful CI runs predate these changes and do not validate them.

## Release gate
Do not merge PR #1 or call this upgrade complete until:
- plugin process boundary is implemented and tested with filesystem/network/secret isolation appropriate to the threat model;
- orchestration invokes distinct role agents and enforces their contracts, budgets, retries, approval and evidence gates;
- latest CI is green;
- physical Android/Termux test report is attached;
- live provider results are recorded for each configured key;
- executable app/browser/API/database/deployment adapters pass against disposable fixtures/staging;
- full regression, security and rollback checks pass.


## Integration repair pass — 2026-11-26

- Plugin loader now removes temporary plugin directories from `sys.path` and evicts newly imported sibling modules from the global `sys.modules` cache after plugin initialization. Registered tool functions retain their module references. This prevents path pollution and common helper-name collisions; it remains same-process execution, not a security boundary.
- The Docker execution adapter now retains direct references to the development engine functions it needs at runtime, so cleanup of the plugin import path does not break lazy runner operations.
- Added an end-to-end CI smoke test that imports VISUAL, verifies critical development, orchestration, self-intelligence and memory-repeat tools are actually registered, then exercises the development task/test/status adapter chain.
- Fixed memory-repeat plugin registration: bare `@tool` decorators did not register tools under the staged plugin decorator. All memory-repeat tools now declare explicit schemas.
- Removed duplicated MemoryStore implementation from the active plugin adapter; it uses the shared `memory_store.py` implementation. Persistent statement data now lives under `~/.visual/last_statement.json`, not inside the source checkout.
- Removed the unused duplicate `orchestration_plugin.py`; orchestration adapters remain registered from the active `plugins/autonomous_development/plugin.py`.
- Installer-generated launcher and Termux:Boot entry now point to the actual directory containing `install.sh`. Updater and supervisor resolve the installation directory relative to their own scripts, with `VISUAL_HOME_DIR` override for the supervisor.
- Updater now runs the same core import smoke test and regression suites as CI before reporting a successful update.
- Regression tests caught two real integration mistakes during this pass (helper fixture accidentally discovered as a top-level plugin, and a memory tool registration/test wiring issue); both were corrected before final verification.

## Verification for this pass

- GitHub Actions run for commit `261f9ac0aa2d32276dd4730bf8efe2472799a2c1`: Python 3.11, 3.13 and 3.14 matrix. The import/tool-registration smoke test, shell syntax checks, continuous-listening mocked tests, memory-repeat tests, core plugin integration tests, Self-Intelligence tests and Autonomous Development tests are required.
- These CI checks are automated hosted-runner evidence only. They do not prove physical Android/Termux behavior, live API provider connectivity, Docker daemon availability on the phone, or app/browser/database/deployment E2E behavior.

## Still not complete / not certified

- Plugin code still executes inside the VISUAL interpreter. A restricted worker process with narrow RPC capabilities is not implemented.
- Planner/Coder/Tester/Security Reviewer are durable workflow roles, but are not yet four independent LLM agents with separately enforced tool grants. The security checklist is not an independent SAST/DAST scan.
- Live provider tests, real Docker test execution on the target device, Android permission/audio/Doze/reboot tests, and executable browser/app/API/database/deployment adapters remain unverified or unimplemented.
- Do not merge the draft PR or describe VISUAL as release-complete until those acceptance gates are independently satisfied.
