---
phase: 22-observability-metrics
plan: 02
subsystem: orchestration
tags: [pool, utilization, saturation, observability, monitor-cli]

# Dependency graph
requires:
  - phase: 22-01
    provides: task lifecycle timestamps, activity log rotation, set_task_metric
  - phase: 19-structured-logging
    provides: structured JSON logger with extra fields

provides:
  - Pool saturation onset/resolution structured log entries with project_id and task context
  - L3ContainerPool.get_pool_stats() returning live utilization snapshot
  - PoolRegistry.get_all_stats() aggregating stats across all project pools
  - monitor.py pool subcommand displaying per-project utilization table with color-coded saturation

affects: [23-pool-config, 24-dashboard-metrics, monitoring-tools]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "On-the-fly aggregation: pool utilization computed from workspace-state.json task statuses rather than maintaining running totals in state (in-memory counters for live pool process, state for persistence)"
    - "Saturation detection via asyncio.Semaphore._value: checking internal _value==0 before acquire detects saturation without side effects"
    - "Saturation two-phase tracking: onset logged when queueing (before block), resolution logged when acquiring (inside async with)"

key-files:
  created: []
  modified:
    - skills/spawn_specialist/pool.py
    - orchestration/monitor.py

key-decisions:
  - "Saturation onset detected by checking semaphore._value==0 before blocking — avoids needing a separate counter or lock"
  - "Resolution logged on acquiring a slot when _saturated was True — correct semantics: pool is no longer saturated once a waiting task gets through"
  - "completed_count incremented inside async with (after task result, before releasing semaphore) so it's atomic with the slot release"
  - "Monitor pool subcommand computes aggregates from state file task statuses (on-the-fly) — consistent with CONTEXT.md discretion and works when pool process is not running"
  - "max_concurrent hardcoded to 3 in monitor — Phase 23 will make this configurable per project"

patterns-established:
  - "Pool stats pattern: get_pool_stats() / get_all_stats() provide O(1) live snapshots without state file I/O"
  - "Saturation event pattern: onset at WARNING (capacity planning signal), resolution at INFO (recovery marker)"

requirements-completed: [OBS-03]

# Metrics
duration: 2min
completed: 2026-02-24
---

# Phase 22 Plan 02: Observability Metrics — Pool Utilization Summary

**Pool saturation event logging and monitor CLI pool subcommand with on-the-fly per-project utilization aggregation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-24T02:12:10Z
- **Completed:** 2026-02-24T02:14:05Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `L3ContainerPool` gains `completed_count`, `queued_count`, and `_saturated` instance attributes for aggregate tracking
- Saturation onset logged at WARNING with `project_id`, `queued_task_id`, `queue_depth`, and `active_task_ids` when semaphore is full and a new task queues
- Saturation resolution logged at INFO with `project_id`, `task_id`, and `queue_depth` when a slot is acquired after saturation
- `completed_count` incremented on any terminal result (inside the semaphore context, before release)
- `L3ContainerPool.get_pool_stats()` returns live utilization dict: active, queued, completed, max_concurrent, saturation_pct, saturated, project_id
- `PoolRegistry.get_all_stats()` aggregates stats across all registered project pools
- `monitor.py pool` subcommand added — reads workspace-state.json per project, computes active/queued/completed/failed counts on-the-fly, displays color-coded saturation table
- `--project` filter supported; summary totals row shown when viewing all projects
- Saturation color coding: green (0-33%), yellow (34-66%), red (67-100%)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add saturation event logging and pool-level counters to pool.py** - `7bc6227` (feat)
2. **Task 2: Add pool utilization subcommand to monitor CLI** - `210b057` (feat)

## Files Created/Modified

- `skills/spawn_specialist/pool.py` — Added completed_count/queued_count/_saturated attrs, saturation onset/resolution logging, get_pool_stats(), PoolRegistry.get_all_stats()
- `orchestration/monitor.py` — Added show_pool_utilization() function and 'pool' subcommand registration

## Decisions Made

- Saturation onset detected by checking `semaphore._value == 0` before the `async with` block — clean, no side effects, no additional synchronization needed.
- Resolution logged on first slot acquisition when `_saturated` was True — correct semantics: once a waiting task gets through, the pool is no longer saturated.
- `completed_count` incremented inside `async with` after task completes — ensures atomicity with the active container slot lifecycle.
- Monitor pool subcommand computes aggregates on-the-fly from state file task statuses per CONTEXT.md's "compute on-the-fly" discretion — works even when no pool process is running.
- `max_concurrent` hardcoded to 3 in monitor (Phase 23 will make this configurable per project via project.json).

## Deviations from Plan

None - plan executed exactly as written.

The plan's verification step (`python3 orchestration/monitor.py pool --help`) fails due to a pre-existing import path issue when running monitor.py as a direct script (not as a module). This is not caused by these changes — the same error occurs for all existing subcommands. The equivalent `python3 -m orchestration.monitor pool --help` works correctly.

## Issues Encountered

None.

## Next Phase Readiness

- OBS-03: Pool utilization (active/queued/completed per project, semaphore saturation) is now queryable via `monitor.py pool` CLI.
- Saturation events are structured log entries with project_id and task context — suitable for capacity planning.
- Phase 23 (Pool Config) can extend pool subcommand to read max_concurrent from project.json instead of hardcoded 3.
- Phase 24 (Dashboard Metrics) can consume pool stats via the same state file aggregation pattern.

---
*Phase: 22-observability-metrics*
*Completed: 2026-02-24*

## Self-Check: PASSED

- FOUND: skills/spawn_specialist/pool.py
- FOUND: orchestration/monitor.py
- FOUND: .planning/phases/22-observability-metrics/22-02-SUMMARY.md
- FOUND commit 7bc6227 (Task 1)
- FOUND commit 210b057 (Task 2)
