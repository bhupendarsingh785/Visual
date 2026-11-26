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

`plugins/knowledge_base/training_prep.py` exports already-indexed knowledge-base documents into JSONL train/validation/test staging files. It accepts explicit permissive licenses and clearly labeled CC0 metadata sources, excludes unknown/restrictive labels, and keeps all documents from the same source domain in one deterministic split to reduce train/test leakage. Outputs are written atomically. It is a preparation stage only: it does not train weights.

The existing global collector searches 15 allowlisted APIs: OpenAlex, Crossref, Zenodo, GBIF, NASA CMR, Hugging Face Datasets, PubMed, Stack Exchange, arXiv, Europe PMC, Wikidata, Openverse Images/Audio, Wikimedia Commons and Internet Archive. Its research map contains 70 domain keys spanning deep learning, computer vision, multimodal AI, medicine, human behaviour/motion, speech/audio, facial movement, semiconductor research, materials science, robotics, history, education and other fields. Each run is bounded to 300 provider-query tasks and up to 25 metadata records requested per task. Scheduled runs execute every six hours; manual runs persist a cursor so repeated requests continue through the task queue instead of repeating the first batch. Actual records returned, indexed and failed are measured in each workflow report; task count is not record count.

This is still metadata harvesting, not a full global bulk-data mirror. The catalog contains 148 dataset entries, but bulk-download flags remain disabled until each dataset's rights, manifest, size and access method are reviewed. Each dataset file requires its own rights check, manifest parsing, resumable download, checksum verification and streaming parser. API search metadata must not be mistaken for full records, source documents, image/audio/video corpora or model training data.

## GitHub execution constraints

GitHub Actions is suitable for CI and bounded scheduled jobs, not an unlimited data warehouse or large-scale GPU training cluster. Workflow artifacts and caches are temporary/limited. For sustained multi-terabyte collection, VISUAL needs a separately configured object store or dataset host and explicit credentials; do not commit credentials or huge data blobs into Git history. Keep code and manifests in Git; store datasets and checkpoints externally.

## Acceptance gates

- Unit tests for license gating, deterministic splits, deduplication and provenance.
- Live API smoke tests with request budgets and backoff.
- Bulk-download tests with resume, checksum, size caps, destination traversal protection and HTTPS-only validation.
- CI matrix for Python 3.11, 3.13 and 3.14; latest commit must be green before release.
- Corpus quality report and manual sample review before training.
- Baseline evaluation, training run manifest, checkpoint hash and post-training regression report.
- No claim of trained model or collected record counts until workflow artifacts and logs prove them.
