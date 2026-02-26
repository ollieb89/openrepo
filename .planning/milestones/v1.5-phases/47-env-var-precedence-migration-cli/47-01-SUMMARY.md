---
phase: 47-env-var-precedence-migration-cli
plan: 01
subsystem: config
tags: [config, env-vars, cli, openclaw, python]

# Dependency graph
requires:
  - phase: 46-schema-validation-fail-fast-startup
    provides: validate_openclaw_config, config.py schema constants, load_and_validate_openclaw_config
  - phase: 45-path-resolver-constants-foundation
    provides: _find_project_root, get_project_root, get_state_path, get_snapshot_dir in config.py
provides:
  - get_active_project_env() function in config.py — single env var read for OPENCLAW_PROJECT
  - _find_project_root() auto-creates OPENCLAW_ROOT directory on first run
  - Env var precedence comment block in config.py listing all five OPENCLAW_* vars
  - project_config.get_active_project_id() routes through config.py (no direct os.environ.get)
  - openclaw-config --help epilog listing all five env vars with descriptions
  - config/openclaw.json.example _comment_env_vars key documenting precedence chain
affects: [spawn, pool, monitor, state_engine, cli, project_config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All OPENCLAW_* env var reads centralised in config.py — no component calls os.environ directly"
    - "get_active_project_env() provides single point for OPENCLAW_PROJECT resolution"
    - "argparse epilog pattern for documenting env vars in CLI --help output"

key-files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/src/openclaw/project_config.py
    - packages/orchestration/src/openclaw/cli/config.py
    - config/openclaw.json.example

key-decisions:
  - "get_active_project_env() returns None (not empty string) when env var is unset — uses 'or None' idiom"
  - "mkdir auto-create applies only to OPENCLAW_ROOT env var path, not ~/.openclaw fallback (expected to exist already)"
  - "String annotation 'str | None' used for Python 3.9 compatibility (| union syntax requires 3.10+ at runtime without quotes)"

patterns-established:
  - "Env var centralisation pattern: all os.environ reads in config.py, callers import functions not raw env values"
  - "Precedence comment block format: five-var table with resolution order in config.py"

requirements-completed: [CONF-04]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 47 Plan 01: Env Var Precedence — OPENCLAW_PROJECT Centralisation Summary

**OPENCLAW_PROJECT env var resolution moved from project_config.py to config.py via get_active_project_env(), with auto-create for OPENCLAW_ROOT, a five-var precedence comment block, CLI --help epilog, and openclaw.json.example documentation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T06:42:21Z
- **Completed:** 2026-02-25T06:44:xx Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `get_active_project_env()` to `config.py` — single authoritative reader for `OPENCLAW_PROJECT`
- Updated `_find_project_root()` to auto-create directory via `mkdir(parents=True, exist_ok=True)` when `OPENCLAW_ROOT` env var is explicitly set
- Added env var precedence comment block in `config.py` listing all five `OPENCLAW_*` vars with resolution order
- Removed direct `os.environ.get("OPENCLAW_PROJECT")` from `project_config.py` — now routes through `config.py`
- Added argparse epilog to `openclaw-config --help` listing all five env vars with brief descriptions
- Added `_comment_env_vars` to `config/openclaw.json.example` documenting precedence chain inline

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get_active_project_env() + auto-create + precedence comment block to config.py** - `6fe41dd` (feat)
2. **Task 2: Route OPENCLAW_PROJECT through config.py; update cli/config.py epilog; update openclaw.json.example** - `96cdbd3` (feat)

## Files Created/Modified
- `packages/orchestration/src/openclaw/config.py` — Added precedence comment block, mkdir auto-create in _find_project_root(), get_active_project_env() function
- `packages/orchestration/src/openclaw/project_config.py` — Import get_active_project_env, replace os.environ.get call
- `packages/orchestration/src/openclaw/cli/config.py` — Added argparse epilog with five-var env var table
- `config/openclaw.json.example` — Added _comment_env_vars key documenting precedence chain

## Decisions Made
- `get_active_project_env()` returns `None` (not empty string) when env var is unset — uses `or None` idiom to coerce empty string to None
- mkdir auto-create applies only to `OPENCLAW_ROOT` env var path, not `~/.openclaw` fallback (home dir path expected to exist already as a pre-existing install)
- String annotation `'str | None'` used with quotes for Python 3.9 compatibility (pipe union syntax requires 3.10+ at runtime without quotes)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- CONF-04 complete — all five OPENCLAW_* env var reads centralised in config.py
- 158 tests pass, no regressions
- Phase 47 Plan 01 is the only plan in this phase — phase complete

---
*Phase: 47-env-var-precedence-migration-cli*
*Completed: 2026-02-25*

## Self-Check: PASSED

All files verified present. Both task commits confirmed in git log.
