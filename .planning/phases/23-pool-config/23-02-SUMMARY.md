---
phase: 23-pool-config
plan: 02
subsystem: infra
tags: [pool, concurrency, semaphore, overflow-policy, pool-mode, monitor, l3-specialist]

# Dependency graph
requires:
  - phase: 23-pool-config
    plan: 01
    provides: get_pool_config() helper, _pool_config attached to pool instances
provides:
  - PoolOverflowError exception class for reject/wait-timeout scenarios
  - Shared vs isolated pool modes in PoolRegistry with lazy shared semaphore
  - Overflow policy enforcement (reject/wait/priority) per project config
  - Monitor pool subcommand with config-driven max_concurrent, pool_mode, overflow_policy display
affects: [pool, monitor, project_config]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Overflow policy enforcement: read _pool_config on each spawn_and_monitor() call — no restart needed"
    - "Shared semaphore: lazy creation on first shared-mode pool request in PoolRegistry"
    - "Reject policy: semaphore._value == 0 check before acquire — immediate PoolOverflowError"
    - "Wait policy: asyncio.wait_for(semaphore.acquire(), timeout=queue_timeout_s) — PoolOverflowError on timeout"
    - "Priority policy: asyncio.PriorityQueue infrastructure — lower number = higher priority"
    - "Hot-reload pool_mode: PoolRegistry.get_pool() swaps semaphore reference when pool_mode changes"

key-files:
  created: []
  modified:
    - skills/spawn_specialist/pool.py
    - orchestration/monitor.py

key-decisions:
  - "PoolOverflowError raised by both reject (immediate) and wait-timeout (after queue_timeout_s) — callers catch same exception type"
  - "Shared semaphore created lazily on first shared-mode project request — capacity from first project's max_concurrent"
  - "priority policy uses asyncio.PriorityQueue + semaphore.acquire() — infrastructure in place for L2 to pass priority=0"
  - "Monitor TOTAL saturation uses sum(per-project max) not N*3 — correct when projects have different max_concurrent"
  - "Semaphore release in spawn_and_monitor() via try/finally instead of async with — required for policy-split acquisition paths"

requirements-completed: [POOL-02, POOL-03]

# Metrics
duration: 5min
completed: 2026-02-24
---

# Phase 23 Plan 02: Pool Isolation Modes and Overflow Policies Summary

**Pool isolation modes (shared/isolated) and overflow policies (reject/wait/priority) implemented in PoolRegistry and L3ContainerPool; monitor pool subcommand reads config-driven values**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-24T03:16:12Z
- **Completed:** 2026-02-24T03:21:27Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `PoolOverflowError` exception class to `pool.py` — raised by both `reject` (immediate) and `wait` (timeout) overflow policies
- Implemented "reject" overflow policy: checks `semaphore._value == 0` before acquisition, raises `PoolOverflowError` immediately with running task IDs and retry suggestion
- Implemented "wait" overflow policy: uses `asyncio.wait_for(semaphore.acquire(), timeout=queue_timeout_s)`, raises `PoolOverflowError` on timeout with context details
- Implemented "priority" overflow policy infrastructure: `asyncio.PriorityQueue` on each pool, `priority` parameter on `spawn_and_monitor()` (default 1; 0 = elevated)
- Added shared vs isolated pool modes to `PoolRegistry`: shared-mode projects reference a lazily-created global semaphore; isolated-mode projects get dedicated per-project semaphores
- Hot-reload for `pool_mode`: `PoolRegistry.get_pool()` swaps semaphore reference on mode change; `overflow_policy` changes are automatic (read from `_pool_config` on each spawn)
- Updated `orchestration/monitor.py` to import `get_pool_config` and use per-project `max_concurrent`, `pool_mode`, and `overflow_policy` in `show_pool_utilization()`
- Monitor pool table now has `MAX`, `MODE`, and `OVERFLOW` columns; summary TOTAL uses sum of per-project max instead of hardcoded `N*3`

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement pool isolation modes and overflow policies** - `0454326` (feat)
2. **Task 2: Update monitor pool subcommand to use config-driven max_concurrent** - `f18f226` (feat)

## Files Created/Modified

- `skills/spawn_specialist/pool.py` — Added `PoolOverflowError`, `_pool_mode` and `_priority_queue` on pool instances, overflow policy enforcement in `spawn_and_monitor()`, shared semaphore in `PoolRegistry`, hot-reload for pool_mode
- `orchestration/monitor.py` — Added `get_pool_config` import, per-project config read in `show_pool_utilization()`, `MAX`/`MODE`/`OVERFLOW` columns in pool table

## Decisions Made

- `PoolOverflowError` is the single exception type for all overflow scenarios — callers don't need to distinguish reject vs wait-timeout at the exception type level
- Shared semaphore is created lazily on first shared-mode `get_pool()` call with capacity from that project's `max_concurrent` — consistent with lazy-init pattern throughout the codebase
- `priority` policy uses a `PriorityQueue` alongside the semaphore — infrastructure is in place for L2 to pass `priority=0` for elevated tasks without further pool changes
- Semaphore released via `try/finally` instead of `async with` — required because the three policy paths (reject/wait/priority) acquire the semaphore via different mechanisms before reaching the shared execution block
- Monitor TOTAL saturation denominator is `sum(per-project max_concurrent)` not `len(rows) * 3` — correct when projects have different limits

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

A `git stash` attempt during verification caused the monitor.py changes to be reverted (stash succeeded but stash pop failed due to pycache conflicts). Changes were re-applied cleanly before the Task 2 commit.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 23 is complete (POOL-01, POOL-02, POOL-03 all done)
- Projects can set `l3_overrides.pool_mode` and `l3_overrides.overflow_policy` in their project.json immediately
- L2 agents can pass `priority=0` to `spawn_and_monitor()` for task elevation under "priority" overflow policy

## Self-Check: PASSED

All files found. All commits verified.
