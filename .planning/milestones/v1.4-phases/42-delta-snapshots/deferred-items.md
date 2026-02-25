# Deferred Items — Phase 42 Delta Snapshots

Discovered during Plan 42-03 execution. Out of scope for Plan 42-03 (PERF-08 only).

## Reorganization test breakage (refactor/repo-structure branch)

**Discovered during:** Task 1 (PERF-08 implementation, test verification)

**Issue:** The `refactor/repo-structure` branch staged a large reorganization of `orchestration/` → `packages/orchestration/src/openclaw/` and `tests/` → `packages/orchestration/tests/`. The reorganized test files had multiple issues:
1. `packages/orchestration/tests/test_delta_snapshots.py` PERF-08 tests used `orchestration.snapshot.*` patch targets instead of `openclaw.snapshot.*`
2. `packages/orchestration/tests/test_delta_snapshots.py` lost `sys.path.insert` for docker memory service (needed by PERF-07 tests)
3. Multiple other test files (`test_l2_review_memorization.py`, `test_pool_memorization.py`, `test_recovery_scan.py`, etc.) still use `orchestration.snapshot.*` patch targets — will fail when `openclaw` package is the only import path

**Partially fixed:** Items 1 and 2 above were fixed inline as Rule 1 (bugs in test scaffold for Plan 42-03 scope).

**Still deferred:** The other test files using old `orchestration.*` patch targets:
- `packages/orchestration/tests/test_l2_review_memorization.py` — 11 tests
- `packages/orchestration/tests/test_pool_memorization.py` — 5 tests
- `packages/orchestration/tests/test_recovery_scan.py` — 1 test
- Potentially others

**Action needed:** Update all remaining test patch targets from `orchestration.*` to `openclaw.*` as part of the refactor/repo-structure work.
