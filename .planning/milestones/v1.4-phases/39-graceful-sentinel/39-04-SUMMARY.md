---
phase: 39-graceful-sentinel
plan: "04"
subsystem: infra
tags: [recovery, startup-scan, pool, spawn-task, wiring, orphaned-tasks]

requires:
  - phase: 39-03
    provides: run_recovery_scan() async method on L3ContainerPool, fully tested

provides:
  - spawn_task() calls await pool.run_recovery_scan() before spawn_and_monitor()
  - pool._pool_config assigned to pool instance in spawn_task() (including except path)
  - REL-06 success criterion 2 satisfied: recovery scan runs automatically without manual intervention
  - Integration test proving call order: run_recovery_scan before spawn_and_monitor

affects:
  - pool.py callers — recovery scan now runs on every pool-managed spawn
  - phase 40 and beyond — startup recovery is fully wired end-to-end

tech-stack:
  added: []
  patterns:
    - "Gap closure: assign pool._pool_config before calling methods that require it"
    - "Ensure except path sets pool_cfg = _POOL_DEFAULTS.copy() so _pool_config is always populated"
    - "Recovery scan wiring: await pool.run_recovery_scan() between pool creation and spawn_and_monitor()"

key-files:
  created: []
  modified:
    - skills/spawn_specialist/pool.py
    - tests/test_recovery_scan.py

key-decisions:
  - "pool_cfg also assigned in except path (was previously only max_concurrent) so _pool_config is always set"
  - "run_recovery_scan() called unconditionally in spawn_task() — no conditional guard needed since scan gracefully handles empty state"

patterns-established:
  - "Pattern: Pool config always available — both try and except paths set pool_cfg before pool creation"

requirements-completed:
  - REL-04
  - REL-05
  - REL-06
  - REL-07
  - REL-08

duration: 1min
completed: "2026-02-24"
---

# Phase 39 Plan 04: Gap Closure — Wire run_recovery_scan() into spawn_task() Summary

**spawn_task() now calls await pool.run_recovery_scan() before spawn_and_monitor() — orphaned task recovery is fully automatic, REL-06 success criterion 2 satisfied**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-02-24T16:55:22Z
- **Completed:** 2026-02-24T16:56:08Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Fixed except block in spawn_task() to set `pool_cfg = _POOL_DEFAULTS.copy()` (previously only set `max_concurrent`, leaving `pool_cfg` undefined if get_pool_config raised)
- Assigned `pool._pool_config = pool_cfg` after pool creation so run_recovery_scan() has config access
- Added `await pool.run_recovery_scan()` between pool creation and `spawn_and_monitor()` call
- Added `test_spawn_task_calls_recovery_scan` — verifies scan called exactly once and before spawn_and_monitor via call order tracking
- All 11 recovery scan tests pass (10 existing + 1 new), full suite 95 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire run_recovery_scan() into spawn_task() and add integration test** - `a1f1ffa` (feat)

## Files Created/Modified

- `skills/spawn_specialist/pool.py` - Fixed except path to set pool_cfg, assigned pool._pool_config, added await pool.run_recovery_scan() before spawn_and_monitor
- `tests/test_recovery_scan.py` - Added test_spawn_task_calls_recovery_scan integration test

## Decisions Made

- pool_cfg is now set in both try and except paths before pool creation — ensures `pool._pool_config` is always a valid dict regardless of whether get_pool_config succeeds
- run_recovery_scan() called unconditionally — no conditional guard required since the scan already handles empty state gracefully (returns {scanned: 0})

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 39 (Graceful Sentinel) fully complete: all 4 plans shipped, REL-04 through REL-08 satisfied
- SIGTERM handling (01), memorize drain (02), recovery scan implementation (03), recovery scan wiring (04)
- Pool startup now automatically scans for orphaned tasks on every spawn_task() invocation
- Ready for Phase 40 (Memory Health Monitor, QUAL-01..06)

---
*Phase: 39-graceful-sentinel*
*Completed: 2026-02-24*
