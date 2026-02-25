---
phase: 48-config-integration-tests
plan: 01
subsystem: testing
tags: [pytest, integration-tests, config, schema-validation, env-vars, pool-config]

# Dependency graph
requires:
  - phase: 45-path-resolver
    provides: get_state_path, get_snapshot_dir, get_project_root, DEFAULT_POOL_* constants
  - phase: 46-schema-validation
    provides: validate_openclaw_config, validate_project_config_schema, ConfigValidationError
  - phase: 47-env-var-precedence-migration-cli
    provides: get_active_project_env, OPENCLAW_PROJECT env var precedence
provides:
  - Integration test suite for config layer (CONF-07) — 15 tests across 4 classes
  - pytest.mark.integration marker registered in pyproject.toml
  - valid_openclaw_config shared fixture in conftest.py
affects: [future-refactors-to-config-layer, ci-pipelines]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Import from openclaw.* inside test methods (not at module level) — avoids import-time side effects, monkeypatching works"
    - "importlib.reload(cfg) in try/finally restores module-level constants after env var tests"
    - "monkeypatch.delenv('OPENCLAW_STATE_FILE', raising=False) before any OPENCLAW_ROOT test — prevents priority shadowing"
    - "pytestmark = [pytest.mark.integration] at module level marks all tests without per-test decoration"

key-files:
  created:
    - packages/orchestration/tests/test_config_integration.py
  modified:
    - packages/orchestration/tests/conftest.py
    - pyproject.toml

key-decisions:
  - "Inner-method imports used throughout test file — monkeypatching env vars takes effect before the module is touched"
  - "try/finally pattern for importlib.reload ensures module-level LOG_LEVEL/ACTIVITY_LOG_MAX don't bleed into subsequent tests"
  - "TestPoolConfigFallback writes real project.json to tmp_path/projects/testproject/ — matches load_project_config() path resolution"

patterns-established:
  - "Integration tests follow class-per-concern: TestPathResolution, TestSchemaValidation, TestEnvPrecedence, TestPoolConfigFallback"
  - "valid_openclaw_config fixture: minimal valid dict (gateway.port + agents.list) — tests copy-and-mutate rather than constructing from scratch"

requirements-completed: [CONF-07]

# Metrics
duration: 8min
completed: 2026-02-25
---

# Phase 48 Plan 01: Config Integration Tests Summary

**Pytest integration test suite for the OpenClaw config layer — 15 tests covering path resolution, schema validation, env var precedence (all 4 vars), and pool config fallback using real filesystem I/O via tmp_path**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-25T07:19:00Z
- **Completed:** 2026-02-25T07:27:21Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Registered `pytest.mark.integration` marker in `pyproject.toml` — no more PytestUnknownMarkWarning
- Added `valid_openclaw_config` shared fixture to `conftest.py` for schema validation tests
- Created `test_config_integration.py` with 15 tests across 4 classes covering all CONF-07 success criteria
- Full suite grows from 214 to 229 tests, all green

## Task Commits

Each task was committed atomically:

1. **Task 1: Register integration marker and add valid_openclaw_config fixture** - `61977fc` (chore)
2. **Task 2: Write test_config_integration.py with all 4 test classes** - `04c5a8f` (feat)

## Files Created/Modified
- `packages/orchestration/tests/test_config_integration.py` - Integration test suite: TestPathResolution (3), TestSchemaValidation (5), TestEnvPrecedence (5), TestPoolConfigFallback (2)
- `packages/orchestration/tests/conftest.py` - Added `valid_openclaw_config` fixture (minimal valid openclaw.json dict)
- `pyproject.toml` - Added `markers = ["integration: integration tests that touch the filesystem"]`

## Decisions Made
- Inner-method imports used throughout — monkeypatching env vars via `monkeypatch.setenv` takes effect before modules are touched
- `try/finally` with `importlib.reload(cfg)` in finally block restores module-level constants after LOG_LEVEL/ACTIVITY_LOG_MAX tests
- Pool config tests write `tmp_path/projects/testproject/project.json` to match exact path that `load_project_config()` resolves

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CONF-07 requirement satisfied — automated test coverage for the full config layer
- Phase 48 is complete (only 1 plan)
- Ready to proceed to Phase 49: Deferred Items (REL-09, QUAL-07, OBS-05)

---
*Phase: 48-config-integration-tests*
*Completed: 2026-02-25*

## Self-Check: PASSED

- FOUND: packages/orchestration/tests/test_config_integration.py
- FOUND: packages/orchestration/tests/conftest.py
- FOUND: pyproject.toml
- FOUND: .planning/phases/48-config-integration-tests/48-01-SUMMARY.md
- FOUND commit: 61977fc (chore: marker + fixture)
- FOUND commit: 04c5a8f (feat: integration test suite)
