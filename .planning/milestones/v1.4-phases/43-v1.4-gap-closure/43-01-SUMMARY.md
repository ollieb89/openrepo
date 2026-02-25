---
phase: 43-v1.4-gap-closure
plan: 01
subsystem: dashboard-api, spawn-pool
tags: [bug-fix, integration, subprocess-paths, sigterm, shutdown, idempotency]
dependency_graph:
  requires: []
  provides: [working-suggestions-api, soul-renderer-rerender, sigterm-drain-wired]
  affects: [packages/dashboard/src/app/api/suggestions, skills/spawn/pool.py]
tech_stack:
  added: []
  patterns:
    - ORCHESTRATION_ROOT constant for monorepo-aware subprocess path resolution
    - Module-level idempotency guard (_shutdown_handler_registered) for signal handler registration
key_files:
  created: []
  modified:
    - packages/dashboard/src/app/api/suggestions/route.ts
    - packages/dashboard/src/app/api/suggestions/[id]/action/route.ts
    - skills/spawn/pool.py
    - packages/orchestration/tests/test_pool_shutdown.py
decisions:
  - ORCHESTRATION_ROOT constant derived from OPENCLAW_ROOT env var at module scope in both route files — single source of truth for monorepo-reorganized path
  - existsSync startup warn in both routes surfaces misconfiguration at server start rather than at request time
  - asyncio.get_running_loop() used in spawn_task() (not get_event_loop()) — spawn_task() is async, get_running_loop() is correct and raises RuntimeError on miscall (fast failure)
  - Idempotency guard is module-level flag (_shutdown_handler_registered) not closure — accessible by patch.object in tests, reset per test without module reload
  - rerenderSoul() try/catch semantics preserved in action/route.ts — consistent with Phase 41 Plan 02 decision (failure logged, accept continues)
metrics:
  duration: ~15 minutes
  completed: 2026-02-25T00:14:41Z
  tasks_completed: 2
  files_modified: 4
---

# Phase 43 Plan 01: v1.4 Gap Closure — Subprocess Paths + SIGTERM Wiring Summary

Three wiring gaps identified by the v1.4 milestone audit closed with surgical edits: dashboard API routes now resolve Python subprocess paths through the post-refactor monorepo layout, and the SIGTERM drain guarantee in spawn_task() is now wired to register_shutdown_handler() with an idempotency guard and regression test.

## What Was Built

### Task 1: Fix dashboard subprocess paths

Both suggestion API routes used pre-refactor paths (`path.join(OPENCLAW_ROOT, 'orchestration', 'suggest.py')` and `path.join(OPENCLAW_ROOT, 'orchestration', 'soul_renderer.py')`) which no longer exist after the `packages/orchestration/` monorepo reorganisation.

**Fixed in route.ts:**
- Added `ORCHESTRATION_ROOT = path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw')`
- Added `existsSync` startup warning for `cli/suggest.py`
- Changed `orchestrationPath` to `path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py')`

**Fixed in action/route.ts:**
- Added same `ORCHESTRATION_ROOT` constant
- Added `existsSync` startup warning for `soul_renderer.py`
- Changed `rerenderSoul()` path to `path.join(ORCHESTRATION_ROOT, 'soul_renderer.py')`
- Error handling semantics preserved (try/catch around rerenderSoul unchanged)

### Task 2: Wire shutdown handler + regression test

`register_shutdown_handler()` was fully implemented but never called from `spawn_task()`, meaning the SIGTERM drain guarantee (REL-08) was not held at runtime.

**Fixed in pool.py:**
- Module-level flag: `_shutdown_handler_registered = False`
- `register_shutdown_handler()` sets `global _shutdown_handler_registered = True` as first statement
- `spawn_task()` checks `_shutdown_handler_registered` after `run_recovery_scan()`, calls `register_shutdown_handler(loop, pool)` when False using `asyncio.get_running_loop()`
- Logs debug message on first registration

**Added regression test in test_pool_shutdown.py:**
- `test_spawn_task_wires_shutdown_handler` — patches `_shutdown_handler_registered = False`, mocks pool and config, asserts `register_shutdown_handler` is called once after `spawn_task()`

## Verification

- Path fixes: ORCHESTRATION_ROOT in both route files, old `'orchestration/suggest.py'` and `'orchestration/soul_renderer.py'` strings absent
- Pool shutdown tests: 7/7 pass (6 pre-existing + 1 new regression test)
- Full suite: 148/148 tests pass

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

### Files exist:
- [x] `packages/dashboard/src/app/api/suggestions/route.ts` — FOUND
- [x] `packages/dashboard/src/app/api/suggestions/[id]/action/route.ts` — FOUND
- [x] `skills/spawn/pool.py` — FOUND (modified)
- [x] `packages/orchestration/tests/test_pool_shutdown.py` — FOUND (modified)

### Commits exist:
- [x] `7290673` — fix(43-01): correct subprocess paths for suggest.py and soul_renderer.py
- [x] `9a629a5` — fix(43-01): wire register_shutdown_handler() in spawn_task() with idempotency guard

## Self-Check: PASSED
