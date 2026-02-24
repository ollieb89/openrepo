---
phase: 27-memory-client-scoping
plan: 01
subsystem: orchestration
tags: [httpx, respx, pytest-asyncio, memory, scoping, memu]

# Dependency graph
requires:
  - phase: 26-memory-service
    provides: memU REST API at /memorize, /retrieve, /health endpoints

provides:
  - MemoryClient class with constructor-enforced project_id + agent_type scoping
  - AgentType(str, Enum) with l2_pm, l3_code, l3_test values
  - MemorizeResult and RetrieveResult frozen dataclasses
  - Sentinel degradation: health()->False, memorize()->None, retrieve()->[] on failure
  - tests/test_memory_client.py: 10-test suite with respx mocks, no live service needed
  - tests/pytest.ini: asyncio_mode=auto for pytest-asyncio

affects:
  - phase-28-spawn-memory-integration
  - phase-29-l2-review-memory
  - phase-30-memory-review-flows
  - phase-31-memory-ui

# Tech tracking
tech-stack:
  added: [httpx, respx, pytest-asyncio]
  patterns:
    - Constructor-enforced scoping — required args at construction time make unscoped calls impossible
    - Sentinel degradation pattern — memory operations never raise, always return typed sentinels
    - respx transport mocking — mock httpx at network layer without live service

key-files:
  created:
    - orchestration/memory_client.py
    - tests/test_memory_client.py
    - tests/pytest.ini
  modified: []

key-decisions:
  - "AgentType(str, Enum) inherits str so values serialize to JSON without .value"
  - "Split timeouts: 3s retrieve (fast path), 10s memorize (embedding generation is slow)"
  - "retrieve() where clause maps project_id to user_id — memU user_id is the project isolation key"
  - "httpx installed via brew Python pip3 (system Python externally managed)"

patterns-established:
  - "MemoryClient scoping pattern: project_id + agent_type required at __init__, no defaults"
  - "respx.mock(base_url=...) decorator for async httpx tests with auto asyncio mode"
  - "Degradation: catch Exception broadly in client methods, log warning, return sentinel"

requirements-completed: [SCOPE-01, SCOPE-02, SCOPE-03]

# Metrics
duration: 8min
completed: 2026-02-24
---

# Phase 27 Plan 01: Memory Client + Scoping Summary

**httpx AsyncClient wrapper with constructor-enforced project_id/agent_type scoping, sentinel degradation returns, and 10-test respx suite proving cross-project isolation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-24T07:24:55Z
- **Completed:** 2026-02-24T07:32:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- MemoryClient requires `base_url`, `project_id`, `agent_type` at construction — omitting either scoping param raises TypeError, making unscoped memory calls impossible by design
- `memorize()` auto-embeds `project_id` as `user.user_id` and `agent_type` as `user.agent_type` in every POST payload; `retrieve()` auto-sets `where.user_id = project_id` in every POST
- 10 tests pass with respx mocks at the httpx transport level — no live memU service required; key isolation test (test_project_isolation) proves client_b's retrieve is scoped to project-b even after client_a memorized

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MemoryClient module with enforced scoping** - `ed5b1bd` (feat)
2. **Task 2: Create test infrastructure and comprehensive test suite** - `5412aae` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `orchestration/memory_client.py` — MemoryClient class, AgentType enum, MemorizeResult/RetrieveResult dataclasses, MEMU_SERVICE_URL constant
- `tests/test_memory_client.py` — 10-test suite: constructor enforcement, health, memorize scoping, retrieve scoping, project isolation, context manager cleanup
- `tests/pytest.ini` — asyncio_mode = auto for pytest-asyncio

## Decisions Made

- AgentType inherits from `str` so enum values serialize directly to JSON without `.value` (e.g. `AgentType.L3_CODE` in a dict becomes `"l3_code"`)
- Split timeouts: 3s for retrieve (fast path, fail fast), 10s for memorize (embedding generation can be slow)
- The retrieve `where` clause maps `project_id` to `user_id` — this is the memU per-user isolation key; project boundaries map directly to memU user boundaries
- `httpx`, `pytest-asyncio`, `respx` installed via brew Python's `pip3` (system Python is externally managed and cannot be modified)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed httpx and test dependencies via brew pip3**
- **Found during:** Task 1 (import verification)
- **Issue:** httpx not installed in the brew Python environment; system `pip` blocked by externally-managed-environment policy
- **Fix:** Used `pip3 install httpx pytest pytest-asyncio respx --break-system-packages` targeting the brew Python at `/home/linuxbrew/.linuxbrew/bin/python3`
- **Files modified:** None (environment change only)
- **Verification:** `python3 -c "import httpx"` succeeds; all 10 tests pass
- **Committed in:** Part of Task 1 commit (environment, not code)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing environment dependency)
**Impact on plan:** Required to run tests at all. No scope creep.

## Issues Encountered

- System Python (`/usr/bin/python3`) is Debian-externally-managed — `pip install` without `--break-system-packages` fails. The actual Python3 on this machine is at `/home/linuxbrew/.linuxbrew/bin/python3` (Python 3.14.3). Used `pip3` which targets the brew Python and accepted `--break-system-packages` correctly.

## User Setup Required

None — no external service configuration required. Tests run with respx mocks, no live memU service needed.

## Next Phase Readiness

- MemoryClient is complete and ready for Phase 28 (spawn.py integration) and Phase 29 (L2 review flows)
- Import pattern: `from orchestration.memory_client import MemoryClient, AgentType, MEMU_SERVICE_URL`
- Construction pattern: `async with MemoryClient(MEMU_SERVICE_URL, project_id, AgentType.L3_CODE) as client:`
- No blockers

## Self-Check: PASSED

- orchestration/memory_client.py: FOUND
- tests/test_memory_client.py: FOUND
- tests/pytest.ini: FOUND
- 27-01-SUMMARY.md: FOUND
- Commit ed5b1bd (Task 1): FOUND
- Commit 5412aae (Task 2): FOUND

---
*Phase: 27-memory-client-scoping*
*Completed: 2026-02-24*
