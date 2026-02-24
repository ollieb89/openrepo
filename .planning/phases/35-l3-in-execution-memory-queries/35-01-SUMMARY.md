---
phase: 35-l3-in-execution-memory-queries
plan: "01"
subsystem: memory
tags: [memu, curl, jq, L3, SOUL, http-mock, integration-tests, RET-05]

requires:
  - phase: 33-l3-soul-injection
    provides: MEMU_API_URL, OPENCLAW_PROJECT, SKILL_HINT env vars injected at spawn; openclaw-memory DNS rewrite
  - phase: 29-spawn-memory-retrieval
    provides: POST /retrieve endpoint shape; memory_client.py graceful degradation pattern
  - phase: 26-memory-service-foundation
    provides: memU FastAPI service with /retrieve endpoint

provides:
  - "## Memory Queries section in agents/l3_specialist/agent/SOUL.md with copy-pasteable curl example"
  - "5 integration tests in tests/test_l3_memory_query.py covering success, empty, unreachable, dict shape, and env var paths"
  - "RET-05 closed: L3 containers have documented + tested capability for mid-execution memU queries"

affects:
  - "future L3 SOUL updates — Memory Queries section is now part of the base template"
  - "future memory phases — test patterns with MockMemuHandler establish mock HTTP server conventions"

tech-stack:
  added: []
  patterns:
    - "MockMemuHandler: stdlib http.server.BaseHTTPRequestHandler in daemon thread on OS-assigned port (bind 0) for mock HTTP endpoints in tests"
    - "printf-based JSON construction in bash avoids single-quote escaping issues when building curl payloads with env vars"
    - "jq dual-shape extraction: (if type == array then . else .items // [] end)[] handles both list and dict response shapes"

key-files:
  created:
    - "tests/test_l3_memory_query.py"
  modified:
    - "agents/l3_specialist/agent/SOUL.md"

key-decisions:
  - "printf used for JSON payload construction in bash test commands — avoids single-quote escaping issues when env vars need expansion inside JSON strings"
  - "Project-only scoping (no global fallback) via OPENCLAW_PROJECT → where.user_id, consistent with memory_client.py and spawn.py patterns"
  - "Advisory-only framing in SOUL: unreachable memU or empty results must not abort task execution — matches existing graceful degradation contract"

patterns-established:
  - "MockMemuHandler pattern: bind to port 0 for OS-assigned free port, daemon thread, store last_request_body, configurable mock_response, yield in fixture for guaranteed cleanup"

requirements-completed: [RET-05]

duration: 2min
completed: 2026-02-24
---

# Phase 35 Plan 01: L3 In-Execution Memory Queries Summary

**L3 SOUL template extended with a Memory Queries section (copy-pasteable curl + jq), backed by 5 mock-HTTP integration tests closing RET-05**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-24T13:06:10Z
- **Completed:** 2026-02-24T13:08:21Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `## Memory Queries` section to `agents/l3_specialist/agent/SOUL.md` after `## Security & Isolation`, with a copy-pasteable curl example that uses `${MEMU_API_URL}`, `--max-time 5`, project scoping via `${OPENCLAW_PROJECT}`, jq extraction handling both list and dict response shapes, and `|| echo "[]"` silent fallback
- Created `tests/test_l3_memory_query.py` with 5 integration tests using a stdlib mock HTTP server — covers successful retrieval, empty result continuation, unreachable server graceful degradation, dict `{items:[]}` response shape, and env var routing proof
- Full test suite passes: 63 tests (58 existing + 5 new), no regressions

## Task Commits

1. **Task 1: Add Memory Queries section to L3 SOUL template** - `a129bbb` (feat)
2. **Task 2: Write integration tests for L3 in-execution memory queries** - `9218740` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `agents/l3_specialist/agent/SOUL.md` - Added Memory Queries section at end (32 lines appended)
- `tests/test_l3_memory_query.py` - 5 integration tests with MockMemuHandler and curl subprocess validation (239 lines)

## Decisions Made
- `printf` used for JSON payload construction in bash test commands — single-quote escaping conflicts with bash variable expansion inside JSON strings. Using `printf '{"key": "%s"}' "$VAR"` correctly expands env vars into the JSON payload that curl sends
- Project-only scoping: `OPENCLAW_PROJECT` maps to `where.user_id` with no global fallback — consistent with `memory_client.py` and `spawn.py`, prevents cross-project contamination (REQUIREMENTS.md out-of-scope)
- Advisory-only framing: SOUL makes clear that memU being unreachable or returning empty must not stop task execution

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed variable expansion in bash curl command test helpers**
- **Found during:** Task 2 (integration tests)
- **Issue:** Initial `_build_curl_cmd` used single-quoted `-d` payload string, causing `${OPENCLAW_PROJECT}` to be sent literally rather than expanded. 2 of 5 tests failed with `where.user_id == '${OPENCLAW_PROJECT}'` instead of `'testproj'`
- **Fix:** Switched to `printf` for JSON construction: `PAYLOAD=$(printf '{"queries": [...], "where": {"user_id": "%s"}}' "$OPENCLAW_PROJECT")` — env var expands into printf argument, payload contains the actual project ID
- **Files modified:** `tests/test_l3_memory_query.py`
- **Verification:** All 5 tests pass after fix
- **Committed in:** `9218740` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — shell quoting bug in test helper)
**Impact on plan:** Required fix for test correctness. Bash single-quote vs double-quote semantics. No scope creep.

## Issues Encountered
- Bash quoting: single-quoted JSON `-d` payload does not expand `${VAR}` references. Resolved by using `printf` to build payload with expanded values. This is a common bash pitfall when constructing JSON for curl.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RET-05 (last retrieval requirement) is closed. v1.3 Agent Memory milestone is feature-complete.
- All retrieval requirements (RET-01 through RET-05) and memorization requirements (MEM-01 through MEM-05) are satisfied.
- 63 tests passing with 0.20s average runtime.

---
*Phase: 35-l3-in-execution-memory-queries*
*Completed: 2026-02-24*
