# VISUAL Deep Learning & Data Strategy

## Keep four separate systems

1. **Source collection:** find public datasets and records, record source, timestamp, license, checksum and access method.
2. **Knowledge/RAG index:** chunk and index material for retrieval. This improves answers by fetching evidence; it does not change neural-network weights.
3. **Training corpus:** only curated, deduplicated, rights-eligible examples. Preserve source provenance and deterministic train/validation/test splits.
4. **Model training:** tokenize the corpus, train or fine-tune a model, evaluate it, version the checkpoint, and roll back if quality regresses.

## Training order

- Start with a pretrained base model; do not attempt foundation-model pretraining from scratch on GitHub Actions.
- Establish a held-out evaluation suite before fine-tuning: Hindi/English reasoning, factuality with citations, coding tests, safety, instruction following, long-context retrieval and regression.
- Begin with small supervised fine-tuning (SFT) or parameter-efficient adapters (LoRA/QLoRA) on a legally usable, high-quality corpus.
- Consider preference optimization only after reliable preference pairs and a baseline exist.
- Never train directly on raw scraped text. Filter spam, boilerplate, duplicates, secrets, personal data and low-quality OCR; retain source-level lineage.
- Keep medical/legal/financial content sourced and retrieval-grounded; do not treat it as a substitute for professional judgement.
- Separate model weights from the RAG store; publish dataset cards, model cards, evaluation results and reproducible configs.

## Current implementation boundary

`plugins/knowledge_base/training_prep.py` exports already-indexed knowledge-base documents into JSONL train/validation/test staging files. It defaults to a narrow allowlist of explicit permissive license labels and excludes unknown/restrictive labels. It is a preparation stage only: it does not train weights.

The existing global collector currently gathers bounded API search metadata from OpenAlex, Crossref, Zenodo, GBIF and NASA CMR. It is not yet a full global bulk-data mirror. Each dataset file requires its own rights check, manifest parsing, download/resume, checksum verification and streaming parser. API search metadata must not be mistaken for full records or source documents.

## GitHub execution constraints

GitHub Actions is suitable for CI and bounded scheduled jobs, not an unlimited data warehouse or large-scale GPU training cluster. Workflow artifacts and caches are temporary/limited. For sustained multi-terabyte collection, VISUAL needs a separately configured object store or dataset host and explicit credentials; do not commit credentials or huge data blobs into Git history. Keep code and manifests in Git; store datasets and checkpoints externally.

## Acceptance gates

- Unit tests for license gating, deterministic splits, deduplication and provenance.
- Live API smoke tests with request budgets and backoff.
- Bulk-download tests with resume, checksum, size caps and content-type validation.
- Corpus quality report and manual sample review before training.
- Baseline evaluation, training run manifest, checkpoint hash and post-training regression report.
- No claim of trained model or collected record counts until workflow artifacts and logs prove them.
