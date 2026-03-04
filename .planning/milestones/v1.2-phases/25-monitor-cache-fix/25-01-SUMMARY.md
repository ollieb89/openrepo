---
phase: 25-monitor-cache-fix
plan: 01
subsystem: orchestration
tags: [monitor, jarvis-state, cache, structured-logging, performance]

requires:
  - phase: 21-state-engine-performance
    provides: mtime-based in-memory JarvisState cache that delivers hits only when instances persist across reads
  - phase: 19-structured-logging
    provides: get_logger factory and StructuredFormatter for JSON stderr logging

provides:
  - Session-scoped JarvisState instance dict (js_instances) in tail_state() poll loop
  - Lazy creation and error-eviction logic for mid-tail project changes
  - Module-level structured logger in monitor.py emitting poll cycle DEBUG summaries
  - Documentation comments on one-shot JarvisState creation sites

affects: [25-monitor-cache-fix]

tech-stack:
  added: []
  patterns:
    - "Session-scoped instance dict (js_instances) keyed by project_id hoisted above polling while loop"
    - "Lazy creation with eviction-on-error for resilient mid-session project changes"
    - "Poll cycle DEBUG summary via structured logger (projects_polled, instances_cached)"

key-files:
  created: []
  modified:
    - orchestration/monitor.py

key-decisions:
  - "js_instances is local to tail_state() (not module-level) — implicit teardown on exit"
  - "Evict instance from js_instances on any read exception so file-recovery is detected next cycle"
  - "show_status/show_task_detail/show_pool_utilization are one-shot — no cross-call cache needed, documented with comments"
  - "Poll cycle log entry uses DEBUG level (not INFO) — cache stats are diagnostic, not operational"

patterns-established:
  - "Pre-create long-lived resources above polling loops; use lazy-creation for late-appearing items"
  - "Evict cached instances on error; re-create on next poll if file recovers"

requirements-completed: [PERF-04]

duration: 3min
completed: 2026-02-24
---

# Phase 25 Plan 01: Monitor Cache Fix Summary

**JarvisState session-scoped instance reuse in monitor.py tail_state() so the Phase 21 mtime cache delivers hits between poll cycles instead of cold-starting every iteration**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-24T02:39:02Z
- **Completed:** 2026-02-24T02:42:10Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Hoisted `js_instances: Dict[str, JarvisState] = {}` above `while True` loop in `tail_state()`, pre-creating instances for all projects with existing state files before polling begins
- Added lazy creation inside loop for projects that appear after tail starts, plus error-eviction so a disappearing state file causes a warning + skip (no crash), and re-creation if the file comes back
- Added `get_logger` import and `logger = get_logger('monitor')` at module level; DEBUG poll cycle summary emitted after each inner loop (`projects_polled`, `instances_cached`)
- Added one-shot documentation comments to `show_status`, `show_task_detail`, and `show_pool_utilization` JarvisState creation sites explaining cross-call cache is not needed

## Task Commits

Each task was committed atomically:

1. **Task 1 + 2: Hoist JarvisState out of poll loop; add structured logger and docs** - `086d208` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `~/.openclaw/orchestration/monitor.py` - Added session-scoped js_instances dict, lazy/evict logic, module logger, one-shot comments

## Decisions Made

- Tasks 1 and 2 committed together — Task 2 adds the logger import that Task 1 uses; separating them would produce an intermediate state with a broken import
- `js_instances` is function-local (not module-level) — implicit teardown on `tail_state()` exit matches CONTEXT.md decision
- Eviction on any exception (not just FileNotFoundError) — defensive for unexpected state engine errors
- Poll cycle log at DEBUG level — diagnostic only, consistent with CONTEXT.md

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- PERF-04 closed: monitor.py now participates in the Phase 21 mtime cache on every poll cycle
- Phase 25 has only one plan; phase is complete

---
*Phase: 25-monitor-cache-fix*
*Completed: 2026-02-24*
