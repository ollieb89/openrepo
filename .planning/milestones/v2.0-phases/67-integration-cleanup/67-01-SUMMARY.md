---
phase: 67-integration-cleanup
plan: 01
subsystem: api
tags: [python, topology, routing, imports, public-api]

requires:
  - phase: 62-topology-foundation
    provides: RubricScorer, score_proposal, renderer functions that were missing from public exports
  - phase: 63-correction-engine
    provides: render_diff_summary added to renderer.py

provides:
  - topology package public API now exports score_proposal and render_diff_summary
  - route_directive package now exports RouteType enum and RouteDecision dataclass
  - DirectiveRouter updated to accept (config, swarm_query=None) and return RouteDecision synchronously
  - agents/ directory made into proper Python package namespace for import

affects: [any consumer of openclaw.topology, any consumer of agents.main.skills.route_directive]

tech-stack:
  added: []
  patterns:
    - "Public API re-export pattern: submodule symbols promoted to package __all__"
    - "Dataclass routing result pattern: route() returns typed RouteDecision not raw dict"
    - "Namespace __init__.py pattern: empty __init__.py files for agents/ package hierarchy"

key-files:
  created:
    - packages/orchestration/tests/test_topology_public_api.py
    - packages/orchestration/tests/test_route_directive_importable.py
    - agents/__init__.py
    - agents/main/__init__.py
    - agents/main/skills/__init__.py
  modified:
    - packages/orchestration/src/openclaw/topology/__init__.py
    - agents/main/skills/route_directive/router.py

key-decisions:
  - "route() changed from async to sync — __main__.py calls it synchronously; removing async eliminates coroutine leaks"
  - "GatewayClient dependency removed from DirectiveRouter.__init__ — routing decisions don't require network dispatch"
  - "agents/ namespace __init__.py files created — required for Python package imports in test context"
  - "parents[3] is repo root from test path — test path is 4 levels deep (tests/ -> orchestration/ -> packages/ -> repo root)"

patterns-established:
  - "TDD RED/GREEN: write failing imports tests before fixing the code"
  - "Pre-existing test failures documented but not fixed (out of scope per deviation rules)"

requirements-completed: [PROP-02, PROP-03, CORR-02, CORR-07]

duration: 4min
completed: 2026-03-04
---

# Phase 67 Plan 01: Integration Cleanup Summary

**Exposed score_proposal and render_diff_summary on the topology package public API, and added RouteType enum + RouteDecision dataclass to route_directive so all documented imports work without submodule paths**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-04T15:56:55Z
- **Completed:** 2026-03-04T16:01:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- `from openclaw.topology import score_proposal, render_diff_summary` now works (INT-01 fixed)
- `from agents.main.skills.route_directive import DirectiveRouter, RouteDecision, RouteType` now works (INT-02 fixed)
- `DirectiveRouter({}, swarm_query=None).route("directive")` returns a typed `RouteDecision` synchronously
- 11 new tests added and passing (4 topology API tests, 7 route_directive tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for both integration gaps** - `191a127` (test) — RED phase
2. **Task 2: Fix topology __all__ exports and route_directive router** - `b04628f` (feat) — GREEN phase

**Plan metadata:** (see final commit below)

_Note: TDD tasks have two commits — test (RED) then feat (GREEN)_

## Files Created/Modified

- `packages/orchestration/src/openclaw/topology/__init__.py` - Added score_proposal and render_diff_summary to imports and __all__
- `agents/main/skills/route_directive/router.py` - Added RouteType, RouteDecision, updated DirectiveRouter constructor and route() to be sync
- `agents/__init__.py` - New: namespace package marker for Python imports
- `agents/main/__init__.py` - New: namespace package marker for Python imports
- `agents/main/skills/__init__.py` - New: namespace package marker for Python imports
- `packages/orchestration/tests/test_topology_public_api.py` - New: 4 import verification tests for INT-01
- `packages/orchestration/tests/test_route_directive_importable.py` - New: 7 import/behavior tests for INT-02

## Decisions Made

- `route()` changed from async to sync — the `__main__.py` caller expects synchronous behavior; async was incorrect
- `GatewayClient` dependency removed from `DirectiveRouter.__init__` — routing decisions are pure logic, no network needed
- `agents/` namespace `__init__.py` files created as part of INT-02 fix — required for Python to treat `agents.main.skills` as a package
- Path parent index corrected from `parents[4]` to `parents[3]` — repo root is 4 directories up from the test file

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added agents/ namespace __init__.py files**
- **Found during:** Task 2 (fixing route_directive router)
- **Issue:** `agents/`, `agents/main/`, `agents/main/skills/` directories lacked `__init__.py` files, making `import agents.main.skills.route_directive` fail with ModuleNotFoundError
- **Fix:** Created empty `__init__.py` files in all three directories
- **Files modified:** agents/__init__.py, agents/main/__init__.py, agents/main/skills/__init__.py
- **Verification:** `uv run pytest test_route_directive_importable.py` — all 7 tests pass
- **Committed in:** b04628f (Task 2 commit)

**2. [Rule 1 - Bug] Fixed path parent index in test file**
- **Found during:** Task 2 (verifying GREEN phase)
- **Issue:** Test file used `parents[4]` for repo root but the actual depth is `parents[3]`
- **Fix:** Changed `parents[4]` to `parents[3]` in two sys.path.insert() calls in test_route_directive_importable.py
- **Files modified:** packages/orchestration/tests/test_route_directive_importable.py
- **Verification:** Import path resolves to `~/Development/Tools/openrepo` (confirmed)
- **Committed in:** b04628f (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both auto-fixes essential to make the INT-02 import tests pass. No scope creep.

## Issues Encountered

- 4 pre-existing test failures exist in `test_proposer.py` and `test_state_engine_memory.py` — all confirmed pre-existing before this plan's changes (asyncio event loop ordering issue and JarvisState attribute error). Logged to deferred-items as out of scope.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All documented imports from the v2.0 milestone audit now work without ImportError
- Full test suite passes (489 tests) with 4 known pre-existing failures unrelated to this plan
- Phase 67 INT-01 and INT-02 gaps are closed

---
*Phase: 67-integration-cleanup*
*Completed: 2026-03-04*

## Self-Check: PASSED

- FOUND: test_topology_public_api.py
- FOUND: test_route_directive_importable.py
- FOUND: agents/__init__.py, agents/main/__init__.py, agents/main/skills/__init__.py
- FOUND: 67-01-SUMMARY.md
- FOUND commits: 191a127, b04628f
- INT-01 import verification: PASSED
- INT-02 import verification: PASSED
