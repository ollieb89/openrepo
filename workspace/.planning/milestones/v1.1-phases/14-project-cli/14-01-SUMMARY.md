---
phase: 14-project-cli
plan: "01"
subsystem: orchestration
tags: [cli, project-management, templates, argparse]
dependency_graph:
  requires:
    - orchestration/project_config.py
    - orchestration/soul_renderer.py
    - agents/_templates/soul-default.md
  provides:
    - orchestration/project_cli.py
    - projects/_templates/*.json
  affects:
    - orchestration/project_config.py (error message update)
tech_stack:
  added: []
  patterns:
    - argparse subparser pattern (consistent with monitor.py)
    - lazy docker import for container detection
    - deferred soul_renderer import to avoid circular imports (Phase 18 pattern)
    - _-prefix convention for template directories (skipped by list enumeration)
key_files:
  created:
    - orchestration/project_cli.py
    - projects/_templates/fullstack.json
    - projects/_templates/backend.json
    - projects/_templates/ml-pipeline.json
  modified:
    - orchestration/project_config.py
decisions:
  - "Project ID validation uses ^[a-zA-Z0-9-]{1,20}$ — consistent with spawn.py task IDs"
  - "remove preserves workspace directory (locked decision: workspace data must not be deleted)"
  - "switch guard checks CURRENT active project for running containers, not the target"
  - "init auto-activates on creation — reduces friction for new project setup"
  - "L2 agent validation is non-fatal warning — matching init.py philosophy for non-blocking startup"
  - "Error messages go to stderr, normal output to stdout — Unix convention"
metrics:
  duration: "2 min"
  completed: "2026-02-23"
  tasks_completed: 2
  files_created: 4
  files_modified: 1
requirements_satisfied:
  - CLI-01
  - CLI-02
  - CLI-03
  - CLI-04
  - CLI-05
  - CLI-06
---

# Phase 14 Plan 01: Project CLI Summary

**One-liner:** Four-subcommand project manager CLI (init/list/switch/remove) with template presets and safety guards for the OpenClaw orchestration system.

## What Was Built

### orchestration/project_cli.py (556 lines)

A complete project management CLI following the argparse subparser pattern established in `monitor.py`. Runnable as `python3 orchestration/project_cli.py <subcommand>`.

**init** — Creates `projects/<id>/project.json` and `agents/<l2_pm>/agent/SOUL.md`. Supports interactive prompting fallback, ID validation (`^[a-zA-Z0-9-]{1,20}$`), collision detection with `--force` override, template merging, workspace path override, auto-activation, and non-fatal L2 agent registration warning.

**list** — Tabular output with ID (15), NAME (15), WORKSPACE (40, truncated) columns and `*` active marker. Handles corrupt projects gracefully.

**switch** — Updates `openclaw.json active_project`. Blocked if L3 containers are running for the current active project (detected via docker label `openclaw.project=<id>`). Docker failures are non-fatal (allow switch with warning).

**remove** — Deletes `projects/<id>/` with `shutil.rmtree()`. Preserves `workspace/<id>/`. Blocked if target is the active project. Requires `--force` in non-interactive mode.

### projects/_templates/ (3 files)

Template preset JSON files that `init --template` merges into the default project config:

- `fullstack.json` — Next.js/React/Tailwind + Python/FastAPI + Docker/PostgreSQL
- `backend.json` — Python/FastAPI + Docker/PostgreSQL, no frontend
- `ml-pipeline.json` — Python/PyTorch/FastAPI + Docker/NVIDIA GPU/MLflow, 8g mem limit, 2x CPU quota

### orchestration/project_config.py (1-line update)

Error message in `load_project_config()` updated from manual `mkdir/cp` instructions to `python3 orchestration/project_cli.py init --id <id>`.

## Verification Results

All plan verification steps passed:

1. `list` — shows geriai and pumplai with correct formatting and `*` active marker
2. `init --id clitest --name "CLI Test" --force` → project appears in list
3. `init --template fullstack` → `tech_stack.frontend == "Next.js, React, Tailwind CSS"`
4. `switch clitest` → `openclaw.json active_project == "clitest"`
5. `remove clitest --force && remove clitest2 --force` → cleanup succeeds
6. `switch pumplai` → original active project restored

Safety guards verified:
- Remove blocked when target is active project (exit code 1, red error message)
- Switch allowed only after switching away from active project first

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

### Files Created/Modified

- `orchestration/project_cli.py` — 556 lines (requirement: >=200) ✓
- `projects/_templates/fullstack.json` — contains "fullstack" ✓
- `projects/_templates/backend.json` — contains "backend" ✓
- `projects/_templates/ml-pipeline.json` — contains "ml-pipeline" ✓
- `orchestration/project_config.py` — error message updated ✓

### Commits

- `e931280` feat(14-01): add project template preset files
- `2477d4c` feat(14-01): create project_cli.py with init/list/switch/remove subcommands

## Self-Check: PASSED
