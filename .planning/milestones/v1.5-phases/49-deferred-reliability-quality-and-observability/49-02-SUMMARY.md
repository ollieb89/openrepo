---
phase: 49-deferred-reliability-quality-and-observability
plan: 02
subsystem: infra
tags: [memory, cosine-similarity, conflict-detection, configuration, schema, docker]

# Dependency graph
requires:
  - phase: 45-path-resolver-and-constants-foundation
    provides: OPENCLAW_ROOT plumbing, config.py constants patterns, get_project_root()
  - phase: 49-01
    provides: 8-test RED scaffold for QUAL-07 in test_phase49.py
provides:
  - MEMORY_CONFLICT_THRESHOLD = 0.85 constant with rationale comment in config.py (QUAL-07)
  - conflict_threshold documented in OPENCLAW_JSON_SCHEMA memory.properties
  - get_conflict_threshold() in project_config.py (openclaw.json → config.py fallback)
  - _get_conflict_threshold() + conflict pre-check in memorize router (fail-open, log + skip)
affects:
  - 49-03-PLAN (OBS-05 — adaptive polling, Wave 2 final plan)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Conflict threshold resolution: openclaw.json memory.conflict_threshold → config.MEMORY_CONFLICT_THRESHOLD fallback"
    - "Memorize router fail-open: if retrieve() fails, proceed with memorize (correctness > missed conflicts)"
    - "Docker container reads openclaw.json directly via OPENCLAW_ROOT env var — cannot import orchestration package"

key-files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/src/openclaw/project_config.py
    - docker/memory/memory_service/routers/memorize.py

key-decisions:
  - "MEMORY_CONFLICT_THRESHOLD = 0.85 (not 0.92 placeholder): sits at related→duplicate boundary per text-embedding-3-small benchmarks; conservative to prefer false negatives over false positives"
  - "Fail-open on conflict check error: if service.retrieve() raises, proceed with memorize — missed conflicts recoverable, failed writes are not"
  - "memorize.py reads openclaw.json directly via OPENCLAW_ROOT (cannot import openclaw package from Docker memory container)"
  - "get_memu_config() extended to pass through conflict_threshold — get_conflict_threshold() delegates to it for config read"

patterns-established:
  - "Config constant with rationale: MEMORY_CONFLICT_THRESHOLD includes multi-line comment explaining value choice and tuning guidance"
  - "Two-layer threshold resolution: JSON config override → Python constant fallback, with Never-raises guarantee"

requirements-completed: [QUAL-07]

# Metrics
duration: 2min
completed: 2026-02-25
---

# Phase 49 Plan 02: Deferred Reliability, Quality, and Observability — QUAL-07 Summary

**Calibrated cosine similarity conflict threshold (0.85) wired from config.py through project_config.py into the memorize router pre-write check**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T08:11:57Z
- **Completed:** 2026-02-25T08:13:35Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added MEMORY_CONFLICT_THRESHOLD = 0.85 to config.py with detailed rationale explaining the evidence-based default and tuning guidance (replaces placeholder 0.92)
- Expanded openclaw.json schema memory property from bare `{"type": "object"}` to typed properties dict documenting memu_api_url, enabled, and conflict_threshold
- Added get_conflict_threshold() to project_config.py with two-layer resolution: openclaw.json override → config.py fallback, never-raises guarantee
- Wired conflict pre-check into memorize router _run_memorize: retrieves top-5 existing memories, compares scores, logs warning and skips write if any score >= threshold (fail-open on retrieve error)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add MEMORY_CONFLICT_THRESHOLD to config.py + schema** - `e47c428` (feat)
2. **Task 2: Add get_conflict_threshold() to project_config.py + wire memorize router** - `4f0ba78` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `packages/orchestration/src/openclaw/config.py` - MEMORY_CONFLICT_THRESHOLD = 0.85 with rationale; memory schema properties expanded
- `packages/orchestration/src/openclaw/project_config.py` - get_conflict_threshold() function added; get_memu_config() extended with conflict_threshold passthrough
- `docker/memory/memory_service/routers/memorize.py` - _get_conflict_threshold() helper + pre-write conflict check in _run_memorize

## Decisions Made
- **0.85 threshold (not 0.92):** text-embedding-3-small benchmarks show 0.85 sits at the related→duplicate boundary; conservative default prefers false negatives (missing conflict) over false positives (dropping distinct memories)
- **Fail-open on retrieve error:** if conflict check's retrieve() call fails, proceed with memorize — missed conflicts are recoverable via health scan, failed writes are not
- **Direct JSON read in memorize router:** Docker memory container cannot import openclaw orchestration package, so reads openclaw.json via OPENCLAW_ROOT env var directly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Note: OBS-05 tests (test_adaptive_poll_*) were already passing before this plan executed — the adaptive polling implementation was already in place in monitor.py from a prior session. The plan's success criteria (268 tests pass, no regressions) was met cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- QUAL-07 fully complete — 3/3 tests passing
- Plan 03 (OBS-05 — adaptive polling) is the final plan for Phase 49; OBS-05 tests already pass so Plan 03 may be a lightweight verification/documentation task
- All 8 test_phase49.py tests green: REL-09 (2), QUAL-07 (3), OBS-05 (3)

## Self-Check: PASSED

- FOUND: packages/orchestration/src/openclaw/config.py (contains MEMORY_CONFLICT_THRESHOLD)
- FOUND: packages/orchestration/src/openclaw/project_config.py (contains get_conflict_threshold)
- FOUND: docker/memory/memory_service/routers/memorize.py (contains conflict_threshold)
- FOUND commit e47c428: feat(49-02): add MEMORY_CONFLICT_THRESHOLD constant and schema expansion
- FOUND commit 4f0ba78: feat(49-02): add get_conflict_threshold() and memorize conflict pre-check (QUAL-07)
- 268 tests passing, 0 failures

---
*Phase: 49-deferred-reliability-quality-and-observability*
*Completed: 2026-02-25*
