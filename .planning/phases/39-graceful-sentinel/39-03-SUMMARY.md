---
phase: 39-graceful-sentinel
plan: "03"
subsystem: infra
tags: [recovery, startup-scan, pool, project-config, orphaned-tasks]

requires:
  - phase: 39-02
    provides: drain_pending_memorize_tasks() and SIGTERM handler on L3ContainerPool

provides:
  - run_recovery_scan() async method on L3ContainerPool
  - recovery_policy validation in get_pool_config() with _VALID_RECOVERY_POLICIES constant
  - recovery_policy added to _POOL_CONFIG_DEFAULTS (default: mark_failed)
  - 10 unit tests covering all policies, edge cases, and config validation

affects:
  - pool.py callers — run_recovery_scan() should be called at pool startup
  - project.json l3_overrides — new recovery_policy key available
  - orchestration/project_config.py — new _VALID_RECOVERY_POLICIES constant

tech-stack:
  added: []
  patterns:
    - "Startup recovery scan: list_active_tasks() -> filter by recoverable states -> apply policy"
    - "Conservative auto_retry: check git for partial commits before re-queuing"
    - "Missing spawn_requested_at treated as expired (not silently skipped)"
    - "Recovery policy validation follows same pattern as overflow_policy validation"

key-files:
  created:
    - tests/test_recovery_scan.py
  modified:
    - skills/spawn_specialist/pool.py
    - orchestration/project_config.py

key-decisions:
  - "auto_retry checks for existing commits on l3/task-{id} branch before re-queuing — conservative fallback to mark_failed if partial work exists"
  - "auto_retry retry limit of 1 — retries once then falls back to mark_failed (prevents infinite retry loops)"
  - "Missing spawn_requested_at treated as expired with a warning log — silently skipping could mask orphaned tasks"
  - "run_recovery_scan() always logs a startup summary even with zero scanned tasks"
  - "For simplicity, auto_retry re-queue is represented as a failed task with RECOVERED prefix — actual re-spawn scheduling is deferred to future phases"

patterns-established:
  - "Pattern: Startup recovery scan — pool instantiation should call run_recovery_scan() before accepting new tasks"
  - "Pattern: Conservative git check — use subprocess git log to verify branch state before taking recovery action"

requirements-completed:
  - REL-06
  - REL-07

duration: 2min
completed: "2026-02-24"
---

# Phase 39 Plan 03: Pool Startup Recovery Scan Summary

**run_recovery_scan() added to L3ContainerPool — detects orphaned tasks at startup and applies configurable mark_failed/auto_retry/manual policy with git-based partial-commit detection**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-24T16:42:08Z
- **Completed:** 2026-02-24T16:44:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `recovery_policy` key to `_POOL_CONFIG_DEFAULTS` (default: `mark_failed`) in both `project_config.py` and `pool.py`
- Added `_VALID_RECOVERY_POLICIES = {"mark_failed", "auto_retry", "manual"}` constant to `project_config.py`
- Added `recovery_policy` validation block in `get_pool_config()` following exact same pattern as `overflow_policy`
- Updated `get_pool_config()` docstring return dict to include `"recovery_policy": str`
- Added `import subprocess` to `pool.py`
- Added `run_recovery_scan()` async method on `L3ContainerPool` after `drain_pending_memorize_tasks()`
- Scan reads non-terminal tasks via `list_active_tasks()`, filters to `in_progress/interrupted/starting` states, checks age vs skill timeout
- `mark_failed` policy: calls `update_task(status="failed", activity_entry="RECOVERED: ...")`
- `auto_retry` policy: checks `retry_count >= 1` for retry limit, then checks git branch for partial commits; falls back to `mark_failed` on either condition; logs retry intent with `failed` status and `auto_retry` message
- `manual` policy: logs but does not modify state, increments `manual` counter
- Missing `spawn_requested_at`: logs warning, treats task as expired (`age_s = timeout_s + 1`)
- Startup summary always logged via `logger.info("Pool startup: recovery scan complete", extra={...})`
- All 10 unit tests pass with zero Docker daemon dependency

## Task Commits

Each task was committed atomically:

1. **Task 1: Add recovery_policy config and run_recovery_scan to pool** - `cb8c658` (feat)
2. **Task 2: Create recovery scan tests** - `f7fd9c7` (test)

## Files Created/Modified

- `orchestration/project_config.py` - Added recovery_policy to defaults, _VALID_RECOVERY_POLICIES constant, validation block in get_pool_config(), updated docstring
- `skills/spawn_specialist/pool.py` - Added import subprocess, recovery_policy to _POOL_DEFAULTS, run_recovery_scan() method
- `tests/test_recovery_scan.py` - 10 unit tests covering all policies, edge cases, and config validation

## Decisions Made

- `auto_retry` conservatively falls back to `mark_failed` if any git commits exist on the `l3/task-{id}` staging branch — prevents overwriting partial work
- Retry limit of 1 enforced via `metadata.retry_count >= 1` check — prevents infinite retry loops on consistently failing tasks
- For simplicity in this phase, `auto_retry` re-queue is represented as `failed` state with `RECOVERED: ... -> auto_retry (queued for re-spawn)` message — actual re-spawn scheduling is out of scope; the recovery scan identifies and flags, operator or next pool invocation acts on it
- Missing `spawn_requested_at` triggers a warning and treats age as expired rather than silently skipping — ensures no orphaned tasks slip through due to incomplete metadata

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- REL-06 and REL-07 complete — recovery scan is fully implemented and tested
- Phase 39 (Graceful Sentinel) all 3 plans shipped: SIGTERM handling (01), memorize drain (02), recovery scan (03)
- Pool shutdown path now covers both graceful SIGTERM drain and startup recovery of orphaned tasks
- No blockers for Phase 40 (Memory Health Monitor)

---
*Phase: 39-graceful-sentinel*
*Completed: 2026-02-24*
