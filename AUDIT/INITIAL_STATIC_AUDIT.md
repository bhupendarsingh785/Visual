# VISUAL initial static audit

Date: 2026-11-26
Target: `main` snapshot at commit `70f6eba368cf46217015f16d93b4f3403204e62d`
Working branch: `upgrade/global-intelligence-v1`

## Scope

Read-only inspection of the repository tree, README, main Python entry point, installer/updater, existing plugin entry points/tests, and browser live client. No device runtime, Android permissions, microphone, API-provider, Telegram, or long-duration test was executed in this audit pass.

## Confirmed structure

- Main runtime: `visual.py` (about 193 KB).
- Browser UI: `web/index.html`, `web/live.js`.
- Plugins: `plugins/continuous_listening`, `plugins/continuous_listening_v2` (spec only), and `plugins/memory_repeat`.
- Shell scripts: `install.sh`, `update.sh`.
- The plugin loader scans only direct children of `plugins/`; directories are loaded when they contain a direct `plugin.py`.

## Findings

### P1 — updater can silently hide deployment failures

`update.sh` ends its Git add/commit/push chain with `|| true`. A failed push or commit is therefore suppressed, after which the script prints that the update completed and starts the app. This can report success when the repository was not updated. The updater also unpacks the newest matching `VISUAL_v*.zip` found under shared storage into the home directory without first validating the archive contents or recording a rollback point.

### P1 — backup/restore and self-upgrade need stronger verification

The main program has backup and self-check mechanisms, but the current self-check verifies import, plugin-load errors, JSON serialization of live tools, and system-prompt construction. It does not execute the full tool suite or Android integrations. A successful self-check must not be treated as proof of device/runtime stability.

### P2 — duplicate and confusing memory plugin layout

The tree contains `plugins/memory_repeat/plugin.py` and a nested `plugins/memory_repeat/plugins/memory_repeat/plugin.py` with the same blob SHA. The loader only scans the top-level `plugins/` directory, so the nested copy is not separately loaded. There is also a separate `memory_store.py` implementation of `MemoryStore`, while `plugin.py` defines its own copy. This increases maintenance ambiguity; do not delete either until references and compatibility are verified.

### P2 — plugin loading executes trusted repository code in the main process

`load_plugins()` uses `exec(compile(...), globals())`. This makes plugins powerful and compatible with shared helpers, but a plugin exception or unsafe plugin code can affect the main process and global namespace. Plugin isolation, explicit registration, and permission boundaries should be considered before adding third-party plugins.

### P2 — continuous-listening test coverage is mock-only

The existing continuous-listening test sets VISUAL dependencies in `builtins` and mocks Termux commands and speech. This is useful unit coverage but does not verify Android microphone permission, screen-off behavior, wake-lock survival, battery optimization, real speech recognition, or notification actions on a physical phone.

### P3 — README claims need a reproducible test record

README describes Python 3.14 compatibility and a 79-tool / zero-crash check. The repository tree does not include a CI workflow or a consolidated reproducible test command/report supporting those claims. Keep these as project claims until a repeatable test run is captured.

## Positive controls observed

- `data_sync()` checks that the destination data repository is private before syncing personal data.
- The sync path excludes obvious secret fields from public config and scans files for key patterns and configured secret values before pushing.
- Risky actions have a confirmation path in the main chat flow.
- The self-upgrade path includes a backup and protected-code marker check.

## Next safe steps

1. Add a repeatable offline test runner and run syntax/import/unit tests on a clean Python environment.
2. Fix updater success reporting and validate ZIP paths before extraction; preserve a rollback copy.
3. Trace every plugin import/registration and resolve duplicate layout only after reference checks.
4. Add tests for tool schema immutability, plugin failures, backup/restore, and self-upgrade rollback.
5. Run physical-device checks separately on Termux/Android before claiming runtime stability.

## Verification status

Static inspection only. No tests are marked PASS in this report. No source-code behavior was changed in this audit commit.
