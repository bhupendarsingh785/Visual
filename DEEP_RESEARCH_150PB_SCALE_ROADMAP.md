# VISUAL — Deep Research and 150 PB Data-Scale Roadmap

**Status:** target/architecture plan, not a claim that 150 PB has been collected.

## Target

- Long-term aspirational target: **150,000 TB (150 PB decimal)** of legally reusable, quality-checked research data and datasets.
- Count only bytes that have actually been downloaded, checksum-verified, license-reviewed, and registered in the durable dataset manifest.
- Keep metadata bytes, downloaded payload bytes, compressed bytes, extracted bytes, and model-training-ready bytes as separate measurements. Never add the same payload twice.
- This target is not a one-run GitHub Actions artifact target. GitHub repository history and short-lived workflow artifacts are not a suitable 150 PB data lake.

## Current verified baseline (2026-11-26)

From workflow run https://github.com/bhupendarsingh785/Visual/actions/runs/45766635225:

- 300 provider-query tasks attempted.
- 216 indexed results; 84 collection errors/insufficient-readable-content outcomes.
- 28,574,610 indexed characters reported by the collector.
- SQLite index: 970 sources, 639 indexed sources/documents, 43,429 chunks, 285,016,064 database bytes.
- SQLite `PRAGMA integrity_check`: `ok`.
- Workflow artifact ZIP: 49,996,545 bytes (about 47.7 MiB), containing the report and SQLite index.
- These are primarily search metadata and indexed text, **not 150 PB of downloaded source datasets** and not model training.

## Collection architecture required to approach 150 PB

### 1. Research discovery and registry
Maintain a versioned registry of datasets, repositories, papers, model weights, benchmark sets, media corpora, scientific archives, and public data portals. Record provider, dataset ID, canonical URL, subject tags, update date, declared size, format, license, attribution, access restrictions, privacy/safety review, and provenance.

### 2. Rights and quality gate
Before downloading a payload:
- Confirm item-level license and permitted use; reject unknown, non-commercial, no-derivatives, restricted, or incompatible items from training unless explicitly approved.
- Exclude personal/sensitive data, credentials, malware, and unsafe payloads.
- Validate MIME type, file signature, archive paths, decompression limits, and source authenticity.
- Compute SHA-256; deduplicate by content hash and canonical dataset version.
- Keep quarantine separate from approved research/training data.

### 3. Durable storage and transfer
Use GitHub only for code, manifests, small reports, and orchestration. Store large payloads in durable object storage or a controlled data-lake service with documented capacity, lifecycle, replication, access control, egress cost, and restore tests. Use resumable multipart transfers, per-object checksums, retry/backoff, and immutable manifests. Do not put huge binary datasets in Git history or workflow artifacts.

### 4. Staged scale gates
- Stage A: metadata discovery and license-aware registry.
- Stage B: small representative downloads and end-to-end checksum/restore tests.
- Stage C: 1 TB verified pilot.
- Stage D: 10 TB, then 100 TB, with cost, throughput, integrity, deduplication, and restore gates.
- Stage E: PB-scale capacity only after storage funding, provider agreements, and operations are demonstrated.
- Stage F: 150,000 TB long-term target; publish actual verified bytes and remaining gap per stage.

### 5. Deep Learning readiness
Keep separate, versioned partitions for raw, cleaned, normalized, deduplicated, labeled, train, validation, and test data. Split by source/dataset or entity to reduce leakage. Store tokenizer/preprocessing versions, label schema, provenance, license, quality scores, and reproducible manifests. Build domain-specific benchmarks and holdout sets. Data collection alone is not training: model weights, compute, training runs, evaluation, and safety testing are separate milestones.

## Mandatory reporting fields

Every run must report:
- bytes discovered (metadata only), bytes downloaded, bytes checksum-verified, bytes license-approved, bytes quarantined, bytes rejected;
- unique payload bytes after deduplication;
- provider/task success, empty, throttled, timeout, and validation-failure counts;
- per-domain coverage and freshness;
- storage backend, object count, integrity status, and restore-test status;
- training-ready bytes separately from raw bytes.

## Non-negotiable honesty rule

Never describe a target, catalog entry, metadata result, cached index, or queued job as downloaded data. Never claim the 150 PB target is achieved until durable storage manifests prove the verified unique payload total. Current GitHub Actions collection is a small metadata/indexing pipeline and does not have the capacity to store 150 PB.
