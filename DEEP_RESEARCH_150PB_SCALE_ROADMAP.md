# VISUAL — GitHub-Only Data Lake Plan (150 PB Aspirational Target)

**Storage preference:** Keep VISUAL code, metadata, manifests, and any data GitHub permits in the same GitHub repository/account. Do not silently send datasets to another provider.

## Reality and hard limits

The long-term target is **150,000 TB (150 PB)** of unique, verified, license-cleared research data. This is a target, not collected volume.

Current official GitHub limits checked 2026-11-26:
- Git repository: GitHub recommends keeping on-disk repository size around 10 GB; push size is capped at 2 GB; regular Git files over 100 MiB are blocked. Recommended repo size is ideally under 1 GB and strongly under 5 GB. Sources: https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits and https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
- Git LFS: Free/Pro includes 10 GiB storage and 10 GiB monthly bandwidth; Free/Pro max LFS object is 2 GB. Paid metered usage is possible with billing enabled; without payment method/allowance, pushes stop when quota is exceeded. Source: https://docs.github.com/en/billing/concepts/product-billing/git-lfs and https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage
- Actions artifacts: GitHub Free currently includes 500 MB artifact storage; Actions cache is not a permanent data lake. Source: https://docs.github.com/en/actions/reference/limits
- Releases can distribute binaries, but each individual asset is still subject to GitHub's per-file limits. Source: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github

Therefore, GitHub-only storage can be expanded with Git LFS billing and Release assets, but **150 PB cannot be provisioned by a repository setting, workflow, or free account**. It would require an extraordinary GitHub-approved enterprise-scale storage arrangement and written confirmation from GitHub. Do not attempt to evade limits with many repos, accounts, or artificial shards.

## GitHub-native layout

- Git repository: code, schemas, documentation, small catalog files, checksums, and manifests only.
- `datasets/`: local staging layout; large binary extensions are configured for Git LFS via `.gitattributes`.
- Git LFS: large dataset objects only after LFS is enabled and account billing/quota has been reviewed.
- GitHub Releases: immutable, versioned dataset bundles within individual asset limits.
- Actions artifacts: short-lived run reports and small validation outputs only; never use as permanent dataset storage.

## Enablement required in GitHub account

1. Open GitHub Settings → Billing and licensing → Metered usage / Git LFS usage.
2. Review the account's LFS storage and bandwidth allowance, payment method, and budget cap. A zero budget stops over-quota use; removing the budget may allow metered charges.
3. Confirm the intended paid budget before any large upload. Do not enable unlimited spending automatically.
4. Install Git LFS on the upload machine and run `git lfs install`.
5. Check `git lfs track` patterns in this repository, commit `.gitattributes`, then push only a small test file first.
6. Verify the object appears in GitHub LFS usage and can be downloaded with a matching SHA-256 before increasing the batch size.

This repository cannot change account billing settings or accept charges on the user's behalf. No large upload should start until the account's paid LFS allowance is confirmed.

## Data governance and Deep Learning quality

Every dataset must have a record containing canonical provider and dataset ID, URL, exact version/date, item-level license, permitted purpose, attribution, declared and actual bytes, SHA-256, MIME/file signature, subject/domain tags, provenance, privacy/safety review, deduplication key, quality score, and train/validation/test assignment.

Keep distinct measurements for:
- metadata bytes;
- downloaded bytes;
- checksum-verified bytes;
- license-cleared bytes;
- unique bytes after deduplication;
- quarantined/rejected bytes;
- training-ready bytes.

Never treat metadata, a URL, a catalog entry, an LFS pointer, or a queued workflow as downloaded payload. Never count the same data twice. Separate raw, cleaned, normalized, labeled, train, validation, and test partitions. Split by dataset/source/entity to prevent leakage. Data collection is not model training; weights, compute, fine-tuning, evaluation, and safety tests are separate.

## Verified current collection baseline (2026-11-26)

Workflow: https://github.com/bhupendarsingh785/Visual/actions/runs/45766635225

- 300 provider-query tasks attempted.
- 216 indexed results; 84 errors/insufficient-readable-content outcomes.
- 28,574,610 indexed characters reported.
- SQLite: 970 sources, 639 indexed sources/documents, 43,429 chunks, 285,016,064 database bytes.
- SQLite integrity check: `ok`.
- Workflow artifact ZIP: 49,996,545 bytes (about 47.7 MiB), report plus SQLite index.
- This is mainly metadata and indexed text, not bulk dataset downloads.

## Scale-up gates

1. Verify Git LFS billing and a small round-trip test.
2. Upload and verify a 1–5 GB licensed pilot using LFS/Release assets within current limits.
3. Measure actual storage charges, bandwidth, transfer speed, restore, integrity, and duplicate ratio.
4. Increase only after explicit account budget approval and verified capacity.
5. For TB/PB targets, obtain written GitHub enterprise capacity approval before building a larger pipeline. If GitHub will not contractually provide the required capacity, the 150 PB target is not achievable under a GitHub-only constraint.

**Honesty rule:** publish actual GitHub-stored unique verified bytes and the remaining target gap. Never claim 150 PB is stored until manifests and provider-side usage prove it.
