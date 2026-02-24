---
phase: 20-reliability-hardening
plan: 02
subsystem: infra
tags: [config-validation, error-handling, python, orchestration]

# Dependency graph
requires:
  - phase: 19-structured-logging
    provides: get_logger structured logging factory used in config_validator
provides:
  - Schema validation for project.json (workspace + tech_stack fields)
  - Agent hierarchy validation for openclaw.json (reports_to refs, level constraints)
  - ConfigValidationError with actionable messages including file path, field name, fix hint
affects: [21-state-engine-perf, 22-observability-metrics, 23-pool-config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Collect-all validation: gather all errors before raising so callers see every problem at once"
    - "Fast-fail on load: validators called immediately after json.load, before return"
    - "Human-friendly errors: file path + field name + fix hint in every message"

key-files:
  created:
    - orchestration/config_validator.py
  modified:
    - orchestration/project_config.py
    - orchestration/__init__.py

key-decisions:
  - "Collect-all strategy for both validators so operators see all problems at once, not one fix at a time"
  - "validate_project_config wired into load_project_config so every caller gets validation for free"
  - "load_and_validate_openclaw_config added as dedicated function; get_active_project_id delegates to it"

patterns-established:
  - "ConfigValidationError.errors: list[str] — individual error strings for programmatic inspection"
  - "Error message format: '{file} ({path}): {problem}. {fix_hint}.'"

requirements-completed: [REL-02, REL-03]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 20 Plan 02: Config Validation Summary

**Schema validation for project.json (workspace + tech_stack) and openclaw.json agent hierarchy with human-friendly collect-all error messages wired into existing config load paths**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T00:51:51Z
- **Completed:** 2026-02-24T00:53:18Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `orchestration/config_validator.py` with `ConfigValidationError`, `validate_project_config`, and `validate_agent_hierarchy`
- Wired `validate_project_config` into `load_project_config` so every caller gets schema validation for free
- Added `load_and_validate_openclaw_config` and updated `get_active_project_id` to use it, ensuring agent hierarchy validated on every access
- Exported all three symbols (`validate_project_config`, `validate_agent_hierarchy`, `ConfigValidationError`) from `orchestration` package root

## Task Commits

Each task was committed atomically:

1. **Task 1: Create config_validator.py with project and agent hierarchy validation** - `a20be7c` (feat)
2. **Task 2: Integrate validators into config loading paths** - `534fa04` (feat)

**Plan metadata:** _(docs commit below)_

## Files Created/Modified

- `orchestration/config_validator.py` - ConfigValidationError class, validate_project_config, validate_agent_hierarchy with structured logging
- `orchestration/project_config.py` - Added validate_project_config call in load_project_config, added load_and_validate_openclaw_config, updated get_active_project_id
- `orchestration/__init__.py` - Exported load_and_validate_openclaw_config, validate_project_config, validate_agent_hierarchy, ConfigValidationError

## Decisions Made

- Collect-all strategy: both validators gather all errors before raising so operators see every problem in one pass
- validate_project_config is called after every `json.load` in `load_project_config` — no bypass possible
- `load_and_validate_openclaw_config` introduced as a first-class function so callers can explicitly request validated access to `openclaw.json`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Config validation infrastructure complete; REL-02 and REL-03 satisfied
- Any code that calls `load_project_config` or `get_active_project_id` now gets validation automatically
- Ready for Phase 21 (State Engine Performance) and Phase 22 (Observability Metrics)

---
*Phase: 20-reliability-hardening*
*Completed: 2026-02-24*
