# VISUAL Autonomous Development Engine

This subsystem completes a missing piece between the existing web/research tools, project builder, Engineer task loop and self-intelligence observer.

## What it adds
- Durable SQLite task ledger with validated lifecycle transitions and event history.
- Separate per-task workspaces under ~/.visual/development/<task-id>; generated artifacts never overwrite the live VISUAL source tree.
- Research provenance ledger: HTTPS source URL, title, summary and short evidence excerpt/section.
- Artifact inventory with SHA-256 hashes, per-file and total workspace size limits, path traversal and symlink rejection, and secret-pattern checks.
- Static validation of Python syntax and JSON without executing generated Python code.
- Dated task state and artifacts remain available after a VISUAL restart.

## Tools exposed to VISUAL
- dev_task_create, dev_task_list, dev_task_status
- dev_task_transition
- dev_task_add_research
- dev_task_write_file, dev_task_files
- dev_task_validate

## How the Developer workflow should use it
1. Create a task and write its goal, constraints, acceptance criteria and deliverables.
2. Move through planning -> researching -> designing -> implementing -> validating.
3. Record every external research source in the source ledger; distinguish source evidence from model inference.
4. Write all generated code into the task workspace, never directly into the live installation.
5. Run static validation and inspect the complete artifact list and hashes.
6. Move to awaiting_approval. A human must review and approve any execution, installation, publishing, deployment or live-system change.
7. Only an independent verifier/release step should mark a task completed.

## Security boundary and limitations
- This module deliberately does not run generated code, install packages, publish repositories, deploy applications, or edit VISUAL itself.
- Static syntax validation is not a substitute for unit/integration tests, dependency checks, security review or device testing.
- A task workspace is a filesystem boundary by convention, not an OS sandbox. Do not execute untrusted generated code on the phone as the Termux user. For actual execution use a separate container/VM or a separately configured OS sandbox with no inherited secrets and restricted network.
- Existing legacy project_run and Engineer tools remain in VISUAL; they are not magically sandboxed by this module. Use explicit owner approval and isolated infrastructure before executing untrusted code.
- GitHub publication, package installation, public deployment and changes to the live core remain separate, approval-gated actions.

## Tests
Run:
```bash
PYTHONPATH=plugins/autonomous_development python -m unittest discover -s plugins/autonomous_development -p 'test_*.py' -v
python -m compileall -q visual.py plugins
```
