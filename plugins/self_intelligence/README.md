# VISUAL Self-Intelligence subsystem

This first implementation adds a persistent, inspectable self-information layer.

## Runtime tools

- `self_intelligence_audit`: take and store a runtime snapshot; inventory tools, plugins, provider definitions, task states and repository files; report deterministic findings.
- `self_intelligence_report`: read the latest snapshot, findings, plans and file-change summary.
- `self_improvement_propose`: create a measurable improvement proposal with scope, rationale, risk/rollback and acceptance tests.
- `self_improvement_update`: change a plan's workflow status. This tool is marked risky and requires the host's approval path.
- `self_improvement_history`: list recent proposals and their acceptance criteria.

## Storage and privacy

The SQLite ledger is stored below VISUAL's existing private runtime home (`~/.visual/self_intelligence.sqlite3`, or the configured HOME used by VISUAL). It stores inventory metadata, not source-file contents or API-key values. Secret-looking filenames are omitted from the inventory. Snapshots are hashed so a saved report can be checked for accidental modification.

## Control model

The subsystem is deliberately observational and proposal-driven. It does not grant permissions, execute generated code, edit the running core, push commits, or self-certify a change as completed. The host must approve a plan, and implementation must go through the existing isolated build/test/review/rollback process. The status `completed` is rejected by the planning layer; independent CI/release verification must own completion.

## Verification

Run locally from the repository root:

```bash
PYTHONPATH=plugins/self_intelligence python -m unittest discover -s plugins/self_intelligence -p 'test_*.py' -v
python -m compileall -q visual.py plugins
```

GitHub Actions also runs the subsystem tests in the Python 3.11/3.13/3.14 matrix. A passing offline test does not prove provider connectivity or Android microphone/background behavior.
