---
phase: 49-deferred-reliability-quality-and-observability
plan: 01
subsystem: infra
tags: [docker, healthcheck, sentinel, tdd, testing, reliability]

# Dependency graph
requires:
  - phase: 45-path-resolver-and-constants-foundation
    provides: OPENCLAW_ROOT plumbing and config constants patterns
provides:
  - 8-test RED scaffold for REL-09, QUAL-07, OBS-05 in test_phase49.py
  - Dockerfile HEALTHCHECK instruction with sentinel file approach (REL-09)
  - entrypoint.sh sentinel write after startup initialization (REL-09)
affects:
  - 49-02-PLAN (QUAL-07 implementation — constants and schema)
  - 49-03-PLAN (OBS-05 implementation — adaptive polling)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docker HEALTHCHECK uses shell form CMD test -f (not exec form) for cap_drop ALL safety"
    - "Sentinel file /tmp/openclaw-healthy written by entrypoint after startup — no capabilities or network needed"
    - "TDD RED scaffold: 8 tests written before implementation so Wave 2 plans have automated verification"

key-files:
  created:
    - packages/orchestration/tests/test_phase49.py
  modified:
    - docker/l3-specialist/Dockerfile
    - docker/l3-specialist/entrypoint.sh

key-decisions:
  - "HEALTHCHECK uses shell form (CMD test -f ...) not exec form — Debian bookworm-slim test is a bash builtin, not standalone binary"
  - "Sentinel written after update_state starting but before staging branch creation — represents container fully initialized and ready"
  - "8 failing tests committed in RED state before implementation — Wave 2 tasks implement against these tests"

patterns-established:
  - "Sentinel pattern: entrypoint writes /tmp/openclaw-healthy after initialization; Dockerfile checks it every 30s"
  - "Phase scaffold: test file created before implementation files so each Wave 2 plan starts with automated RED tests"

requirements-completed: [REL-09]

# Metrics
duration: 8min
completed: 2026-02-25
---

# Phase 49 Plan 01: Deferred Reliability, Quality, and Observability — Test Scaffold + REL-09 Summary

**Docker HEALTHCHECK via sentinel file (/tmp/openclaw-healthy) for L3 containers, plus 8-test RED scaffold for QUAL-07 and OBS-05**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-25T08:08:23Z
- **Completed:** 2026-02-25T08:16:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created test_phase49.py with 8 failing tests covering REL-09, QUAL-07, and OBS-05 — Wave 2 plans have automated verification targets before implementation starts
- Added HEALTHCHECK instruction to Dockerfile with --interval=30s --timeout=5s --retries=3 --start-period=30s using shell-form CMD test -f (safe with cap_drop ALL)
- Added sentinel touch /tmp/openclaw-healthy to entrypoint.sh after update_state "starting", making L3 container health visible in docker ps

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_phase49.py with 8 failing tests** - `b67a2aa` (test)
2. **Task 2: Docker HEALTHCHECK + entrypoint.sh sentinel (REL-09)** - `942e199` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `packages/orchestration/tests/test_phase49.py` - 8 failing tests for REL-09 (2), QUAL-07 (3), OBS-05 (3)
- `docker/l3-specialist/Dockerfile` - HEALTHCHECK instruction added before USER l3worker
- `docker/l3-specialist/entrypoint.sh` - sentinel touch after update_state "starting" call

## Decisions Made
- Shell form HEALTHCHECK (CMD test -f /tmp/openclaw-healthy || exit 1) not exec form — Debian bookworm-slim lacks /usr/bin/test as standalone binary; bash builtin works fine with shell form
- Sentinel placed after update_state "starting" but before staging branch creation — startup phase complete, git/state init done
- 8 tests created in RED state; QUAL-07 (3 tests) and OBS-05 (3 tests) remain failing pending Wave 2 implementation plans 02 and 03

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- test_phase49.py is the verification harness for Plans 02 and 03
- Plan 02: Implement MEMORY_CONFLICT_THRESHOLD constant in config.py, get_conflict_threshold() in project_config.py, expand memory schema in OPENCLAW_JSON_SCHEMA (QUAL-07)
- Plan 03: Implement _count_active_l3_containers() and POLL_INTERVAL_IDLE in monitor.py (OBS-05)
- REL-09 fully complete — no further work needed on Docker health check

## Self-Check: PASSED

- FOUND: packages/orchestration/tests/test_phase49.py
- FOUND: docker/l3-specialist/Dockerfile (contains HEALTHCHECK)
- FOUND: docker/l3-specialist/entrypoint.sh (contains touch /tmp/openclaw-healthy)
- FOUND: .planning/phases/49-deferred-reliability-quality-and-observability/49-01-SUMMARY.md
- FOUND commit b67a2aa: test(49-01): add 8 failing tests for REL-09, QUAL-07, OBS-05 (RED)
- FOUND commit 942e199: feat(49-01): Docker HEALTHCHECK + entrypoint sentinel (REL-09)

---
*Phase: 49-deferred-reliability-quality-and-observability*
*Completed: 2026-02-25*
