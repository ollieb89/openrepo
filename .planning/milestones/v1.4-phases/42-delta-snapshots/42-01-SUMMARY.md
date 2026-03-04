---
phase: 42-delta-snapshots
plan: "01"
subsystem: testing
tags: [pytest, delta-snapshots, cursor, memory-retrieval, snapshot-pruning, tdd]

requires:
  - phase: 42-delta-snapshots
    provides: RESEARCH.md and CONTEXT.md with cursor design, test map, API contracts

provides:
  - "13-test RED scaffold covering PERF-05 through PERF-08 in tests/test_delta_snapshots.py"

affects:
  - 42-02 (Wave 1 implementation of JarvisState cursor helpers and spawn.py)
  - 42-03 (Wave 2 implementation of FastAPI filter and snapshot pruning)

tech-stack:
  added: []
  patterns:
    - "sys.path.insert(0, ...) at top of test file — matches test_spawn_memory.py pattern"
    - "sys.path.insert(0, docker/memory/memory_service) for FastAPI router imports"
    - "MagicMock context manager pattern (__enter__/__exit__) for httpx.Client mock"
    - "patch('orchestration.snapshot.load_project_config') for PERF-08 tests"

key-files:
  created:
    - tests/test_delta_snapshots.py
  modified: []

key-decisions:
  - "Tests import _filter_after from 'routers.retrieve' (with docker/memory/memory_service on sys.path) — not a deep package path"
  - "PERF-08 snapshot tests patch load_project_config, cleanup_old_snapshots, subprocess.run, and get_snapshot_dir — all four needed because capture_semantic_snapshot calls all of them"
  - "PERF-06 tests verify the (list, bool) return type from _retrieve_memories_sync — tests assert isinstance(result, tuple) before unpacking"

patterns-established:
  - "TDD RED scaffold: write all 13 tests before any implementation — Plans 02 and 03 rely on this file existing"
  - "Conservative pass-through: items with None/missing created_at pass through _filter_after unchanged"

requirements-completed:
  - PERF-05
  - PERF-06
  - PERF-07
  - PERF-08

duration: 8min
completed: 2026-02-24
---

# Phase 42 Plan 01: Delta Snapshots Test Scaffold Summary

**13-test RED scaffold for cursor-based memory retrieval and snapshot pruning — covering JarvisState cursor helpers, spawn.py tuple return type, FastAPI _filter_after, and capture_semantic_snapshot prune wiring**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-24T00:00:00Z
- **Completed:** 2026-02-24T00:08:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- 13 failing tests created in `tests/test_delta_snapshots.py` covering all four PERF requirements
- pytest collects exactly 13 tests with no collection errors or syntax issues
- All 13 tests fail in RED state — implementation does not exist yet
- Test names match the exact function names in RESEARCH.md test map

## Task Commits

1. **Task 1: Write test scaffold for all PERF-05 through PERF-08 behaviors** - `1da5c4a` (test)

**Plan metadata:** TBD (docs: complete plan)

## Files Created/Modified

- `tests/test_delta_snapshots.py` — 13 failing test functions covering PERF-05..08; 373 lines

## Decisions Made

- Used `sys.path.insert(0, "~/.openclaw/docker/memory/memory_service")` to import `_filter_after` from `routers.retrieve` — matches the plan's recommended import strategy
- PERF-08 tests patch four symbols in `orchestration.snapshot`: `load_project_config`, `cleanup_old_snapshots`, `subprocess.run`, `get_snapshot_dir` — all four are needed because `capture_semantic_snapshot` calls all of them during the snapshot write path
- PERF-06 tests assert `isinstance(result, tuple)` before unpacking to `(items, ok)` — gives clear failure message when function still returns bare list

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Test scaffold is complete and in RED state — Plans 02 and 03 can use `python3 -m pytest tests/test_delta_snapshots.py -x -q` to verify implementation progress
- Plans 02 and 03 must NOT modify this file except to fix tests that are genuinely wrong due to implementation-discovery issues
- Expected GREEN targets after Plan 02: PERF-05 (3 tests) + PERF-06 (3 tests) = 6 tests green
- Expected GREEN targets after Plan 03: PERF-07 (4 tests) + PERF-08 (3 tests) = 7 tests green

## Self-Check: PASSED

- `tests/test_delta_snapshots.py`: FOUND
- `42-01-SUMMARY.md`: FOUND
- Commit `1da5c4a`: FOUND
- pytest collects 13 tests, all 13 fail (RED state verified)

---
*Phase: 42-delta-snapshots*
*Completed: 2026-02-24*
