# Global Dataset Expansion

VISUAL's curated web-page catalog is only a seed list. This registry is a broader discovery layer for global public data.

## Registry

- `datasets_catalog.json` lists 55+ public dataset families across research, health, education, programming, standards, biodiversity, climate, geospatial, humanities, economics, agriculture and India-specific public data.
- Each entry records access pattern, region, approximate size class and a license/rights warning.
- Entries are disabled by default. Listing a dataset does not mean it has been downloaded, verified, or approved for reuse.

## Required ingestion pipeline before bulk downloads

1. Discover dataset metadata and authoritative manifests from the publisher.
2. Verify license and rights at dataset/record/file level; public access is not a reuse license.
3. Estimate bytes, storage, bandwidth, CPU, memory and battery cost.
4. Select partitions, years, topics, languages or records; never automatically pull an entire multi-terabyte corpus to a phone.
5. Download with HTTP range/resume, ETag/Last-Modified, checksum verification, retry/backoff and atomic rename.
6. Store source provenance, manifest version, retrieval time, license, checksums and transformation history.
7. Parse incrementally (JSONL/CSV/Parquet/ XML dumps where supported), deduplicate, chunk and index.
8. Run quality checks, record errors, support pause/resume, and expose progress/space estimates in the browser panel.
9. Keep raw data and the searchable index distinct so the index can be rebuilt.

## Phone-first strategy

- Default to catalog metadata + selected API records + small curated documents.
- Large sources such as Common Crawl, OpenAlex snapshots, Wikidata dumps, OSM planet and satellite archives require selective partitions or an external disk/server; do not promise they fit on a phone.
- Prefer JSONL/CSV/Parquet partitions and incremental APIs. Avoid loading entire files into RAM.
- Use SQLite/FTS for the initial searchable store; add a vector index only with measured memory/storage budgets.
- Offline answers must cite local source metadata and state when the local corpus has no evidence.

## Intelligence boundary

The knowledge base is retrieval-augmented context, not model-weight training. It can make VISUAL more informed and useful offline after indexing, but independent reasoning also needs task planning, tool execution, source comparison, contradiction detection, confidence estimates, memory, tests and safe permission gates. No system can know all world data or be perfectly independent.
