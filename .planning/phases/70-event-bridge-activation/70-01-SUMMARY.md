---
phase: 70-event-bridge-activation
plan: 01
subsystem: events
tags: [unix-socket, event-bus, asyncio, sse, bridge, orchestration]

# Dependency graph
requires:
  - phase: 68-tech-debt-resolution
    provides: Cleaned-up event infrastructure (event_bus, transport, protocol) ready for activation
provides:
  - events/bridge.py with ensure_event_bridge(), _envelope_to_event(), _bridge_handler()
  - Unix socket transport with OPENCLAW_ROOT-derived path (no hardcoded /tmp/)
  - Single event publish path: event_bus.emit() -> bridge handler -> Unix socket -> SSE clients
  - Stale socket detection and atexit cleanup
  - Dashboard SSE route using dynamic socket path
  - 13 new tests for bridge wiring, auto-start, idempotency, and socket path derivation
affects:
  - dashboard
  - monitor-cli
  - state-engine
  - autonomy-hooks
  - any phase adding new event publishers

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single event publish path: event_bus.emit() is the only public API for event publishing"
    - "Bridge handler pattern: daemon thread + asyncio loop wires sync event_bus to async transport"
    - "Idempotent bridge start: ensure_event_bridge() safe to call multiple times"
    - "Socket path from env: OPENCLAW_EVENTS_SOCK > OPENCLAW_ROOT/run/events.sock > ~/.openclaw/run/events.sock"

key-files:
  created:
    - packages/orchestration/src/openclaw/events/bridge.py
    - packages/orchestration/tests/test_event_bridge.py
  modified:
    - packages/orchestration/src/openclaw/events/transport.py
    - packages/orchestration/src/openclaw/events/__init__.py
    - packages/orchestration/src/openclaw/state_engine.py
    - packages/orchestration/src/openclaw/autonomy/hooks.py
    - packages/orchestration/src/openclaw/cli/monitor.py
    - packages/dashboard/src/app/api/events/route.ts
    - packages/orchestration/tests/test_state_engine_memory.py

key-decisions:
  - "AutonomyEventBus.emit() already calls event_bus.emit() — no second direct emission needed in hooks.py (removing duplicate prevented double-fire regression)"
  - "Bridge handler is fire-and-forget: failures log warning but never raise, orchestration never blocked by event errors"
  - "get_socket_path() uses lazy import of get_project_root() to avoid circular deps at module level"
  - "autonomy events from AutonomyEventBus will have project_id='unknown' in bridge — acceptable for current phase, project_id can be threaded through later"

patterns-established:
  - "Event publishers: event_bus.emit({event_type: EventType.X.value, project_id: ..., task_id: ..., ...extra}) is the canonical pattern"
  - "ensure_event_bridge() is idempotent — call it at long-running CLI startup, not on every event"
  - "Transport stale-socket detection: try asyncio.open_unix_connection with 0.5s timeout before removing"

requirements-completed: [EVNT-01, EVNT-02]

# Metrics
duration: 9min
completed: 2026-03-04
---

# Phase 70 Plan 01: Event Bridge Activation Summary

**Unix socket event bridge activated — event_bus.emit() now forwards events through daemon-thread asyncio loop to connected SSE clients, with OPENCLAW_ROOT-derived socket path and graceful degradation**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-04T20:41:30Z
- **Completed:** 2026-03-04T20:50:26Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Created `events/bridge.py` with `ensure_event_bridge()` (idempotent auto-start), `_envelope_to_event()` (dict-to-OrchestratorEvent mapping), and `_bridge_handler()` (fire-and-forget forwarding to Unix socket)
- Migrated all direct `event_bridge.publish()` calls to `event_bus.emit()` in `state_engine.py` — eliminating the async loop conflict pattern (get_running_loop/except RuntimeError)
- Fixed hardcoded `/tmp/openclaw-events.sock` in `transport.py` and `dashboard/route.ts` — now derived from `OPENCLAW_ROOT/run/events.sock` with `OPENCLAW_EVENTS_SOCK` env override
- Added 13 passing tests covering envelope mapping, idempotency, end-to-end wiring, and socket path derivation; full suite 707 tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create bridge module and fix socket path** - `30ebe97` (feat)
2. **Task 2: Migrate publishers and update consumers** - `9245ac0` (feat)
3. **Task 3: Test bridge wiring and graceful degradation** - `e434e3d` (test)

## Files Created/Modified

- `packages/orchestration/src/openclaw/events/bridge.py` — New: bridge handler, ensure_event_bridge(), _envelope_to_event()
- `packages/orchestration/src/openclaw/events/transport.py` — Fixed: get_socket_path() function, stale-socket detection, atexit cleanup, parent dir creation
- `packages/orchestration/src/openclaw/events/__init__.py` — Added: ensure_event_bridge export
- `packages/orchestration/src/openclaw/state_engine.py` — Migrated: event_bridge.publish() -> event_bus.emit() in update_task() and create_task()
- `packages/orchestration/src/openclaw/autonomy/hooks.py` — Cleaned: removed duplicate direct event_bus.emit() (AutonomyEventBus already handles it)
- `packages/orchestration/src/openclaw/cli/monitor.py` — Updated: tail_events uses ensure_event_bridge() + asyncio.open_unix_connection() as client
- `packages/dashboard/src/app/api/events/route.ts` — Fixed: socket path from OPENCLAW_ROOT/OPENCLAW_EVENTS_SOCK env vars
- `packages/orchestration/tests/test_event_bridge.py` — New: 13 tests for bridge behavior
- `packages/orchestration/tests/test_state_engine_memory.py` — Fixed: patch event_bus.emit instead of removed event_bridge

## Decisions Made

- **AutonomyEventBus is already cross-runtime**: `AutonomyEventBus.emit()` calls `event_bus.emit()` internally, so hooks.py did not need a second direct emission — the duplicate caused a double-fire regression that was auto-fixed.
- **Bridge failure = warning, not crash**: if `ensure_event_bridge()` fails (socket bind error, etc.), orchestration continues with a warning log. Events are silently dropped, not surfaced to callers.
- **autonomy.state_changed events have no project_id**: `AutonomyEventBus` envelope does not include `project_id`, so bridge maps it to `"unknown"`. Acceptable for now — can be fixed by threading project_id into AutonomyEventBus in a future phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed duplicate event_bus.emit() in autonomy/hooks.py**
- **Found during:** Task 3 (full test suite run)
- **Issue:** `on_task_spawn()` emitted `autonomy.state_changed` twice — once via `AutonomyEventBus.emit()` (which already calls `event_bus.emit()`) and once via our new direct `event_bus.emit()`. This caused `test_state_changed_event_emitted` to fail with `assert 2 == 1`.
- **Fix:** Removed the redundant direct `event_bus.emit()` block from `hooks.py` and removed the now-unused `EventType` and `event_bus` imports. Added clarifying comment.
- **Files modified:** `packages/orchestration/src/openclaw/autonomy/hooks.py`
- **Verification:** All 707 tests pass; `autonomy.state_changed` emitted exactly once per state transition.
- **Committed in:** `e434e3d` (Task 3 commit)

**2. [Rule 1 - Bug] Updated test_state_engine_memory.py to patch event_bus.emit instead of removed event_bridge**
- **Found during:** Task 3 (full test suite run)
- **Issue:** `test_state_transition_triggers_memory` patched `openclaw.state_engine.event_bridge` which no longer exists after migration, causing `AttributeError`.
- **Fix:** Replaced `@patch("openclaw.state_engine.event_bridge")` with `@patch("openclaw.event_bus.emit")`, removed async mocking (no longer needed since event_bus.emit is synchronous).
- **Files modified:** `packages/orchestration/tests/test_state_engine_memory.py`
- **Verification:** Test passes, memory trigger assertions still hold.
- **Committed in:** `e434e3d` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs surfaced by regression tests)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the two regressions documented above, both of which were caught by the test suite and auto-fixed.

## Next Phase Readiness

- Event bridge is active and wired — `event_bus.emit()` is the single publish path
- Dashboard SSE endpoint (`/api/events`) ready to stream events when bridge server is running
- `ensure_event_bridge()` can be called from `openclaw-monitor tail --events` and any long-running orchestration command
- Remaining gap: `AutonomyEventBus` envelopes lack `project_id` — bridge uses `"unknown"` for autonomy events
- Environment page (`/app/environment/page.tsx`) still shows old hardcoded socket path — cosmetic issue, deferred

## Self-Check: PASSED

All files and commits verified present:
- bridge.py: FOUND
- test_event_bridge.py: FOUND
- SUMMARY.md: FOUND
- Commit 30ebe97 (Task 1): FOUND
- Commit 9245ac0 (Task 2): FOUND
- Commit e434e3d (Task 3): FOUND

---
*Phase: 70-event-bridge-activation*
*Completed: 2026-03-04*
