# VISUAL Deep Learning & Data Strategy

## Four separate systems (do not conflate them)

1. **Source collection:** discover public records and datasets; record source URL, retrieval time, license, attribution, checksum and access method.
2. **Knowledge/RAG index:** chunk and index retrieved material. This improves evidence retrieval; it does not change neural-network weights.
3. **Training corpus:** curate, deduplicate and filter rights-eligible examples; preserve lineage and deterministic train/validation/test splits.
4. **Model training:** tokenize the approved corpus, fine-tune a pretrained model (initially SFT/LoRA), evaluate, version checkpoints and retain rollback evidence.

## Training order and quality gates

- Start from a pretrained base model; do not attempt foundation-model pretraining on GitHub Actions.
- Establish held-out Hindi/English reasoning, factuality/citations, coding, safety, instruction-following, retrieval and regression evaluations before training.
- Begin with a small, reproducible SFT or LoRA experiment. Consider preference optimization only after reliable preference pairs and a baseline exist.
- Never train directly on raw scraped text. Filter spam, boilerplate, duplicates, secrets, personal data and low-quality OCR; retain source-level lineage.
- Keep medical, legal and financial content sourced and retrieval-grounded.
- Publish dataset cards, model cards, training configs, evaluation results and checkpoint hashes.

## Current implementation boundary

`plugins/knowledge_base/training_prep.py` exports already-indexed KB documents into JSONL train/validation/test staging files. It accepts explicit permissive license labels and narrowly labeled CC0 metadata sources, excludes unknown/restrictive labels, deduplicates by content hash, and keeps documents from a source domain in one deterministic split. It writes outputs atomically. This is corpus preparation only: no tokenizer, training, fine-tuning, model weights or benchmark execution is implemented by this module.

The global collector searches 15 allowlisted public APIs and has 70 domain keys. It is deliberately bounded to 300 provider-query tasks per run, with at most 25 records requested per task (some APIs impose lower limits). Its results are primarily API search metadata, not complete datasets, full-text corpora or model-ready examples. The dataset catalog has 152 entries; bulk-download flags remain disabled pending item-level rights, manifest, size and access checks.

### Latest inspected collection evidence (2026-11-26)

Artifact: `visual-public-knowledge-45766635225` (49,996,545 bytes; GitHub Actions run 45766635225).

- 300 provider-query tasks attempted; 216 indexed outcomes; 84 failures or responses rejected for insufficient readable content.
- 28,574,610 indexed characters.
- Persistent local KB snapshot: 970 sources, 639 indexed documents, 43,429 chunks; SQLite `PRAGMA integrity_check = ok`.
- Source statuses in the snapshot: 639 indexed, 149 blocked, 149 error, 33 queued.
- The report's topic counts show **zero documents tagged `deep_learning` in this snapshot**. Deep-learning query coverage exists in the research map, but a topic key is not proof that suitable training data has been collected.
- Run stopped at the configured 300-task cap; cursor moved from 1290 to 1590 of 2115 provider-query tasks. This is not proof that all topics or all providers have been exhaustively searched.

Treat these figures as a verified metadata-index snapshot only. The 84 outcomes are not all necessarily provider outages: many are short/empty search responses that the indexer correctly declined to treat as useful documents.

## GitHub-only storage policy

The project owner has explicitly chosen GitHub as the storage platform. Do not silently redirect dataset storage to S3, Hugging Face, Google Drive or another object store.

- Keep source code, small manifests, dataset cards, checksums, provenance and compact reports in ordinary Git.
- The root `.gitattributes` configures Git LFS tracking patterns for common binary dataset and model formats under `datasets/`. This is only a tracking configuration: it does **not** enable account billing, provision quota, install the local LFS client or upload any LFS payload.
- Use Git LFS for eligible large objects only after the account's storage/bandwidth budget and per-file limits are confirmed. Split large datasets into independently checksummed shards that respect the applicable per-file maximum.
- Use GitHub Releases for immutable, versioned bundles where each asset respects the applicable upload limit. Use Actions artifacts only for temporary run outputs, not as a permanent data lake.
- Do not commit large binaries directly into ordinary Git history; do not place secrets or private/personal data in the repository.
- GitHub limits are hard constraints, not settings that repository code can override. Current standard Free/Pro LFS allowances and per-file limits are finite; GitHub Actions artifact storage is also finite. A 150 PB target is **not provisioned or achievable under ordinary GitHub quotas**. It would require explicit written GitHub Enterprise capacity/contract confirmation before any claim that GitHub can host it. Never multiply accounts/repos to evade service limits.

## Acceptance gates before claiming Deep Learning readiness

- Dedicated deep-learning dataset discovery must produce real dataset records, not only API search-result metadata.
- Every candidate needs a dataset card, source/license/attribution, schema, size, checksum and version.
- Review representative samples for quality, language coverage, duplicates, contamination, personal data and benchmark leakage.
- Build reproducible tokenization/preprocessing and streaming/sharding tests.
- Export a rights-approved corpus; report exact train/validation/test counts and exclusions.
- Run a small baseline fine-tune only on suitable compute, record configuration and checkpoint hash, then compare held-out metrics and regressions.
- CI must pass on Python 3.11, 3.13 and 3.14; collection smoke tests must respect request budgets and backoff.
- No claim of complete collection, trained model, error-free system or available storage capacity without artifacts and verification proving it.

## Expanded global research map and verified source registry (2026-11-26)

The collector's research map now contains 100 subject keys. The priority source registry is `plugins/knowledge_base/research_sources_registry.json` and currently records 15 authoritative portals or repositories across biodiversity, animal bioacoustics, marine ecosystems, neuroscience, medicine, earth observation, AI datasets and scholarly metadata. Registry entries are discovery leads, not harvested-data claims.

High-priority source-specific constraints:
- GBIF exposes documented taxonomy and occurrence APIs, but records carry different licenses and data-quality uncertainty; preserve source attribution and uncertainty.
- OBIS offers marine biodiversity records and large GeoParquet exports. Its integrated export is CC BY-NC, and source datasets can have different licenses; do not treat the entire export as commercial-training material.
- The Museum für Naturkunde Berlin Animal Sound Archive has a large collection; GBIF's occurrence record lists CC BY 4.0, but linked audio-file reuse must be checked separately with the archive.
- Xeno-canto requires API v3 access credentials and each recording has its own Creative Commons license; non-commercial and share-alike terms are common.
- iNaturalist explicitly warns against treating its API as a bulk-scraping channel. Observation records and media have distinct licenses, and presence-only observations are subject to observer bias.
- OpenNeuro provides BIDS-formatted MRI, PET, MEG, EEG and iEEG datasets; human-subject privacy, consent and dataset-level checks remain mandatory.
- NEMAR hosts EEG, MEG, iEEG and EMG datasets with per-dataset license filters; do not assume all hosted datasets are public domain.
- Allen Brain Map resources are governed by Allen Institute terms and citation policy, not a blanket CC0 declaration.

Evidence used to seed this registry includes official GBIF API and terms documentation, OBIS data access and policy pages, the Museum für Naturkunde Berlin archive, Xeno-canto API information, iNaturalist developer guidance, OpenNeuro documentation, NEMAR dataset discovery, NIH BRAIN archive guidance and Allen Institute terms. Re-check source terms at collection time because policies and datasets can change.

## Accuracy and provenance protocol

1. Store raw provider response separately from normalized records; never overwrite the source payload with a model-generated interpretation.
2. Keep exact source URL, source ID, retrieval timestamp, dataset version, license evidence, attribution, checksum and parser version.
3. Validate identifiers, taxonomic names, timestamps, units, coordinates, modality and schema; quarantine invalid or contradictory records.
4. Mark uncertain, inferred, missing and human-annotated fields distinctly. Never convert uncertainty into ground truth.
5. For animal audio/video, preserve original media and recording context; validate species label confidence, recorder, sample rate, duration, habitat, date and location precision.
6. For human brain/clinical data, require privacy, consent, de-identification and applicable data-use approvals before ingestion or training.
7. Split model datasets by subject/individual, recording session, location, source or study as appropriate to prevent train/test leakage.
8. Generate a validation report with accepted, rejected, duplicate, unknown-license and human-review counts. Do not silently discard failures.
9. Run regression tests on parsers and provider connectors; verify database integrity and artifact checksums after every collection.
10. Do not claim training readiness until a reviewed corpus manifest, sample audit, baseline evaluation and reproducible training run exist.
