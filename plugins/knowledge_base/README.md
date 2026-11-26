# VISUAL Public Knowledge Base

## Goal
A persistent, local-first research corpus that VISUAL can retrieve while planning, coding,
debugging, testing, and researching. It is separate from private user memory and self-audit logs.

## Current implementation
- SQLite + FTS5 full-text index at `~/.visual/knowledge.sqlite3`.
- Source provenance: canonical URL, domain, license/terms label, fetch time, ETag,
  Last-Modified, SHA-256 content hash, status and error.
- Deduplicated documents and overlapping text chunks.
- Search returns excerpts with source URL and license label.
- User/agent must explicitly add a URL, then explicitly ingest it.
- HTTPS only; DNS-resolved non-global/private IPs blocked; robots.txt checked;
  2 MiB per-response cap; text/HTML/JSON/XML only; obvious secret-like strings redacted.
- No recursive crawling, no private repositories, no credential-bearing URLs.

## Knowledge policy
Prioritize official documentation and permissively licensed material:
Python docs, Android/Termux docs, SQLite docs, MDN, GitHub docs, PyPI/npm package
documentation, RFCs, OWASP, standards, research papers with reuse terms, and public
Git repositories whose licenses permit the intended use. Store source metadata and
prefer links/excerpts; do not assume public means public-domain or unrestricted reuse.
Do not ingest personal data, leaked secrets, private repos, paywalled content, or
robots-disallowed pages.

## Continuous operation (next integration stage)
A scheduled queue worker should run only while VISUAL is active / Android allows it:
- refresh due sources with conditional HTTP requests;
- discover new sources from curated catalogs, not arbitrary recursive crawling;
- retry transient errors with exponential backoff and per-domain rate limits;
- cap bandwidth, CPU, database size, and daily fetches on-device;
- expose pause/resume, source removal, export/backup, and storage alerts.
Android Doze and battery policies mean 24/7 background execution cannot be guaranteed.

## Intelligence integration (next stage)
At each research/coding task, query this corpus first, then use live web research for
fresh or missing evidence. Attach citations to generated specs/code comments/reports.
Record task outcome and user-approved corrections as quality signals, not as unquestioned truth.
Do not train model weights automatically: retrieval-augmented generation (RAG) uses
the corpus as context; model fine-tuning is a separate, costly, reviewed process.

## Limits
No free unlimited storage exists. Device storage, bandwidth, source terms, and rate limits
are real limits. Use configurable retention, backups, optional user-owned storage, and
incremental indexing. The index is not yet a verified autonomous crawler or a 24/7 worker.
