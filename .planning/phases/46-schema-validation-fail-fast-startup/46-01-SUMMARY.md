---
phase: 46-schema-validation-fail-fast-startup
plan: 01
subsystem: testing
tags: [pytest, tdd, jsonschema, config-validation, CONF-02, CONF-06]

# Dependency graph
requires:
  - phase: 45-path-resolver-constants-foundation
    provides: config.py with consolidated constants and path resolution
provides:
  - 7-test RED suite for validate_openclaw_config and validate_project_config_schema
  - TDD contract defining CONF-02 and CONF-06 validation interface
affects: [46-02-PLAN.md, schema validation implementation]

# Tech tracking
tech-stack:
  added: []
  patterns: [TDD RED state — test suite written before implementation, plain pytest functions with descriptive docstrings]

key-files:
  created:
    - packages/orchestration/tests/test_config_validator.py
  modified: []

key-decisions:
  - "validate_openclaw_config returns (fatal: list, warnings: list) tuple — not exception-based for openclaw.json validation"
  - "validate_project_config_schema is a separate function wrapping jsonschema for project.json — raises exception on failure"
  - "Minimal valid config for tests: {gateway: {port: 18789}, agents: {list: []}}"

patterns-established:
  - "TDD RED: tests import from target modules before those symbols exist — ImportError is the expected RED state"
  - "config_validator tests call validators directly, never via sys.exit() wrappers"

requirements-completed: []

# Metrics
duration: 1min
completed: 2026-02-25
---

# Phase 46 Plan 01: Schema Validation Test Suite Summary

**7-test TDD RED suite defining the validate_openclaw_config() and validate_project_config_schema() contract for CONF-02 and CONF-06**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-25T05:40:02Z
- **Completed:** 2026-02-25T05:40:45Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Wrote 7 failing unit tests covering all CONF-02 and CONF-06 scenarios from research
- Confirmed RED state via ImportError on collection (validate_openclaw_config, validate_project_config_schema, OPENCLAW_JSON_SCHEMA do not yet exist)
- All 151 existing tests still pass — no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests (RED)** - `4b4aea2` (test)

**Plan metadata:** (docs commit follows)

_Note: TDD RED — single test commit, no implementation._

## Files Created/Modified

- `packages/orchestration/tests/test_config_validator.py` - 7 failing unit tests for CONF-02 and CONF-06 schema validation

## Decisions Made

- `validate_openclaw_config` returns a `(fatal: list[str], warnings: list[str])` tuple — callers inspect and decide whether to call `sys.exit()`. This keeps the validator testable without mocking sys.exit.
- `validate_project_config_schema` is a separate entry point for project.json — raises an exception (matching existing `ConfigValidationError` pattern in the module).
- Minimal valid config `{"gateway": {"port": 18789}, "agents": {"list": []}}` is sufficient to cover all CONF-02/CONF-06 scenarios.
- `test_project_json_missing_required` uses `pytest.raises(Exception)` (broad) because the exact exception type (`ConfigValidationError` vs `jsonschema.ValidationError`) is an implementation detail Plan 02 will decide.

## Deviations from Plan

None - plan executed exactly as written. Test file content matches the specification from the plan verbatim.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED state established — Plan 02 (implementation) can now make all 7 tests green
- Existing `ConfigValidationError` class in config_validator.py is already importable — Plan 02 only needs to add `validate_openclaw_config`, `validate_project_config_schema`, and `OPENCLAW_JSON_SCHEMA`

## Self-Check: PASSED

- `packages/orchestration/tests/test_config_validator.py` — FOUND
- `46-01-SUMMARY.md` — FOUND
- Commit `4b4aea2` — FOUND

---
*Phase: 46-schema-validation-fail-fast-startup*
*Completed: 2026-02-25*
