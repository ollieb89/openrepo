---
phase: 49-deferred-reliability-quality-and-observability
plan: 03
subsystem: infra
tags: [monitor, docker, polling, adaptive, observability, cli]

# Dependency graph
requires:
  - phase: 49-deferred-reliability-quality-and-observability
    provides: POLL_INTERVAL constants from 49-01 (Plan 01 test scaffold), config.py patterns
  - phase: 45-path-resolver-and-constants-foundation
    provides: OPENCLAW_ROOT plumbing and config constants patterns
provides:
  - POLL_INTERVAL_ACTIVE = 2.0 and POLL_INTERVAL_IDLE = 30.0 constants in config.py
  - _count_active_l3_containers() in monitor.py with fail-open Docker query
  - Adaptive sleep in tail_state() while loop (2s active, 30s idle)
affects:
  - Any future monitor.py changes that touch the tail_state() while loop

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fail-open pattern: Docker query returns 0 (idle) on any exception, monitor never crashes"
    - "Adaptive interval pattern: Docker container count as activity signal for poll frequency"
    - "Module-level docker import allows monkeypatching in tests (monkeypatch.setattr)"

key-files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/src/openclaw/cli/monitor.py

key-decisions:
  - "Adaptive polling constants hardcoded (2s/30s) — not configurable in openclaw.json per locked decision"
  - "Up to 30s transition lag when idle→active is acceptable — container count checked per cycle"
  - "Docker query fails open to 0 (idle) so monitor continues running even when Docker daemon unavailable"
  - "POLL_INTERVAL = 1.0 kept intact for legacy --interval CLI arg default and _tail_single_file()"

patterns-established:
  - "Adaptive poll: _count_active_l3_containers() per cycle; sleep POLL_INTERVAL_ACTIVE if >0 else POLL_INTERVAL_IDLE"

requirements-completed: [OBS-05]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 49 Plan 03: Deferred Reliability, Quality, and Observability — OBS-05 Adaptive Polling Summary

**Adaptive monitor polling using Docker container count as activity signal — 2s when L3 containers running, 30s when idle — replacing the fixed 1s poll interval**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T08:12:03Z
- **Completed:** 2026-02-25T08:13:25Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added POLL_INTERVAL_ACTIVE = 2.0 and POLL_INTERVAL_IDLE = 30.0 constants to config.py alongside the preserved POLL_INTERVAL = 1.0 legacy constant
- Implemented _count_active_l3_containers() in monitor.py — queries Docker for openclaw.managed=true running containers with fail-open semantics (returns 0 on any exception)
- Replaced fixed time.sleep(interval) in tail_state() while loop with adaptive logic: 2s when active containers exist, 30s when swarm is idle

## Task Commits

Each task was committed atomically:

1. **Task 1: Add POLL_INTERVAL_ACTIVE and POLL_INTERVAL_IDLE to config.py** - `a7f3acf` (feat)
2. **Task 2: Implement _count_active_l3_containers() + adaptive sleep in monitor.py** - `535ac54` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `packages/orchestration/src/openclaw/config.py` - POLL_INTERVAL_ACTIVE = 2.0 and POLL_INTERVAL_IDLE = 30.0 added; POLL_INTERVAL = 1.0 unchanged
- `packages/orchestration/src/openclaw/cli/monitor.py` - import docker added; POLL_INTERVAL_ACTIVE/IDLE imported; _count_active_l3_containers() function added before _discover_projects(); adaptive sleep replaces time.sleep(interval) in tail_state() while loop

## Decisions Made
- Adaptive polling constants (2s active, 30s idle) are hardcoded — not in openclaw.json — per locked decision from research phase
- Up to 30s transition lag on idle→active is explicitly accepted; Docker query runs per cycle
- Docker failure returns 0 (idle) and logs a warning — monitor never crashes due to Docker unavailability
- POLL_INTERVAL = 1.0 preserved unchanged for backward compat (--interval CLI default, _tail_single_file())

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The file had been partially modified by Plan 02 execution (MEMORY_CONFLICT_THRESHOLD and updated memory schema were already present) — this was expected context from Wave 2 dependency.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- OBS-05 fully complete — 3/3 adaptive poll tests pass
- All 8 phase 49 tests pass (REL-09 + QUAL-07 + OBS-05)
- 268 total tests passing — 0 regressions
- Phase 49 is now complete: all 3 plans done, all deferred requirements (REL-09, QUAL-07, OBS-05) shipped
- v1.5 Config Consolidation milestone is complete

## Self-Check: PASSED

- FOUND: packages/orchestration/src/openclaw/config.py (contains POLL_INTERVAL_ACTIVE)
- FOUND: packages/orchestration/src/openclaw/cli/monitor.py (contains _count_active_l3_containers)
- FOUND commit a7f3acf: feat(49-03): add POLL_INTERVAL_ACTIVE and POLL_INTERVAL_IDLE to config.py
- FOUND commit 535ac54: feat(49-03): implement _count_active_l3_containers() + adaptive sleep (OBS-05)
- FOUND: .planning/phases/49-deferred-reliability-quality-and-observability/49-03-SUMMARY.md

---
*Phase: 49-deferred-reliability-quality-and-observability*
*Completed: 2026-02-25*
