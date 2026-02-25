---
phase: 40-memory-health-monitor
plan: 01
subsystem: memory
tags: [fastapi, pydantic, memu, cosine-similarity, health-scan, memory-hygiene]

# Dependency graph
requires:
  - phase: 26-38-agent-memory (v1.3)
    provides: "memU REST service, list_memory_items(), update_memory_item(), delete_memory_item(), cosine_topk()"
provides:
  - "POST /memories/health-scan endpoint — staleness + conflict detection with scored flags"
  - "GET /memories/health-flags endpoint — cached flag retrieval from last scan"
  - "PUT /memories/{memory_id} endpoint — content update via existing memu CRUD pipeline"
  - "HealthFlag, HealthScanRequest, HealthScanResult, MemoryUpdateRequest Pydantic models"
  - "scan_engine.py — pure-Python staleness and conflict detection (no pydantic/memu deps at import)"
affects:
  - 40-02 (dashboard health UI — consumes health-scan endpoint and flags)
  - 40-03 (if applicable — scheduled scan logic)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "scan_engine.py extracted as dependency-free module for testability — no FastAPI/pydantic at import time"
    - "Deferred lazy imports (cosine_topk, pendulum) inside functions to avoid top-level dep requirements"
    - "app.state.health_flags dict for ephemeral flag storage — regenerated on each scan, keyed by memory_id"
    - "_ItemProxy wraps list_memory_items() dicts for attribute access in scan helpers"
    - "Test-local cosine function mirrors production algorithm without numpy — validates dedup logic independently"

key-files:
  created:
    - docker/memory/memory_service/scan_engine.py
    - tests/test_health_scan.py
  modified:
    - docker/memory/memory_service/models.py
    - docker/memory/memory_service/service.py
    - docker/memory/memory_service/routers/memories.py

key-decisions:
  - "scan_engine.py extracted as stdlib-only module so scan algorithm is testable without pydantic/memu in root env"
  - "Lazy import of cosine_topk and pendulum inside functions — _check_staleness works without memu at import time"
  - "user_id required (non-optional) in HealthScanRequest to prevent cross-project scope leak (Pitfall 6)"
  - "content required (non-optional) in MemoryUpdateRequest to prevent empty-body ValueError from memu CRUD (Pitfall 1)"
  - "last_reinforced_at absence treated as 'fresh' if created_at is within retrieval_window — avoids Pitfall 2 false positives"
  - "Conflict pair deduplication via tuple(sorted([id_a, id_b])) seen-set — Pitfall 3 prevention"
  - "Test vectors chosen to have cosine similarity in [0.75, 0.97] window — base=[1,0,0,0], other=[0.9,0.4,0,0] gives ~0.914"

patterns-established:
  - "Health flags stored ephemerally in app.state.health_flags — dict keyed by memory_id, replaced on each scan"
  - "Scan endpoints follow existing GET/DELETE pattern: get memu from app.state, return 503 if None, 500 on error"
  - "Pure-Python algorithm modules (no heavy deps) in Docker service enable root-env unit testing"

requirements-completed: [QUAL-01, QUAL-02, QUAL-03, QUAL-04]

# Metrics
duration: 7min
completed: 2026-02-24
---

# Phase 40 Plan 01: Memory Health Monitor Backend Summary

**Health scan engine with staleness + cosine-conflict detection, three new FastAPI endpoints (POST health-scan, GET health-flags, PUT memories/:id), and 19 unit tests all passing**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-24T17:29:28Z
- **Completed:** 2026-02-24T17:36:37Z
- **Tasks:** 2
- **Files modified:** 5 (3 modified + 2 created)

## Accomplishments
- Memory health scan engine in `scan_engine.py`: `_check_staleness` (age + retrieval frequency) and `_find_conflicts` (cosine topk with dedup)
- Three new FastAPI endpoints wired into `routers/memories.py`: POST health-scan, GET health-flags, PUT memories/{id}
- Pydantic models: `HealthFlag`, `HealthScanRequest`, `HealthScanResult`, `MemoryUpdateRequest`
- 19 unit tests covering all staleness scenarios, conflict deduplication, self-exclusion, PUT delegation, and empty corpus

## Task Commits

Each task was committed atomically:

1. **Task 1: Health scan models and engine** - `08848b2` (feat)
2. **Task 2: REST endpoints and tests** - `47c45ab` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `docker/memory/memory_service/models.py` - Added HealthFlag, HealthScanRequest, HealthScanResult, MemoryUpdateRequest models
- `docker/memory/memory_service/scan_engine.py` - Pure-Python staleness + conflict detection logic (no pydantic/memu deps)
- `docker/memory/memory_service/service.py` - run_health_scan() orchestrator + _ItemProxy for dict→attribute access
- `docker/memory/memory_service/routers/memories.py` - POST /memories/health-scan, GET /memories/health-flags, PUT /memories/{id}
- `tests/test_health_scan.py` - 19 unit tests covering all scan engine behaviors

## Decisions Made
- `scan_engine.py` extracted as a dependency-free module (no pydantic, no memu imports at module level). This allows the scan algorithm to be tested in the root Python environment which lacks those packages. Production code in Docker has all deps.
- `cosine_topk` and `pendulum` imported lazily inside functions — `_check_staleness` is callable without memu installed.
- Test-local `_find_conflicts_with_custom_topk` uses pure-Python cosine (no numpy) to validate deduplication and filtering logic without needing the memu package in the test env.
- Test vectors selected to produce cosine ~0.914 (within [0.75, 0.97] window): `[1.0, 0.0, 0.0, 0.0]` vs `[0.9, 0.4, 0.0, 0.0]`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extracted scan logic into scan_engine.py to unblock tests**
- **Found during:** Task 2 (running tests)
- **Issue:** `docker/memory/memory_service/models.py` imports pydantic; `service.py` imports memu and pendulum. Root Python env lacks all three packages. Tests couldn't even import the test module.
- **Fix:** Extracted `_check_staleness` and `_find_conflicts` into `scan_engine.py` with lazy imports of pendulum and cosine_topk inside function bodies (not at module level). Tests import from `scan_engine.py` directly. Test-local `_find_conflicts_with_custom_topk` replicates the algorithm with pure stdlib math for additional isolation.
- **Files modified:** `docker/memory/memory_service/scan_engine.py` (created), `docker/memory/memory_service/service.py` (import from scan_engine)
- **Verification:** All 19 tests pass; 95 existing tests still pass
- **Committed in:** `08848b2` (Task 1 commit), `47c45ab` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Required refactor makes production code cleaner (algorithm separated from FastAPI layer) and improves testability. No scope creep.

## Issues Encountered
- Test embedding vectors initially had cosine similarity ~0.9997 (near-duplicate range), above the default `similarity_max=0.97`. Fixed by selecting vectors with cosine ~0.914: `[1.0, 0.0, 0.0, 0.0]` vs `[0.9, 0.4, 0.0, 0.0]`.

## Next Phase Readiness
- Backend health scan API is complete — POST /memories/health-scan returns HealthScanResult, PUT /memories/:id updates content
- Dashboard (Plan 02) can call POST /api/memory/health-scan → proxy to service, render badges and Health tab
- Flags are ephemeral (app.state dict) — dashboard must trigger a scan on load or on button press, not rely on persistent state

---
*Phase: 40-memory-health-monitor*
*Completed: 2026-02-24*
