---
phase: 75-unified-observability
plan: 01
subsystem: api
tags: [python-metrics, snapshot, observability, metrics, state-engine, fcntl, atomic-write, tdd]

# Dependency graph
requires:
  - phase: 70-event-bridge-activation
    provides: state_engine.py with _write_state_locked() hook point
  - phase: 74-dashboard-streaming-ui
    provides: /api/metrics route.ts as base for extension
provides:
  - "write_python_metrics_snapshot() in metrics.py: throttled, atomic, failure-isolated"
  - "collect_metrics_from_state() in metrics.py: lock-safe helper from pre-loaded state"
  - "python-metrics.json written alongside workspace-state.json on every state write"
  - "GET /api/metrics returns python.* and meta.* fields alongside existing dashboard fields"
  - "Graceful degradation: python: null + meta.snapshot_missing: true when file absent"
affects: [dashboard-metrics-display, python-observability, unified-observability-phase-75]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy import to break circular dependency (metrics.py imports state_engine at module level would cause circular import — deferred to function body)"
    - "Module-level throttle dict (_last_snapshot_times) keyed by project_id for per-project rate limiting"
    - "Atomic file write via NamedTemporaryFile + os.replace() in same directory"
    - "Failure-isolated side effects: snapshot writer wrapped in try/except, never propagates to caller"
    - "Lock-safe metrics: collect_metrics_from_state(state_dict) accepts pre-loaded dict to avoid re-entrant fcntl lock deadlock"

key-files:
  created:
    - packages/orchestration/tests/test_python_metrics_snapshot.py
    - packages/dashboard/tests/api/metrics/unified-metrics.test.ts
  modified:
    - packages/orchestration/src/openclaw/metrics.py
    - packages/orchestration/src/openclaw/state_engine.py
    - packages/dashboard/src/app/api/metrics/route.ts

key-decisions:
  - "Lazy import JarvisState inside collect_metrics() function body to break circular import (state_engine imports metrics at module level)"
  - "collect_metrics_from_state() receives pre-loaded state dict — never calls read_state() — eliminates re-entrant fcntl lock deadlock"
  - "project_id derived from self.state_file.parent.name (workspace-state.json lives at {root}/workspace/.openclaw/{project_id}/workspace-state.json)"
  - "Snapshot hook placed after _create_backup(), before cache update — failure in hook never blocks state write"
  - "readPythonSnapshot exported as named function from route.ts for direct unit testing (same pattern as aggregateTodayUsage)"

patterns-established:
  - "Side-effect hooks in _write_state_locked: wrapped in outer try/except, non-fatal"
  - "Python → Dashboard data bridge: python-metrics.json written by Python, read by TypeScript API route with graceful degradation"

requirements-completed: [OBSV-01]

# Metrics
duration: 5min
completed: 2026-03-05
---

# Phase 75 Plan 01: Unified Observability — Python Metrics Snapshot Summary

**Throttled atomic snapshot writer (write_python_metrics_snapshot) hooked into state_engine writes python-metrics.json alongside workspace-state.json; /api/metrics merges it into unified response with python.* and meta.* fields**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-05T16:32:36Z
- **Completed:** 2026-03-05T16:37:25Z
- **Tasks:** 3
- **Files modified:** 5 (2 new Python, 2 new TS tests, 2 modified Python, 1 modified TS)

## Accomplishments

- Implemented `write_python_metrics_snapshot(project_id, state_file, state_dict)` with atomic write, 750ms throttle, and full failure isolation — never blocks state writes
- Added `collect_metrics_from_state(state_dict)` as lock-safe alternative to `collect_metrics()` — receives pre-loaded dict, eliminates re-entrant fcntl deadlock risk
- Hooked snapshot writer into `_write_state_locked` after `_create_backup()` — python-metrics.json written on every state write
- Extended `GET /api/metrics` to merge python-metrics.json into response; graceful degradation when file absent (python: null, meta.snapshot_missing: true)
- 5 Python TDD tests + 4 TypeScript TDD tests; 761 Python tests pass, 11 metrics TS tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test scaffolds for Python snapshot writer** - `179c7ee` (test)
2. **Task 2: Implement write_python_metrics_snapshot and hook into state_engine** - `7a7759f` (feat)
3. **Task 3: Extend /api/metrics and write TS test scaffold** - `e3bdb79` (feat)

_Note: TDD tasks have test commit first, then implementation commit_

## Files Created/Modified

- `packages/orchestration/tests/test_python_metrics_snapshot.py` - 5 tests: valid JSON, atomic write, throttle, failure swallowed, no-reentrant-lock
- `packages/orchestration/src/openclaw/metrics.py` - Added `collect_metrics_from_state()`, `write_python_metrics_snapshot()`, module-level throttle state; lazy import for JarvisState
- `packages/orchestration/src/openclaw/state_engine.py` - Import `write_python_metrics_snapshot`; hook call in `_write_state_locked` after `_create_backup()`
- `packages/dashboard/tests/api/metrics/unified-metrics.test.ts` - 4 tests: valid response, ENOENT degradation, JSON parse error degradation, snapshot_age_s computation
- `packages/dashboard/src/app/api/metrics/route.ts` - Added `readPythonSnapshot()` exported function and `PythonSnapshotResult` interface; merged into handler Promise.all and response

## Decisions Made

- **Lazy import to break circular import:** `metrics.py` imports from `state_engine`; `state_engine` now imports from `metrics`. Moving `JarvisState` import inside `collect_metrics()` function body breaks the cycle.
- **Lock-safe via parameter passing:** `collect_metrics_from_state(state_dict)` receives the already-loaded state dict rather than calling `read_state()` internally — eliminates deadlock risk when called from inside `_write_state_locked`.
- **project_id from path:** Derived as `self.state_file.parent.name` — matches convention where workspace-state.json lives at `{root}/workspace/.openclaw/{project_id}/workspace-state.json`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Circular import between metrics.py and state_engine.py**
- **Found during:** Task 2 (implementing write_python_metrics_snapshot)
- **Issue:** state_engine.py imports from metrics at module level (`from .metrics import write_python_metrics_snapshot`), but the original metrics.py imported JarvisState from state_engine at module level — creating a circular import that caused `ImportError: cannot import name 'JarvisState' from partially initialized module`
- **Fix:** Moved `from .state_engine import JarvisState` import to inside the `collect_metrics()` function body (lazy import), breaking the circular dependency
- **Files modified:** packages/orchestration/src/openclaw/metrics.py
- **Verification:** `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -v` — 5 tests pass; full 761-test suite passes
- **Committed in:** `7a7759f` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - circular import bug)
**Impact on plan:** Required fix for correctness — without it, the entire openclaw package would fail to import. No scope creep.

## Issues Encountered

None beyond the circular import auto-fixed above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- python-metrics.json is now written alongside workspace-state.json on every state write
- /api/metrics returns unified response with `python.*` and `meta.*` fields
- Dashboard can read `response.python` for Python-side task counts, pool utilization, memory health
- Ready for Phase 75 Plan 02: dashboard UI components to display the unified python.* metrics

## Self-Check: PASSED

Files verified:
- packages/orchestration/tests/test_python_metrics_snapshot.py - FOUND
- packages/orchestration/src/openclaw/metrics.py - FOUND
- packages/orchestration/src/openclaw/state_engine.py - FOUND (modified)
- packages/dashboard/tests/api/metrics/unified-metrics.test.ts - FOUND
- packages/dashboard/src/app/api/metrics/route.ts - FOUND (modified)

Commits verified:
- 179c7ee (Task 1 test scaffold)
- 7a7759f (Task 2 implementation)
- e3bdb79 (Task 3 TS tests + route extension)

---
*Phase: 75-unified-observability*
*Completed: 2026-03-05*
