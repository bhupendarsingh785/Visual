# VISUAL Deep Research Collection Notes

- Research date: 2026-11-26
- Scope: authoritative discovery and acquisition planning for AI/ML, multimodal, science, environment, and India public data.
- Status: source research and acquisition leads only; no dataset payloads were downloaded by this research note.
- Rule: do not count catalog records, API metadata, compressed source sizes, or search results as stored corpus bytes.

## High-value source findings

| Area | Source | Verified access facts | VISUAL action |
|---|---|---|---|
| Machine learning / benchmarks | OpenML — https://www.openml.org/ and https://docs.openml.org/data/use/ | Open platform with thousands of datasets, tasks, runs and reproducibility metadata; API supports filtered dataset discovery and loading. | Add API-based dataset-card discovery; persist dataset ID, version, size, format, licence, tasks and checksum before selective download. |
| India government data | OGD India — https://data.gov.in/ and https://data.gov.in/catalogs | Portal search result reported 12,636 catalogues, 358,259 resources and 162,244 APIs; catalog pages expose dataset/resource records and API/download options. Portal page also reports maintenance notice, so API availability must be tested. | Prioritize CSV/API metadata for agriculture, health statistics, climate, education, transport, economy and science; record ministry, update date and Government Open Data License-India per resource. |
| Web-scale text corpus | Common Crawl — https://www.commoncrawl.org/get-started and https://www.commoncrawl.org/about | Public crawl archives are freely accessible via HTTPS; archive exceeds 10 PiB and crawls contain billions of pages. | Do not mirror the whole archive. Select crawl indexes and WARC ranges by domain/language/topic, filter robots/rights/privacy, deduplicate URLs and content hashes, and stream only selected records. |
| Space/life sciences/multimodal | NASA Open Science Data Repository — https://science.nasa.gov/biological-physical/data/osdr/ and https://api.nasa.gov/ | OSDR contains multi-modal data: omics, phenotype, physiology, behaviour, biomedical imaging, environmental telemetry, hardware, text, code, images and video. API supports search, metadata and file discovery. | Add study-level discovery; inspect study version, file manifest, human/animal subject constraints, terms and byte sizes before downloading. |
| Broad dataset discovery | OpenML docs — https://docs.openml.org/concepts/data/ | Search filters include size/type/format; API exposes dataset metadata and direct loading. | Use OpenML as a dataset index, not as proof that all linked datasets have identical reuse rights. |

## Prioritized acquisition plan

1. **Small, high-value structured data first:** OpenML metadata and selected benchmark datasets; OGD India CSV/API resources; NASA OSDR metadata and selected public files.
2. **Scientific text and records:** OpenAlex/Crossref metadata, Europe PMC open-access records after article-level licence filtering, Zenodo/Figshare/Dataverse records with per-record licences.
3. **Multimodal:** NASA OSDR image/video/telemetry; licensed speech/audio corpora; GBIF/OBIS occurrence records; crop disease imagery from India OGD where the record licence permits.
4. **Web scale last:** Common Crawl selective WARC extraction only. Never download petabyte-scale archives blindly.

## Mandatory ingestion gates

- Check source terms, licence, attribution, privacy/consent and commercial-use restrictions at the item/file level.
- Fetch manifest first; estimate compressed and expanded bytes; require free-space headroom before transfer.
- Use resumable downloads, bounded concurrency, retries with backoff and provider rate limits.
- Verify provider checksum where available and calculate SHA-256 locally.
- Deduplicate by source-native ID, canonical URL, file checksum and normalized content hash.
- Preserve source URL, access timestamp, dataset version, licence text/URL, citation, schema, modality, byte count and checksum.
- Quarantine malformed, unsafe, personal, restricted or licence-unclear payloads.
- Report separately: discovered records, eligible records, downloaded files, verified bytes, indexed documents and duplicate bytes avoided.
- Keep raw payload storage outside ordinary Git history; GitHub Actions artifacts are transient and are not a 2 TB data lake.

## Important distinction

This document is research metadata and a plan. It is not evidence that any listed dataset has been downloaded, licensed for every use, or stored in VISUAL. A 2 TB target is reached only when 2,000,000,000,000 bytes of unique eligible payloads are downloaded, checksum-verified and durably stored, with a machine-readable manifest.
