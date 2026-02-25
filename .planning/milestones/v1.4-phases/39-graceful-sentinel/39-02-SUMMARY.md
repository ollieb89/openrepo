---
phase: 39-graceful-sentinel
plan: "02"
subsystem: infra
tags: [asyncio, sigterm, fire-and-forget, graceful-shutdown, pool, memorization]

requires:
  - phase: 39-01
    provides: SIGTERM handling in L3 entrypoint and spawn.py stop_timeout=30

provides:
  - _pending_memorize_tasks list tracking on L3ContainerPool
  - drain_pending_memorize_tasks() async drain method with configurable timeout
  - register_shutdown_handler() using loop.add_signal_handler (no fcntl deadlock)
  - _drain_and_stop() coroutine for loop shutdown after drain
  - Done-task pruning after each task completion
  - 6 unit tests covering drain behavior and signal handler registration

affects:
  - pool.py callers that use PoolRegistry or L3ContainerPool directly
  - Future phases that extend shutdown/drain behavior

tech-stack:
  added: []
  patterns:
    - "Fire-and-forget task tracking: asyncio.create_task() result stored in list for drain on shutdown"
    - "SIGTERM via loop.add_signal_handler (not signal.signal) to avoid fcntl deadlock"
    - "Idempotent SIGTERM handler using mutable closure dict {'flag': False}"
    - "Done-task pruning inline after task completion: [t for t if not t.done()]"

key-files:
  created:
    - tests/test_pool_shutdown.py
  modified:
    - skills/spawn_specialist/pool.py

key-decisions:
  - "Use loop.add_signal_handler() not signal.signal() — signal.signal() runs in C signal handler context, risk of deadlock if fcntl.flock() is held by state engine at signal time"
  - "Idempotency guard via mutable closure dict to handle double SIGTERM without double-scheduling drain"
  - "drain_pending_memorize_tasks() returns summary dict (pending/drained/timed_out) not raises — caller decides action"
  - "30s default drain timeout matches docker stop --stop-timeout 30 set in 39-01"

patterns-established:
  - "Pattern: Tracked fire-and-forget — always store asyncio.create_task() result for shutdown drain"
  - "Pattern: Asyncio signal handler — use loop.add_signal_handler for safe concurrent lock interaction"

requirements-completed:
  - REL-08

duration: 2min
completed: "2026-02-24"
---

# Phase 39 Plan 02: Fire-and-Forget Memorize Drain on SIGTERM Summary

**asyncio.create_task() memorize calls now tracked in _pending_memorize_tasks list, drained via 30s gather on SIGTERM using loop.add_signal_handler to prevent fcntl deadlock**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-24T16:37:33Z
- **Completed:** 2026-02-24T16:39:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `_pending_memorize_tasks: list` to `L3ContainerPool.__init__` for tracking fire-and-forget tasks
- Replaced bare `asyncio.create_task()` call with tracked version that appends to pending list
- Added done-task pruning after each task completion to prevent unbounded list growth
- Added `drain_pending_memorize_tasks()` async method — gathers pending tasks with configurable timeout, returns summary dict
- Added `register_shutdown_handler()` module-level function using `loop.add_signal_handler(signal.SIGTERM, ...)` (not `signal.signal()`)
- Added `_drain_and_stop()` coroutine that drains then calls `loop.stop()`
- All 6 unit tests pass with no Docker daemon required

## Task Commits

Each task was committed atomically:

1. **Task 1: Add memorize task tracking and SIGTERM drain to pool.py** - `7ea1ed8` (feat)
2. **Task 2: Create pool shutdown drain tests** - `59595a5` (test)

## Files Created/Modified

- `skills/spawn_specialist/pool.py` - Added _pending_memorize_tasks tracking, drain method, register_shutdown_handler, _drain_and_stop
- `tests/test_pool_shutdown.py` - 6 unit tests covering task tracking, drain success, drain timeout, empty drain, pruning, signal registration

## Decisions Made

- Used `loop.add_signal_handler()` rather than `signal.signal()` because the latter fires in C signal handler context and would deadlock if `fcntl.flock()` is held by the Jarvis state engine at that moment
- Idempotency guard uses mutable closure dict `{"flag": False}` so double SIGTERM is silently ignored
- `drain_pending_memorize_tasks()` returns a summary dict rather than raising — the `_drain_and_stop()` caller logs the result and stops the loop regardless
- 30s drain timeout matches the `stop_timeout=30` set on Docker containers in plan 39-01

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- REL-08 complete — pool SIGTERM drain is fully implemented and tested
- Phase 39 (Graceful Sentinel) plans 01 and 02 both shipped
- Pool shutdown path: SIGTERM → `_on_sigterm()` → `_drain_and_stop()` → `drain_pending_memorize_tasks(30s)` → `loop.stop()`
- No blockers for subsequent phases

---
*Phase: 39-graceful-sentinel*
*Completed: 2026-02-24*
