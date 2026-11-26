# VISUAL Complete-System Upgrade Blueprint (Research-led)

Date: 2026-11-26
Repository: `bhupendarsingh785/Visual`
Target branch: `upgrade/global-intelligence-v1`
Status: architecture and acceptance blueprint; not a claim that all capabilities are implemented.

## 1. Existing baseline verified in source

The current code already contains meaningful foundations; do not replace them wholesale:

- 16 configured cloud providers in `visual.py`: Gemini, Groq, OpenRouter, GitHub Models, Cerebras, NVIDIA, Mistral, Zhipu, SiliconFlow, ModelScope, Qwen, DeepSeek, Moonshot, Upstage, Cohere and Sarvam.
- Category-aware routing (`classify`, `route`), provider/model discovery, key rotation/cooldowns, rate-limit-aware fallback and persisted quality/latency statistics.
- Tool registry and confirmation flow for risky tools; phone-control, web search/read, Telegram/web interfaces and voice paths.
- Existing Engineer task queue (`agent_task` / `_engineer`), code-generation candidate evaluation (`_sandbox_eval`), self-diagnosis, backups, self-check, rollback and private data sync.
- Existing persistent JSON memory, sessions, facts, reminders and router stats.

These are foundations, not proof that every provider/model/key is currently live or that all advertised tools work on a real Android phone. Provider model IDs and free quotas change; runtime discovery and observed health must be authoritative.

## 2. Target architecture

Keep the current single-process Termux application as the compatibility shell for the first release. Add modular subsystems behind stable interfaces; avoid a disruptive rewrite.

### A. Control plane / Master Orchestrator
- One task state machine: `queued -> planning -> running -> validating -> awaiting_approval -> completed | failed | cancelled`.
- Every task has an immutable task ID, owner/session, goal, allowed tools, budget (time/tokens/API calls), deadline, retry budget, checkpoints, artifacts and final evidence report.
- Deterministic policy code decides which agent can run and which actions require approval. LLM output never grants itself permissions.
- Agent roles: Planner, Researcher, Evidence Verifier, Architect, Coder, Test Engineer, Security Reviewer, Runtime/Device Tester, Release Manager.
- Agents communicate through typed JSON task envelopes and artifact references, not unrestricted shared prompt history.
- Parallelize independent research/review tasks only; serialize writes to a given file/branch.

### B. Provider gateway / router
- Preserve the 16 current provider adapters and existing category router. Put provider-specific request/response parsing behind a common adapter interface.
- Capability registry per model: text, vision, tool-call compatibility, JSON/schema support, context limits, streaming, latency, cost/free-tier status, region and last verified timestamp.
- Health state per provider+model+key fingerprint: healthy, rate_limited, auth_failed, unavailable, model_retired, capability_mismatch. Use Retry-After and provider headers where present; exponential backoff with jitter; never retry invalid credentials endlessly.
- Separate provider availability from model capability. A fallback is eligible only if it supports the task's required capabilities.
- Exploration is bounded, opt-out for critical tasks, and never sends sensitive user data to a newly discovered provider without consent.
- Keep per-category routing quality, latency, success, token/cost estimates and calibration. Avoid treating a model's own self-rating as ground-truth quality.
- Live voice remains a separately negotiated capability; do not imply every provider supports realtime audio.

### C. Research subsystem
- Pipeline: clarify question -> decompose subquestions -> search independent sources -> fetch primary sources -> extract claims -> attach exact URLs/date/quotes -> corroborate/conflict-check -> write synthesis -> human-readable source ledger.
- Each claim stores source URL, publisher, published/updated date, retrieved timestamp, quoted evidence span, confidence and contradiction notes.
- Prefer official docs, standards, original papers and primary datasets; use secondary reporting for context.
- Search failure is explicit. No fabricated citations and no claim of web verification if sources were not fetched.
- Respect robots, rate limits, licensing, privacy, and no login/paywall bypass.

### D. Memory system
- Keep existing JSON memory readable and provide one-way migration with backup; do not delete legacy files during migration.
- Add SQLite as the durable index: events, facts, conversations, tasks, artifacts, provenance, consent, expiry and deletion tombstones.
- Use SQLite FTS5 lexical retrieval first (low RAM / CPU); optional local embeddings are an add-on, not a mandatory dependency. FTS5 provides full-text search and ranking/snippets.
- Every memory item records source, created_at, last_confirmed_at, sensitivity, confidence, expiry and user-edit/delete status.
- Memory writes are suggestions with deduplication and confidence thresholds; sensitive details are not retained by default. User correction overrides inferred memory.
- Summaries are derived views; original records remain recoverable until user-requested deletion policy applies.

### E. Safe tool and plugin execution
- Replace shared-global `exec` loading over time with explicit plugin manifest + registry. Until then, load only trusted bundled plugins.
- Plugin manifest: name/version, entry point, tool schemas, required permissions, network hosts, filesystem roots, risk class and dependency hashes.
- Capability grants are deny-by-default. Read-only tools, network tools, device-control tools and destructive tools have separate scopes.
- Tool arguments validated against JSON Schema; outputs size-limited and treated as untrusted data.
- Prompt injection in web pages, documents and tool results must not alter system policy or permission grants.
- Human confirmation for SMS, calls, messaging, purchases/payments, file deletion, external posting, credential changes, code execution outside sandbox and repository release.
- Audit log records actor, requested action, arguments redacted for secrets, decision, approval identity, result and timestamps.

### F. Coding / self-repair / release
- Self-repair is a proposal pipeline, never direct self-modification of the live process.
- Steps: reproduce -> failing regression test -> patch in isolated worktree -> syntax/type/static checks -> unit/integration tests -> security scan -> critic review -> backup -> staged install -> health check -> rollback on failure.
- Tests may not be weakened or removed just to make a patch pass. If a test is invalid, require a documented reason and reviewer approval.
- Sandbox generated code with a separate OS process, temporary HOME, restricted filesystem, no inherited secrets, network disabled by default, CPU/memory/time limits. Python subprocess alone is not a security sandbox.
- Keep a signed/hashed release manifest, dependency lock file, SBOM, change log and rollback pointer.
- No automatic merge to `main`. Draft PR first; merge only after all CI gates and device acceptance tests pass.

### G. Android / Termux runtime
- Termux remains CPU-first and cloud optional. Do not promise always-on microphone behavior across Android versions or OEM battery policies.
- Start listening only from an explicit foreground user action and after microphone permission; provide a persistent notification and immediate stop.
- Android 14+ microphone foreground services require correct service type and while-in-use permission; background-start restrictions apply. A Termux shell + wake-lock is not equivalent to a native foreground microphone service.
- Separate optional native Android companion/service from the Termux core if reliable screen-off listening is a hard requirement.
- Battery, thermal, network and memory state are runtime inputs; degrade gracefully (lower polling, pause local models, queue nonurgent work).

## 3. Research-informed design decisions

1. OpenAI tool/function calling is a multi-step application-controlled loop; tool execution and returned results must be handled by the host application. Keep authorization and execution outside model-generated text.
2. OpenAI guidance recommends limiting initially exposed tools and deferring large tool surfaces; use task-specific tool subsets rather than exposing every phone capability to every agent.
3. Ollama supports tool calling and JSON-schema structured outputs, making it a candidate optional local adapter when device resources permit; benchmark on target phone before enabling.
4. LangGraph describes durable execution, streaming and human-in-the-loop for long-running stateful agent workflows. VISUAL can implement the required state machine directly in lightweight Python/SQLite first; adding a large framework on Android is not mandatory.
5. OWASP agentic security highlights tool misuse, prompt injection, excessive agency, identity/privilege abuse, supply-chain compromise, unexpected code execution and memory/context poisoning. These become explicit security test categories.
6. SQLite FTS5 offers local full-text retrieval suitable for a low-dependency baseline; optional embeddings can be added after RAM/latency benchmarks.
7. Android microphone foreground-service restrictions are platform rules, not bugs a Termux retry loop can reliably bypass.

## 4. Delivery phases and hard gates

### Phase 0 — baseline inventory (no feature deletion)
- Enumerate every tool, provider adapter, config key, CLI mode, plugin, background thread, data file and external command.
- Build call graph and dependency map from entry point to each feature.
- Map README claims to source symbol + test + real-device evidence.
- Identify dead/duplicate files by references and loader behavior; delete only proven unreachable duplicates after backup.

**Gate:** 100% of discovered public tools/features have an inventory row; no unknown data directory is removed.

### Phase 1 — stability and test foundation
- Fix updater and launcher semantics; never print success after a failed fetch/pull/push.
- Add isolated unit tests for router, schema validation, tool confirmation, backup/restore, plugin load failures, task resume and data sync secret filtering.
- CI matrix for supported Python versions; pin dependencies and test Termux-specific differences.
- Test failure injection: network off, 429, 401, 5xx, disk full, malformed JSON, process kill, corrupt memory and low storage.

**Gate:** all CI jobs green; backup restore test passes; updater can roll back from injected failure.

### Phase 2 — provider gateway
- Preserve 16 adapters; verify each provider's current model catalog, authentication, tool calling, structured output, timeout, rate limits and actual key availability.
- Build capability matrix and mock contract tests; run live smoke tests only for keys the owner has configured.
- Add cost/free-tier telemetry without assuming any service is permanently free.

**Gate:** no unsupported provider is selected for a required capability; fallback tests cover 401/429/5xx/model-retired cases.

### Phase 3 — orchestrator and agent workflow
- Convert existing Engineer task into durable state machine with checkpoints and bounded budgets.
- Add planner/researcher/verifier/coder/tester/security reviewer as constrained roles over shared task artifacts.
- Require independent evidence for completion and explicit approval for risky actions.

**Gate:** crash/restart resumes safely; duplicate task execution is idempotent; budget exhaustion stops cleanly.

### Phase 4 — research and memory
- Add source ledger and claim-level citations.
- Migrate memory to SQLite with FTS5, preserving old JSON and enabling export/restore.
- Add provenance, retention, correction and deletion tests.

**Gate:** each research claim traces to evidence; memory migration round-trips without loss.

### Phase 5 — plugin security and self-repair
- Introduce manifests, capability grants and explicit plugin registration.
- Add sandbox runner and security regression suite.
- Make repair pipeline create draft PRs only.

**Gate:** malicious plugin/web prompt cannot access secrets, arbitrary files, phone tools or write permissions without an explicit grant.

### Phase 6 — Android device validation
- Test on actual target phone: permissions, screen-off, notification stop, wake lock, network transitions, reboot, Doze/battery optimization, audio quality, memory and thermal.
- Document Android version, Termux version, Termux:API version, device model and exact results.

**Gate:** no claim of stable background listening until repeatable device tests pass.

## 5. Acceptance matrix (must be completed before declaring complete)

| Area | Required evidence |
|---|---|
| Existing features | inventory + regression tests for every tool and CLI mode |
| 16 providers | per-provider capability and live smoke-test report where keys exist |
| Router | deterministic route tests, cooldown, rate-limit, fallback and key-rotation tests |
| Agents | task state machine, checkpoint/restart, idempotency, budgets, approval tests |
| Research | source ledger, citation integrity, conflicting-source handling, search-failure tests |
| Memory | JSON migration/restore, FTS retrieval, provenance, retention and deletion tests |
| Plugins | manifest validation, permission-denial tests, malicious input tests |
| Self-repair | isolated sandbox, patch test, backup, staged rollout and rollback test |
| Security | prompt injection, secret leakage, privilege escalation, unsafe tool call tests |
| Termux | real device permission, audio, screen-off, wake-lock, reboot, low-resource tests |
| Release | all CI green, draft PR reviewed, no main merge until gates pass |

## 6. Explicit non-goals / honest constraints

- No guarantee that all 16 providers offer free quota, remain available, or expose identical tools/models.
- No claim that 6 GB Android phones can run large local LLMs at useful speed; benchmark small quantized models individually.
- No unrestricted self-modification, arbitrary internet code execution, autonomous payments or silent messaging.
- No promise that Termux alone can override Android microphone/foreground-service restrictions.
- No deletion of a feature just because it is not currently tested; mark it unverified and preserve it.

## 7. Primary research references

- OpenAI tools overview: https://developers.openai.com/api/docs/guides/tools
- OpenAI function calling flow: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI guidance on tool surface size: https://developers.openai.com/api/docs/guides/function-calling
- Ollama API, tool calling and structured outputs: https://github.com/ollama/ollama/blob/main/docs/api.md
- LangGraph durable agent orchestration: https://docs.langchain.com/oss/python/langgraph/overview
- OWASP Agentic Applications 2026, tool misuse: https://genai.owasp.org/agentic-applications-2026/asi02-tool-misuse-and-exploitation/
- OWASP LLM risks: https://owasp.org/projects/top-10-for-large-language-model-applications/
- SQLite FTS5: https://www.sqlite.org/fts5.html
- Android microphone foreground service restrictions: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- Android foreground service types: https://developer.android.com/about/versions/14/changes/fgs-types-required

## 8. Current implementation status

- The existing VISUAL baseline and current Patch 1 changes are preserved on the working branch.
- Patch 1 CI has passed Python 3.11, 3.13 and 3.14 compilation + current mocked plugin tests.
- The full target architecture in this document is not yet implemented.
- Physical Android/Termux validation has not yet been performed.
- This document is the scope and acceptance contract for subsequent incremental implementation; it is not a release-complete declaration.
