---
phase: 42-delta-snapshots
plan: "02"
subsystem: orchestration, memory-service
tags: [cursor, memory-retrieval, delta-fetch, state-engine, fastapi, perf-05, perf-06, perf-07]

requires:
  - phase: 42-delta-snapshots
    plan: "01"
    provides: "13-test RED scaffold in tests/test_delta_snapshots.py"

provides:
  - "JarvisState.get_memory_cursor() and update_memory_cursor() — PERF-05"
  - "Cursor-aware _retrieve_memories_sync returning (list, bool) tuple — PERF-06"
  - "memU /retrieve endpoint with optional created_after filter via _filter_after() — PERF-07"

affects:
  - "42-03: PERF-08 snapshot pruning (no dependency on this plan's changes)"

tech-stack:
  added: []
  patterns:
    - "LOCK_EX read-modify-write pattern for cursor persistence in JarvisState"
    - "Try/except import guards in retrieve.py to allow test-env import without fastapi"
    - "Naive datetime normalization for consistent timezone-unaware comparison in _filter_after"

key-files:
  created: []
  modified:
    - orchestration/state_engine.py
    - skills/spawn_specialist/spawn.py
    - docker/memory/memory_service/models.py
    - docker/memory/memory_service/routers/retrieve.py
    - tests/test_spawn_memory.py

key-decisions:
  - "retrieve.py uses try/except ImportError guards for both fastapi and relative imports — allows _filter_after to be imported in test env where only docker/memory/memory_service is on sys.path"
  - "Naive datetime normalization: cutoff and item_dt both stripped to naive UTC via .replace(tzinfo=None) before comparison — avoids TypeError on Python 3.11+ when comparing TZ-aware ISO strings"
  - "empty_url returns ([], True) not ([], False) — not a network error, callers may advance cursor safely"
  - "test_spawn_memory.py updated to unpack (list, bool) tuples — preserves existing test semantics"

duration: 5min
completed: 2026-02-24
---

# Phase 42 Plan 02: Delta Snapshots — Cursor Helpers and Retrieve Filter Summary

**JarvisState cursor read/write helpers (PERF-05), cursor-aware spawn retrieval with (list, bool) return type (PERF-06), and memU /retrieve created_after filter (PERF-07) — 10 of 13 tests green**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-24T22:41:18Z
- **Completed:** 2026-02-24T22:46:06Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added `get_memory_cursor()` and `update_memory_cursor()` to `JarvisState` using the existing LOCK_EX read-modify-write pattern (PERF-05)
- Changed `_retrieve_memories_sync` to return `(list, bool)` tuple; `bool=False` on network failure prevents cursor advancement (PERF-06)
- Added `created_after` parameter to `_retrieve_memories_sync` payload when provided (PERF-06)
- Wired cursor read/update around memory retrieval in `spawn_l3_specialist` using same `jarvis` instance (PERF-06)
- Added `created_after: Optional[str]` field to `RetrieveRequest` pydantic model (PERF-07)
- Added `_filter_after()` helper and filter block in `/retrieve` endpoint (PERF-07)
- 10 of 13 tests in `test_delta_snapshots.py` now pass; 3 PERF-08 tests remain failing (Plan 03)
- 144 total tests passing across full suite

## Task Commits

1. **Task 1: JarvisState cursor helpers + cursor-aware spawn retrieval** - `cd29967`
2. **Task 2: memU retrieve router — created_after filter** - `6ccf004`

## Files Created/Modified

- `orchestration/state_engine.py` — Added `get_memory_cursor()` and `update_memory_cursor()` methods at end of JarvisState class
- `skills/spawn_specialist/spawn.py` — `_retrieve_memories_sync` returns `(list, bool)`, cursor wired in `spawn_l3_specialist`
- `docker/memory/memory_service/models.py` — `RetrieveRequest` gains `created_after: Optional[str] = None`
- `docker/memory/memory_service/routers/retrieve.py` — `_filter_after()` helper added, filter block in retrieve endpoint
- `tests/test_spawn_memory.py` — Updated 4 test assertions to unpack `(list, bool)` return type

## Decisions Made

- Used try/except import guards in `retrieve.py` so `_filter_after` is importable in test environments without fastapi installed
- Normalized both cutoff and item_dt to naive UTC datetimes before comparison — Python 3.11+ raises `TypeError` when comparing TZ-aware vs TZ-naive datetimes directly
- Empty `base_url` case returns `([], True)` — not a network error, so cursor can advance (no false negatives)
- Updated `test_spawn_memory.py` assertions to unpack `(list, bool)` tuples — Rule 1 auto-fix for regression from return type change

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Regression] test_spawn_memory.py assertions incompatible with (list, bool) return type**
- **Found during:** Task 1 verification
- **Issue:** 4 tests in `test_spawn_memory.py` used `assert result == []` or `assert result == mock_items` which fail when `result` is a `(list, bool)` tuple
- **Fix:** Unpacked `items, ok = result` in each affected test; added `assert isinstance(result, tuple)` guard
- **Files modified:** `tests/test_spawn_memory.py`
- **Commit:** `cd29967` (same Task 1 commit)

**2. [Rule 1 - Bug] Timezone-naive vs timezone-aware comparison in _filter_after**
- **Found during:** Task 2 PERF-07 test run — `test_filter_after_unix_float` and `test_filter_after_timestamp` failing
- **Issue:** `datetime.fromisoformat("2026-02-24T10:00:00+00:00")` on Python 3.11+ returns TZ-aware datetime; `datetime.utcfromtimestamp(ts)` returns naive datetime; comparison raises `TypeError` caught by conservative except → items pass through unchecked
- **Fix:** Strip tzinfo from both cutoff and item_dt (`.replace(tzinfo=None)`) before comparison, normalizing to naive UTC
- **Files modified:** `docker/memory/memory_service/routers/retrieve.py`
- **Commit:** `6ccf004`

**3. [Rule 3 - Blocker] fastapi not installed in root test env**
- **Found during:** Task 2 test run — `ModuleNotFoundError: No module named 'fastapi'` when importing `routers.retrieve`
- **Issue:** Test adds `docker/memory/memory_service` to sys.path and imports `_filter_after` directly; fastapi is only present in the Docker container
- **Fix:** try/except ImportError guards for fastapi and relative imports; fallback to stdlib `logging.getLogger` when package imports fail
- **Files modified:** `docker/memory/memory_service/routers/retrieve.py`
- **Commit:** `6ccf004`

## Self-Check: PASSED

- `orchestration/state_engine.py`: get_memory_cursor — FOUND
- `orchestration/state_engine.py`: update_memory_cursor — FOUND
- `skills/spawn_specialist/spawn.py`: created_after — FOUND
- `docker/memory/memory_service/models.py`: created_after — FOUND
- `docker/memory/memory_service/routers/retrieve.py`: _filter_after — FOUND
- Commit `cd29967`: FOUND
- Commit `6ccf004`: FOUND
- 10 of 13 tests passing (PERF-05 + PERF-06 + PERF-07 green)

---
*Phase: 42-delta-snapshots*
*Completed: 2026-02-24*
