# Repository Guidelines

## Project Structure & Module Organization
- Root config in `openclaw.json`; adjust `source_directories` and agent mappings carefully.
- Agent personas live in `agents/` (`clawdia_prime/`, `pumplai_pm/`, `l3_specialist/`); reuse `_templates/` for new identities.
- Orchestration core is in `orchestration/` (`state_engine.py`, `snapshot.py`, `project_cli.py`, `monitor.py`).
- Skills reside in `skills/` (`router/` for L1→L2 dispatch, `spawn/` for L2→L3 containers, `review/` for diff review).
- Container image lives at `docker/l3-specialist/` (`Dockerfile`, `entrypoint.sh`).
- Per-project manifests live under `projects/<id>/`; runtime state and snapshots are in `workspace/.openclaw/<id>/`.
- Docs and dashboards: `docs/`, `workspace/occc/`; operational data sits in `logs/`, `sandboxes/`, `delivery-queue/`.

## Build, Test, and Development Commands
- Build L3 image: `docker build -t openclaw-l3-specialist:latest docker/l3-specialist/`.
- Initialize a project: `python3 orchestration/project_cli.py init --id myproject --name "My Project" [--workspace <path>]`.
- Spawn a specialist: `python3 skills/spawn/spawn.py task-001 code "Implement feature" --workspace <path>`.
- Monitor or inspect state: `python3 orchestration/monitor.py tail` and `python3 orchestration/monitor.py status`.
- List/switch projects: `python3 orchestration/project_cli.py list` and `python3 orchestration/project_cli.py switch <id>`.

## Coding Style & Naming Conventions
- Python: prefer snake_case, explicit typing when practical, and small, testable functions.
- JavaScript/Node (skills): use clear module boundaries and avoid shell-injection by keeping exec arguments array-based.
- Config files (JSON): keep keys lower_snake_case; preserve existing ordering to ease diff review.
- Directory naming mirrors roles (`l3_specialist`, `router`); new project folders follow `projects/<id>/`.
- Default to ASCII; avoid embedding secrets in configs, prompts, or logs.

## Testing Guidelines
- No automated test suite; rely on manual verification and dry-runs.
- Before merging, run container-critical flows: project init, spawn, and monitor commands against a test project.
- Review diffs for state file changes under `workspace/.openclaw/` to avoid corrupting task history.
- Validate generated JSON with `python -m json.tool <file>` when editing configs.

## Commit & Pull Request Guidelines
- Use focused commits; conventional style encouraged (e.g., `chore: update spawn specialist docs`).
- Summaries should state scope and impact; bodies note validation commands run and any state files touched.
- For PRs, include linked issues/task IDs, expected outcomes, and screenshots for dashboard/UI changes.
- Avoid rebasing away staging-branch history from L3 runs unless explicitly cleaning up rejected work.

## Security & Configuration Tips
- Keep `openclaw.json` trust paths minimal; avoid broadening `source_directories` without need.
- Do not check credentials into `identity/`, `logs/`, or `workspace/` snapshots.
- L3 containers are ephemeral; confirm cleanup policies before increasing concurrency or queue timeouts in `spawn/pool.py`.
