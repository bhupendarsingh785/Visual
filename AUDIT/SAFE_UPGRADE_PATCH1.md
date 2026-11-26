# VISUAL initial static audit and safe patch record

Date: 2026-11-26
Target baseline: `main` commit `70f6eba368cf46217015f16d93b4f3403204e62d`
Working branch: `upgrade/global-intelligence-v1`

## Scope and limits

Static inspection of the repository tree, README, main Python entry point, installer/updater, plugin entry points/tests, and browser live client. No physical Android/Termux runtime, microphone, screen-off, wake-lock, API-provider, Telegram, or long-duration test was run. This report does not claim device stability.

## Repository structure confirmed

- Main runtime: `visual.py` (about 193 KB).
- Browser UI: `web/index.html`, `web/live.js`.
- Plugins: `plugins/continuous_listening`, `plugins/continuous_listening_v2` (spec only), and `plugins/memory_repeat`.
- Shell scripts: `install.sh`, `update.sh`.
- The loader scans direct children of `plugins/`; a directory is loaded only when it contains a direct `plugin.py`.

## Findings from baseline

1. **Updater masked failures (high):** the previous `update.sh` suppressed Git commit/push errors with `|| true`, yet printed a success message. It also extracted the newest shared-storage ZIP directly into the home directory without validating its contents or making a rollback copy.
2. **Test claims were not reproducible from CI:** README describes Python 3.14 compatibility and a 79-tool / zero-crash check, but there was no workflow to run the plugin tests across Python versions.
3. **Duplicate unreachable plugin copy:** `plugins/memory_repeat/plugins/memory_repeat/plugin.py` duplicated the active plugin's code/blob. The main loader does not recurse into nested plugin directories, so this copy was not loaded.
4. **Memory test touched persistent data:** the original memory test called `clear()` against the module's default `last_statement.json`, which is a repository/runtime data file rather than a temporary test fixture.
5. **Plugin execution is in-process:** `load_plugins()` executes plugin code in the main `visual.py` globals. This is powerful but not isolated; only trusted first-party plugins should be loaded until a permission boundary exists.
6. **Continuous listening tests are mocked:** current tests do not prove microphone permissions, Android background survival, wake-lock behavior, battery optimization behavior, or real speech recognition.

## Changes made on this branch

- Replaced `update.sh` with a Git-based fail-safe updater. It refuses dirty worktrees, creates a timestamped archive backup, fetches and fast-forward pulls the current branch, compiles Python sources, runs plugin unit tests, and resets to the previous Git commit if update/checking fails. It no longer extracts arbitrary shared-storage ZIPs or silently reports failed pushes as success.
- Updated the memory-repeat tests to use a temporary file, so test setup/cleanup does not clear or overwrite the real memory JSON.
- Removed the unreachable nested duplicate plugin file. The active top-level `plugins/memory_repeat/plugin.py` remains unchanged.
- Added a GitHub Actions workflow to compile Python and run both plugin test suites on Python 3.11, 3.13, and 3.14.

## Not changed intentionally

- `visual.py`, the active plugins, live voice client, phone-control tools, secrets/data sync, and risky-action confirmation logic were not rewritten.
- No unknown plugin, user data, API key, memory file, or feature was deleted.
- No changes were applied to the user's phone or to `main`.

## Verification status

The GitHub commits and branch contents were confirmed after each write. The test workflow has been added but has not yet been observed completing on GitHub Actions. Therefore, no unit test is marked PASS here. Physical-device tests remain required before claiming runtime stability.
