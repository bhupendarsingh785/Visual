# VISUAL Public Knowledge Base

## Goal
A persistent, local-first research corpus that VISUAL can retrieve while planning, coding,
debugging, testing, and researching. It is separate from private user memory and self-audit logs.

## Current implementation
- SQLite + FTS5 full-text index at `~/.visual/knowledge.sqlite3`.
- Source provenance: canonical URL, domain, topic, license/terms label, fetch time, ETag,
  Last-Modified, SHA-256 content hash, status and error.
- Deduplicated documents and overlapping text chunks.
- Search returns excerpts with source URL and license label.
- User/agent must explicitly add a URL, then explicitly ingest it.
- HTTPS only on port 443; DNS-resolved non-global/private IPs blocked and revalidated before requests/redirects; robots.txt checked;
  2 MiB per-response cap; text/HTML/JSON/XML only; obvious secret-like strings redacted.
- No recursive crawling, no private repositories, no credential-bearing URLs.
- Global research collector: 15 allowlisted APIs across 100 subject areas; up to 300 provider-query tasks per run and 25 metadata records requested per task.
- Dataset registry: 152 curated entries, 15 metadata connectors enabled, and 0 automatic bulk-download entries enabled; every file still needs item-level rights and storage review.
- GitHub Actions collection schedule: every six hours; collection report and SQLite index are retained as a 30-day artifact. A task count is not a record count; inspect the report for actual successes and failures.
- Provider-specific pacing for Crossref, Zenodo, PubMed, arXiv, Europe PMC, Wikidata, Hugging Face, Stack Exchange, GBIF and NASA; transient 429/5xx and network failures use bounded retries.
- Global research cursor persists across manual runs and rotates across the full provider-query queue; scheduled runs also advance the batch offset.

## Knowledge policy
Prioritize official documentation and permissively licensed material:
Python docs, Android/Termux docs, SQLite docs, MDN, GitHub docs, PyPI/npm package
documentation, RFCs, OWASP, standards, research papers with reuse terms, and public
Git repositories whose licenses permit the intended use. Store source metadata and
prefer links/excerpts; do not assume public means public-domain or unrestricted reuse.
Do not ingest personal data, leaked secrets, private repos, paywalled content, or
robots-disallowed pages.

## Continuous operation (next integration stage)
A GitHub Actions metadata collector now runs every six hours. This is cloud-side API metadata collection, not a 24/7 Android worker. A separate on-device worker remains a future integration and should run only while VISUAL is active / Android allows it:
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


## Curated global starting catalog
`sources_catalog.json` currently lists official documentation and open-knowledge starting
points across programming languages, web standards, Android/Termux, databases, AI/ML,
security, scientific research, education, archives, and space/climate science.
`knowledge_queue_catalog` adds these URLs to the local queue; it does not mass-download
them. Each source must still pass robots.txt, technical safety checks, and its own license
or terms review before ingestion. This is a curated seed list, not a complete world corpus.

## Offline independence
Once material is indexed, local full-text search works without internet. Live web access is
an optional way to discover/update information, not a runtime requirement for searching
already stored knowledge. The system must clearly label stale or unverified knowledge.


## Offline local dataset ingestion
`knowledge_import_local` imports user-owned or reuse-permitted local files directly into the same SQLite/FTS index; it does not need internet. It supports TXT, Markdown, RST, HTML, CSV, JSON, JSONL/NDJSON, XML and gzip-compressed variants. JSONL.GZ is the recommended format for very large datasets because records are read one at a time. Re-running an import deduplicates records by file hash + record number + content hash. Large imports use one SQLite session with batched commits rather than reconnecting for every record; malformed JSONL lines are counted and retained for inspection.

Allowed paths are restricted to `~/.visual`, Android shared `Download`, and `Documents` folders. Example tool call from VISUAL:
```json
{"name":"knowledge_import_local","args":{"path":"/storage/emulated/0/Download/my_dataset.jsonl.gz","topic":"science","max_records":0}}
```
`max_records: 0` means process until EOF. Large imports should be run while the phone is charging and with sufficient free storage. The importer stores an index/copy of extracted text in SQLite; it does not delete the original dataset. It is not yet a Parquet importer or a vector/embedding index.

## Large public data sources (download selectively)
- Wikidata structured entity data is CC0; other namespaces and media may carry different terms. Prefer the JSON entity dumps or incremental dumps and process line-by-line; the full dump is not phone-sized. See [official download and license notes](https://www.wikidata.org/wiki/Wikidata:Database_download).
- OpenAlex public snapshot is free to download anonymously, but the full JSONL snapshot is roughly 745 GB compressed as of the September 2026 release; select entity/date partitions instead of attempting the full snapshot on a phone. See [snapshot format and manifest](https://help.openalex.org/access/snapshot/).
- NASA's open-data portal is a catalog of thousands of public science datasets; each underlying dataset has its own access and reuse terms. See [NASA Open Data](https://data.nasa.gov/).

## Verified research-source registry

`research_sources_registry.json` lists 15 priority research repositories and official portals for biodiversity, animal sounds, marine ecosystems, neuroscience, medicine, engineering and AI. It records the access method, dataset-level rights caveats, collection status and quality checks. Registry presence is discovery metadata only; it does not mean the source has been harvested, a media file has been downloaded, or a license has been granted. Validate the JSON and ensure every listed domain exists in `global_research.py` before expanding the collector.
