---
phase: 46-schema-validation-fail-fast-startup
plan: 02
subsystem: config
tags: [jsonschema, schema-validation, fail-fast, openclaw-json, project-json, config-validator]

# Dependency graph
requires:
  - phase: 46-01
    provides: 7-test RED suite for validate_openclaw_config and validate_project_config_schema (CONF-02, CONF-06)
  - phase: 45-path-resolver-constants-foundation
    provides: OPENCLAW_ROOT path resolution, consolidated constants in config.py
provides:
  - OPENCLAW_JSON_SCHEMA and PROJECT_JSON_SCHEMA dict constants in config.py
  - validate_openclaw_config() returning (fatal, warnings) tuple in config_validator.py
  - validate_project_config_schema() raising ConfigValidationError in config_validator.py
  - Wired validation in load_and_validate_openclaw_config() and load_project_config()
  - _emit_validation_results() with TTY colour support for stderr output
  - jsonschema>=4.26.0 declared as pyproject.toml dependency
affects: [phase-47, phase-48, openclaw-startup, project-config-loading]

# Tech tracking
tech-stack:
  added: [jsonschema>=4.26.0, Draft202012Validator]
  patterns:
    - Lazy import of schema constants inside validator functions to avoid circular imports
    - (fatal_errors, warnings) tuple return from validators — sys.exit at call site not inside validator
    - additionalProperties violations demoted to warnings; required/type violations are fatal
    - TTY-aware stderr output with ANSI colour codes for interactive vs non-interactive environments

key-files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/src/openclaw/config_validator.py
    - packages/orchestration/src/openclaw/project_config.py
    - packages/orchestration/pyproject.toml

key-decisions:
  - "additionalProperties violations are warnings not fatal errors — unknown fields may be forward-compatible"
  - "sys.exit(1) fires in _emit_validation_results() at the project_config.py call site, not inside the validator"
  - "OPENCLAW_JSON_SCHEMA and PROJECT_JSON_SCHEMA imported lazily inside validator functions to avoid circular imports"
  - "Draft202012Validator.iter_errors() collects all errors before raising — collect-all strategy"

patterns-established:
  - "Validator functions return (fatal: list, warnings: list) — clean testable API without mocking sys.exit"
  - "Schema constants live in config.py, validator logic in config_validator.py, wiring in project_config.py"

requirements-completed: [CONF-02, CONF-06]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 46 Plan 02: Schema Validation + Fail-Fast Startup Summary

**jsonschema Draft202012Validator wired into openclaw.json and project.json load paths — unknown fields warn, missing required fields exit(1)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T05:42:53Z
- **Completed:** 2026-02-25T05:45:17Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- OPENCLAW_JSON_SCHEMA and PROJECT_JSON_SCHEMA added to config.py with required/optional field definitions
- validate_openclaw_config() and validate_project_config_schema() implemented in config_validator.py using Draft202012Validator
- Validation wired into load_and_validate_openclaw_config() and load_project_config() in project_config.py
- All 7 new tests GREEN; all 158 tests (151 prior + 7 new) pass
- Live openclaw.json correctly warns on unknown 'wizard' field and continues startup

## Task Commits

Each task was committed atomically:

1. **Task 1: Add OPENCLAW_JSON_SCHEMA and PROJECT_JSON_SCHEMA to config.py; declare jsonschema dep** - `d1fe575` (feat)
2. **Task 2: Implement validate_openclaw_config() and validate_project_config_schema()** - `76f84d3` (feat)
3. **Task 3: Wire validation into project_config.py load paths; add TTY stderr output** - `18f0f1e` (feat)

## Files Created/Modified
- `packages/orchestration/src/openclaw/config.py` - Added OPENCLAW_JSON_SCHEMA and PROJECT_JSON_SCHEMA dict constants
- `packages/orchestration/src/openclaw/config_validator.py` - Added validate_openclaw_config(), validate_project_config_schema(), helper functions; imported re, sys, Draft202012Validator
- `packages/orchestration/src/openclaw/project_config.py` - Updated imports, added _is_tty()/_emit_validation_results() helpers, wired schema validation into both load functions
- `packages/orchestration/pyproject.toml` - Added jsonschema>=4.26.0 to dependencies

## Decisions Made
- additionalProperties violations are warnings not fatal errors — unknown fields may be forward-compatible
- sys.exit(1) fires in _emit_validation_results() at the project_config.py call site, not inside the validator
- OPENCLAW_JSON_SCHEMA and PROJECT_JSON_SCHEMA imported lazily inside validator functions to avoid circular imports
- Draft202012Validator.iter_errors() collect-all strategy before reporting — user sees all errors at once

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 46 Plan 03 (test wiring and integration verification) is ready — all schema validation implemented and tested
- CONF-02 and CONF-06 requirements complete
- The live openclaw.json produces a WARNING for an unknown 'wizard' field — this is expected behavior; the field may be removed in a future cleanup

---
*Phase: 46-schema-validation-fail-fast-startup*
*Completed: 2026-02-25*
