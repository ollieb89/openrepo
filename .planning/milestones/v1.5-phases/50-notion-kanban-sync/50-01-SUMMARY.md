---
phase: 50-notion-kanban-sync
plan: 01
subsystem: infra
tags: [event-bus, threading, pub-sub, notion, orchestration]

requires: []
provides:
  - event_bus.py module with emit/subscribe/clear_handlers (fire-and-forget, daemon threads)
  - Phase lifecycle events from state_engine (phase_started, phase_completed, phase_blocked)
  - Container lifecycle events from pool (container_completed, container_failed)
  - Project events from project_cli (project_registered, project_removed)
  - NOTION-01 through NOTION-11 requirements defined in REQUIREMENTS.md
affects:
  - 50-02-PLAN (skill skeleton uses event_bus.subscribe)
  - 50-03-PLAN (Notion client registered as subscriber)
  - All future Notion sync plans

tech-stack:
  added: []
  patterns:
    - "Lazy import pattern: from .event_bus import emit inside function body to avoid circular imports"
    - "Fire-and-forget threading: threading.Thread(daemon=True) per handler invocation"
    - "Event envelope shape: {event_type, occurred_at, project_id, phase_id, container_id, payload}"
    - "Non-blocking try/except on all hook sites — orchestration never fails due to event emission"

key-files:
  created:
    - packages/orchestration/src/openclaw/event_bus.py
  modified:
    - packages/orchestration/src/openclaw/state_engine.py
    - skills/spawn/pool.py
    - packages/orchestration/src/openclaw/cli/project.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "event_bus.py has zero openclaw imports at module level — only stdlib (threading, logging, collections, typing)"
  - "Each handler gets its own daemon thread per emit() call — no shared handler thread pool"
  - "Hook in state_engine placed inside lock context after _write_state_locked(), before break statement"
  - "Hook in pool placed after completed/failed branch resolution, before lock_wait_ms metric set"
  - "project_cli hooks placed at end of success paths — emit() fires only when CLI operation fully succeeded"

patterns-established:
  - "Event hook pattern: lazy import + try/except with no re-raise + daemon thread dispatch"
  - "Envelope shape: all 6 fields present on every event (None for inapplicable fields)"

requirements-completed:
  - NOTION-01

duration: 12min
completed: 2026-02-25
---

# Phase 50 Plan 01: Event Bus Infrastructure Summary

**Thread-safe pub/sub event bus (emit/subscribe/clear_handlers) wired into state_engine, pool, and project_cli as fire-and-forget hooks emitting canonical event envelopes**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-25T06:34:44Z
- **Completed:** 2026-02-25T06:46:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created `event_bus.py` with stdlib-only imports, daemon-thread dispatch, and exception isolation
- Wired 5 hook sites across 3 orchestration modules with lazy import pattern
- Verified 158 existing tests pass — hooks are transparent no-ops when no handlers registered
- Added NOTION-01 through NOTION-11 requirements to REQUIREMENTS.md with Phase 50 traceability

## Task Commits

Each task was committed atomically:

1. **Task 1: Create event_bus.py + update REQUIREMENTS.md** - `899f33a` (feat)
2. **Task 2: Wire event hooks into state_engine, pool, project_cli** - `738ff34` (feat)

## Files Created/Modified
- `packages/orchestration/src/openclaw/event_bus.py` — Event bus: emit/subscribe/clear_handlers with daemon thread dispatch
- `packages/orchestration/src/openclaw/state_engine.py` — Hook in update_task(): emits phase_started/phase_completed/phase_blocked
- `skills/spawn/pool.py` — Hook in _attempt_task(): emits container_completed/container_failed
- `packages/orchestration/src/openclaw/cli/project.py` — Hooks in cmd_init()/cmd_remove(): emit project_registered/project_removed
- `.planning/REQUIREMENTS.md` — NOTION-01..11 added under v2.0 section, traceability table updated

## Decisions Made
- Zero openclaw imports at module level in event_bus.py — avoids circular import (state_engine imports from openclaw, so event_bus must not import from openclaw at module load time)
- Each handler spawns its own daemon thread — simple and robust; no thread pool needed at this scale
- Hook placement in state_engine is inside the lock context (after write, before break) — ensures event fires only on successful write
- Hook placement in pool is after the completed/failed status branches and before the lock_wait_ms metric — covers both terminal states cleanly
- project_cli hooks placed at end of each success path, after all side effects complete

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Event bus is live: any subscriber registered via `subscribe()` will receive events as orchestration runs
- Hook sites emit canonical envelopes matching the SPEC.md schema exactly
- Ready for Phase 50 Plan 02: skill skeleton + Notion client wrapper that subscribes to these events

---
*Phase: 50-notion-kanban-sync*
*Completed: 2026-02-25*
