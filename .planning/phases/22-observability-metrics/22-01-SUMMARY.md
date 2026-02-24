---
phase: 22-observability-metrics
plan: 01
subsystem: orchestration
tags: [state-engine, metrics, observability, activity-log, lifecycle-timing]

# Dependency graph
requires:
  - phase: 21-state-engine-performance
    provides: write-through cache, mtime-based invalidation, JarvisState class
  - phase: 19-structured-logging
    provides: structured JSON logger with extra fields

provides:
  - Task lifecycle timestamps (spawn_requested_at, container_started_at, completed_at) in workspace-state.json
  - Cumulative lock_wait_ms and retry_count per task
  - Activity log auto-rotation when exceeding configurable threshold
  - set_task_metric() generic metric stamping method on JarvisState
  - ACTIVITY_LOG_MAX_ENTRIES config constant (default 100, env OPENCLAW_ACTIVITY_LOG_MAX)

affects: [23-pool-config, 24-dashboard-metrics, monitoring-tools]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rotate-outside-lock: update_task appends then calls rotate_activity_log() separately (each acquires its own lock) to avoid nested locking"
    - "Generic metric stamping: set_task_metric(task_id, key, value) for atomic key writes without full update_task overhead"
    - "Wall-clock lock-wait proxy: pool.py times its own state engine calls to accumulate lock_wait_ms without modifying _acquire_lock return type"

key-files:
  created: []
  modified:
    - orchestration/config.py
    - orchestration/state_engine.py
    - skills/spawn_specialist/spawn.py
    - skills/spawn_specialist/pool.py

key-decisions:
  - "rotate_activity_log() acquires its own separate LOCK_EX rather than being called inside update_task's lock — simpler, avoids nesting, and fast-path cache check avoids acquiring any lock when within threshold"
  - "update_task changed from return to break to allow rotate_activity_log to run after successful write"
  - "lock_wait_ms in pool.py is wall-clock time around state engine calls (not internal lock spin time) — practical proxy without modifying _acquire_lock return type"
  - "spawn_requested_at stored in task metadata dict rather than as a top-level field to maintain schema consistency"

patterns-established:
  - "Lifecycle metric pattern: spawn.py records request time, pool.py records start/complete times — queue wait and execution time derivable without joins"
  - "Activity log rotation: archived_activity_count preserves cumulative count of dropped entries for auditability"

requirements-completed: [OBS-02, OBS-04]

# Metrics
duration: 3min
completed: 2026-02-24
---

# Phase 22 Plan 01: Observability Metrics — Task Lifecycle Timing Summary

**Task lifecycle timestamps, cumulative lock-wait metrics, and bounded activity log rotation instrumented across state engine, spawn, and pool modules**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-24T02:07:00Z
- **Completed:** 2026-02-24T02:10:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `set_task_metric()` added to JarvisState for atomic stamping of arbitrary metric keys (container_started_at, completed_at, lock_wait_ms, retry_count)
- `rotate_activity_log()` trims activity log to configurable threshold (default 100), tracks archived count cumulatively in `archived_activity_count`
- `update_task()` auto-triggers rotation after every append; rotation uses fast-path cache check to skip lock acquisition when within threshold
- spawn.py records `spawn_requested_at` at task creation time (earliest lifecycle marker before Docker spawns)
- pool.py records `container_started_at`, `completed_at`, `retry_count`, and cumulative `lock_wait_ms`; emits structured "Task lifecycle metrics" log at INFO

## Task Commits

Each task was committed atomically:

1. **Task 1: Add task lifecycle timestamps and activity log rotation to state engine** - `a37afda` (feat)
2. **Task 2: Record task lifecycle timestamps in spawn and pool modules** - `9903e75` (feat)

## Files Created/Modified

- `orchestration/config.py` — Added `ACTIVITY_LOG_MAX_ENTRIES` constant (configurable via `OPENCLAW_ACTIVITY_LOG_MAX` env var, default 100)
- `orchestration/state_engine.py` — Added `set_task_metric()`, `rotate_activity_log()`, lock wait DEBUG logging, and rotation hook in `update_task()`
- `skills/spawn_specialist/spawn.py` — Added `import time`, added `spawn_requested_at: time.time()` to `create_task` metadata
- `skills/spawn_specialist/pool.py` — Added `import time`, records `container_started_at`/`completed_at`/`retry_count`/`lock_wait_ms` via `set_task_metric()`, emits lifecycle metrics log

## Decisions Made

- `update_task` changed from `return` to `break` on success so `rotate_activity_log` runs after the retry loop — a one-line fix that enables clean post-write rotation without nested locks.
- `rotate_activity_log` uses fast-path cache read to check log length before acquiring any lock; no-ops immediately if within threshold, minimizing contention.
- `lock_wait_ms` in pool.py is wall-clock time around state engine calls (not internal fcntl spin time). Practical proxy without changing `_acquire_lock` return type.
- `spawn_requested_at` stored inside the `metadata` dict on the task entry (alongside `cli_runtime`, `container_name`) rather than as a top-level field.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed `rotate_activity_log` never being called due to `return` in retry loop**
- **Found during:** Task 1 verification
- **Issue:** Plan specified calling `rotate_activity_log` after `update_task`'s write, but the original `update_task` used `return` inside the `for` loop — meaning code after the loop (where the rotation call was placed) was unreachable on success.
- **Fix:** Changed `return` to `break` so the loop exits normally on success, then rotation runs after the loop.
- **Files modified:** `orchestration/state_engine.py`
- **Verification:** Functional test — 120 updates to a task with threshold=100 confirmed log trimmed to 100 and `archived_activity_count >= 20`.
- **Committed in:** `a37afda` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug)
**Impact on plan:** Fix was essential for correctness; without it, rotation never fired. Single-line change with no scope creep.

## Issues Encountered

None beyond the `return`-vs-`break` bug caught during verification.

## Next Phase Readiness

- OBS-02: spawn-to-complete duration, lock wait, and retry count are all derivable from workspace-state.json task entries.
- OBS-04: activity logs auto-rotate at configurable threshold, preventing unbounded state file growth.
- Phase 23 (Pool Config) and Phase 24 (Dashboard Metrics) can consume these fields directly from state.
- Dashboard can display queue_wait = container_started_at - spawn_requested_at, execution = completed_at - container_started_at, total = completed_at - spawn_requested_at.

---
*Phase: 22-observability-metrics*
*Completed: 2026-02-24*

## Self-Check: PASSED

- FOUND: orchestration/config.py
- FOUND: orchestration/state_engine.py
- FOUND: skills/spawn_specialist/spawn.py
- FOUND: skills/spawn_specialist/pool.py
- FOUND: .planning/phases/22-observability-metrics/22-01-SUMMARY.md
- FOUND commit a37afda (Task 1)
- FOUND commit 9903e75 (Task 2)
