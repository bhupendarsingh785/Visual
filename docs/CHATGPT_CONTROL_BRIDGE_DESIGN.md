# VISUAL ChatGPT Control Bridge — Design Specification

Status: design only. This document does not implement a phone-side executor.
Target: Android + Termux. VISUAL remains the runtime, data owner and execution authority.

## Existing-system findings

The repository already documents `visual remote`: a temporary Cloudflare Quick Tunnel with email OTP to VISUAL's browser chat panel. The agent, tools and local data remain on the phone. It is a human browser-access path, not by itself a ChatGPT tool connector. The browser API's per-session secret and same-origin Origin/Referer checks must remain enabled.

VISUAL already has a registered tool system with schemas and risky-tool markers; a knowledge-base plugin with `knowledge_collect_global_research`, `knowledge_status`, `knowledge_search`, catalog and dataset tools; and a bounded public metadata collector. The collector is capped at 300 provider-query tasks per run and 25 requested records per task across allowlisted APIs. It indexes search metadata, not complete corpora and not model weights.

## Proposed architecture: private GitHub mailbox

Use the owner's existing **private** `visual-data` repository as an asynchronous command mailbox. Do not use the public VISUAL source repository for private commands or reports.

1. ChatGPT, through the owner's authorized GitHub connection, writes a command envelope to a dedicated mailbox namespace in the private data repository.
2. VISUAL on the phone polls the mailbox using the owner's existing `gh` authentication.
3. VISUAL validates repository identity, expiry, nonce, schema, tool name and typed arguments.
4. VISUAL records the command ID locally before execution, preventing duplicate execution after restart/retry.
5. Risky actions require VISUAL's local owner approval. Remote input cannot override `confirm_risky`.
6. VISUAL runs only a registered tool from a narrow allowlist, on the phone.
7. VISUAL writes a bounded status/result record to the private mailbox. Never upload API keys, secrets, SMS, contacts, private files or unrestricted shell output.
8. ChatGPT reads the report and distinguishes success, partial completion and failure.

This is asynchronous polling, not live RPC. Use conservative polling, exponential backoff offline, and GitHub rate-limit handling.

## Command envelope

Required fields: `schema_version`, unique `command_id`, `created_at`, short `expires_at`, `requested_by`, exact `tool_name`, typed `arguments`, and one-time `nonce`. VISUAL derives approval requirements from its local registry; it must not trust a remote `approval_required` flag.

Reject unknown fields/tools, invalid arguments, expired commands, replayed IDs/nonces, oversized payloads, wrong/public repositories and malformed JSON. Never accept Python, shell commands, arbitrary URLs, arbitrary file paths or code to evaluate.

## Initial allowlist

- `knowledge_status` — read-only.
- `knowledge_search` — bounded local search.
- `knowledge_queue_catalog` — queue curated sources only.
- `knowledge_collect_global_research` — bounded metadata collection; local approval required.
- `knowledge_collect_now` — bounded source ingestion; local approval required.

Do not expose arbitrary shell/Python, code editing, SMS/calls, payments, key management, arbitrary dataset URLs or unrestricted plugin invocation.

## Knowledge and deep-learning boundaries

Canonical database remains on the phone at `~/.visual/knowledge.sqlite3`. Mailbox stores command envelopes and bounded reports, not the database itself.

Preserve source URL, provider, retrieval time, topic, license/terms note, content hash, status and attribution. Unknown, non-commercial, no-derivatives, restricted or unclear rights must not silently become training-eligible.

Keep these stages separate:
1. Metadata discovery.
2. Item-level license/terms review.
3. Selective full-text/dataset download with size and checksum limits.
4. Deduplication, quality filtering and source-domain-aware train/validation/test split.
5. Training-data preparation.
6. Model fine-tuning/training.
7. Evaluation, checkpointing and rollback.

RAG/FTS indexing is knowledge retrieval, not neural-network weight training. Never describe metadata collection as deep-learning training.

## Security and recovery

- Verify the configured mailbox is private and matches the exact expected repository.
- Reuse phone-side `gh auth`; never copy tokens into commands or logs.
- Treat mailbox contents as untrusted, even in a private repo.
- Keep local owner confirmation and the tool allowlist enforced.
- Use local durable deduplication, atomic status writes, bounded outputs and secret redaction.
- Apply provider pacing, Retry-After, bounded retries and cancellation.
- Fail closed on malformed input, expiry, auth failure or database-integrity failure.
- Remote cancel may stop only a bridge-owned task; it must not terminate VISUAL or disable safeguards.

## Acceptance tests

1. Verify exact private repository identity/visibility.
2. Complete harmless `knowledge_status` command round-trip.
3. Reject wrong/public repository, unknown tool, invalid schema, expired command and replay.
4. Prove risky actions still require local owner approval.
5. Prove shell/Python/arbitrary URL/file access cannot be requested.
6. Restart during a task and prove no duplicate execution.
7. Simulate offline, 401/403/404/429/5xx, malformed JSON and oversized payload.
8. Verify secrets never appear in logs, mailbox or reports.
9. Run collector on the real phone; verify SQLite `PRAGMA integrity_check`, database deltas and provider counts.
10. Measure Android battery, data use, RAM, CPU temperature and sustained runtime.

## Implementation order

A. Inspect the private data-sync format and authentication path; reserve a non-colliding mailbox namespace.
B. Implement read-only phone-side polling, strict validation, replay protection and reporting; test against a fake GitHub API.
C. Add the narrow knowledge-tool allowlist and local approval gate; keep disabled by default.
D. Add ChatGPT-side mailbox write/read through the authorized GitHub connection; test `knowledge_status` first.
E. Enable bounded collection only after the owner approves the first live phone run and local SQLite integrity is verified.
F. Design the training executor separately, after the data pipeline is proven.

## Non-goals

Not a public command endpoint, not unrestricted phone control, not a cloud copy of the phone database, not a bypass for Android permissions or owner approval, and not a replacement for VISUAL's local agent.
