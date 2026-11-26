# VISUAL System Re-audit and Hardening Plan — 2026-11-26

Status: **audit baseline and acceptance plan**. This document does not claim that the listed upgrades or physical-device checks are complete.

Target: current `main` baseline, with all implementation work isolated on `upgrade/verified-system-hardening-2026-11-26`.

## 1. Verified baseline from repository inspection

- The main branch contains the public Knowledge Base collector and its tool registration in `plugins/knowledge_base/plugin.py`. The global collector is explicitly bounded to 300 provider requests per run and 25 metadata records per request. It harvests public API metadata; it is not a full dataset mirror and does not train model weights.
- The main branch contains the Android remote browser bridge: `scripts/visual-remote.sh`, `docs/REMOTE_BROWSER_BRIDGE.md`, and a same-origin/token regression test added with the bridge. The documented bridge requires Termux, the phone-hosted web server, Cloudflare Quick Tunnel, and an email OTP. The URL is temporary and the phone must remain online.
- The main branch README describes separate memory files and GitHub sync/restore. Repository documentation alone does not prove that all memory stores are unified or that a restore is complete on a physical device.
- Hardware optimizer code discovers available runtime providers and reports/plans compute placement. RTL simulation or synthesis is not evidence of integration with the Android phone's physical NPU/GPU.
- A prior experimental branch `upgrade/global-intelligence-v1` contains autonomous-development/orchestration and audit work, but comparison against current main reports **186 commits ahead and 230 behind**. It is intentionally not merged or treated as a safe patch source.

## 2. Evidence labels required in every report

Use only these labels:
- **PASS-CI**: a named CI job passed on the exact commit SHA.
- **PASS-LOCAL**: a named test passed in a recorded local environment.
- **PASS-DEVICE**: the test ran on the owner's actual Android phone and records Android version, device/SoC, Termux/Python versions, power/network state, command, timestamp and result.
- **PASS-LIVE**: a real provider/API/browser/database/deployment request succeeded; redact all credentials.
- **BLOCKED**: required device, permission, credential, service, hardware, or fixture was unavailable.
- **FAIL**: reproducible failure with test name, logs and commit SHA.
- **NOT-IMPLEMENTED**: no executable implementation exists.
- **NOT-VERIFIED**: code or docs exist but no sufficient runtime evidence exists.

Never convert CI evidence into a phone/hardware/live-service claim.

## 3. Workstreams and acceptance gates

### A. Runtime and plugin registration
- Verify clean import, deterministic plugin discovery, duplicate-name collision handling, atomic tool registration, schema validation and startup/shutdown.
- Inject malformed plugin, missing dependency, duplicate tool name, import exception and partial-registration failures.
- Verify one plugin failure does not prevent unrelated safe plugins from loading.
- Preserve existing tool names and public interfaces unless a migration is tested.

### B. Knowledge Base and global research
- Verify provider allowlist, bounded request budgets, Retry-After/backoff, cursor persistence, deduplication, source provenance, license quarantine, malformed/empty response classification and SQLite integrity.
- Run repeated collection with the same cursor and with a resumed cursor; prove no duplicate growth beyond documented behavior.
- Report per-provider attempts, successes, empty results, rejected records, failures, newly indexed records, database deltas, topic counts and storage bytes.
- Verify a dedicated deep-learning topic search yields actual dataset records and item-level license evidence before calling the data training-ready.
- Explicitly separate metadata harvesting, full dataset download, RAG indexing, corpus preparation and model training.

### C. Memory integration
- Inventory every memory/conversation/task/knowledge store and every read/write/sync/restore path.
- Define canonical ownership, schemas, identifiers, timestamps, migrations, conflict policy, deletion/retention and backup/restore behavior.
- Test cross-store recall, duplicate writes, interrupted writes, concurrent access, migration, backup, restore and corruption recovery.
- Do not silently merge semantically different stores or overwrite source-of-truth data.

### D. Autonomous development
- Distinguish durable workflow states from genuinely independent Planner, Coder, Tester and Security Reviewer agents.
- Enforce typed role-specific tool permissions, bounded budgets, immutable task artifacts, current workspace hashes, reproducible execution evidence and owner approval.
- A Tester pass must refer to tests actually executed against the exact artifact hash.
- A Security Reviewer pass must include independent static/security checks; a manually filled checklist alone is not an independent scan.
- Verify failed tasks, retries, cancellation, resume, approval denial and workspace mutation invalidation.

### E. Plugin isolation and security
- Current Python namespaces/import cleanup are not an OS security boundary.
- Design a restricted worker process with narrow RPC capabilities, explicit filesystem roots, network policy, time/memory/CPU limits, sanitized environment and structured logs.
- Test filesystem escape, secret/environment access, subprocess escape, network access, resource exhaustion, worker crash and malformed RPC payloads.
- If a safe process boundary cannot be implemented on Android/Termux, fail closed for untrusted plugins and document the supported platform boundary.

### F. Android background runtime and remote browser
- Test actual Termux launch, supervisor restart, foreground/notification behavior where supported, screen-off runtime, Doze/battery restrictions, reboot recovery, microphone/camera permissions, storage access, thermal throttling and sustained operation.
- Test remote bridge start/stop, web-server readiness, email OTP gate, same-origin/token checks, cross-site rejection, tunnel loss/reconnect and cleanup.
- Do not publish or share temporary tunnel URLs or secrets in CI logs.
- Record phone model, Android build, Termux and package versions for each device run.

### G. Hardware and AI acceleration
- Detect only real available CPU/GPU/NPU/NNAPI/ONNX/PyTorch providers; never report simulated RTL as a deployed accelerator.
- Separate device discovery, backend availability, model-load success, inference correctness, latency, memory and sustained thermal tests.
- Test CPU fallback and unsupported-provider failure paths.
- Physical NPU/GPU integration remains NOT-VERIFIED until a real model inference benchmark runs on the target phone and identifies the provider actually used.

## 4. Repeated test strategy

For every code change:
1. Static checks: syntax/compile, imports, schema, duplicate registrations, secret scan and dependency checks.
2. Unit tests: changed module and failure-path tests.
3. Integration tests: plugin registration, runtime startup, knowledge/memory/development interactions.
4. Security tests: permissions, path traversal, origin/token checks, worker boundaries and secret redaction.
5. Regression suite: all existing project tests on supported Python versions.
6. Repeatability: run the relevant suite at least three times; investigate flaky tests rather than hiding them.
7. Recovery: interruption, restart, rollback and data-integrity tests.
8. Device/live gates: execute separately on the owner's phone and real external services; attach sanitized evidence.

Every result must record commit SHA, command, environment, test name, outcome and log/artifact reference.

## 5. Release gate

No claim of "complete", "error-free", "fully autonomous", "phone-tested" or "hardware-accelerated" until all applicable gates above pass with evidence. Do not merge this branch into main until CI is green, review is complete, and any device-only limitations are clearly recorded. Preserve the existing main branch and user data; do not run destructive migrations or bulk downloads as part of an audit.
