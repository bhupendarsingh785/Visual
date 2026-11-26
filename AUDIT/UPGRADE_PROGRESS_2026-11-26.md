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
