---
phase: 71-l3-output-streaming
plan: 01
subsystem: events
tags: [event-bus, unix-socket, streaming, heartbeat, docker, l3]

# Dependency graph
requires:
  - phase: 70-event-bridge-activation
    provides: event_bus.emit(), UnixSocketTransport, bridge handler, _envelope_to_event, ensure_event_bridge()
provides:
  - TASK_OUTPUT = "task.output" in EventType enum
  - pool.py stream_logs() emits task.output events per output line with task_id, project_id, stream fields
  - UnixSocketTransport heartbeat loop (30s interval, configurable for testing)
  - 4 new tests covering TASK_OUTPUT bridge mapping and heartbeat behavior
affects:
  - 74-dashboard-streaming-ui
  - Any consumer of the Unix socket event stream

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TASK_OUTPUT events are fire-and-forget — inner try/except prevents log streaming crash"
    - "Lazy import of event_bus.emit inside stream_logs() matching existing pool.py pattern"
    - "Heartbeat interval stored as instance attribute (_heartbeat_interval) enabling test override"
    - "Heartbeat loop uses asyncio.ensure_future() started from start_server()"

key-files:
  created:
    - packages/orchestration/tests/test_event_bridge.py (4 new tests added to existing file)
  modified:
    - packages/orchestration/src/openclaw/events/protocol.py
    - packages/orchestration/src/openclaw/events/transport.py
    - skills/spawn/pool.py

key-decisions:
  - "Used single-stream container.logs() with stream='stdout' label for all lines — simpler than demux, plan explicitly allowed this fallback"
  - "Heartbeat interval stored as _heartbeat_interval instance attr (default 30) — allows tests to set to 1s without monkey-patching asyncio.sleep"
  - "bridge.py required no code changes — _EVENT_TYPE_MAP and event subscriptions are already dynamic over all EventType values"

patterns-established:
  - "Event emission in infrastructure loops: wrap emit() in inner try/except so loop continues on failure"
  - "Transport heartbeat uses asyncio.ensure_future() not create_task() to support pre-3.10 Python"

requirements-completed: [EVNT-03]

# Metrics
duration: 15min
completed: 2026-03-04
---

# Phase 71 Plan 01: L3 Output Streaming Summary

**TASK_OUTPUT event type wired through event bus with pool.py stream_logs() emission and UnixSocketTransport 30-second heartbeat keepalive**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-04T21:10:02Z
- **Completed:** 2026-03-04
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added `TASK_OUTPUT = "task.output"` to EventType enum — bridge auto-discovers it via dynamic map
- Wired `stream_logs()` in pool.py to emit `task.output` events per output line with task_id, project_id, and stream fields
- Added `_heartbeat_loop()` to UnixSocketTransport sending heartbeat JSON every 30 seconds to all connected clients
- Heartbeat cleans up disconnected clients and is cancelled cleanly in `stop_server()`
- 4 new tests, 711 total (up from 707), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add TASK_OUTPUT event type and wire pool.py emission** - `59c102b` (feat)
2. **Task 2: Add socket heartbeat and write tests** - `b787bff` (feat)

**Plan metadata:** (docs commit — this summary)

## Files Created/Modified

- `packages/orchestration/src/openclaw/events/protocol.py` - Added TASK_OUTPUT = "task.output" to EventType enum
- `skills/spawn/pool.py` - stream_logs() now emits task.output events per line via lazy-imported event_bus.emit
- `packages/orchestration/src/openclaw/events/transport.py` - Added _heartbeat_task, _heartbeat_loop(), stop_server() cancellation, import time/Optional
- `packages/orchestration/tests/test_event_bridge.py` - Added TestTaskOutputEventMapping (2 tests) and TestHeartbeatSentToClients (2 tests)

## Decisions Made

- Used single-stream `container.logs()` with `stream="stdout"` for all lines rather than `demux=True` — plan explicitly allowed this simpler fallback; stderr distinction deferred to a future phase
- Stored heartbeat interval as `_heartbeat_interval` instance attribute (default 30) so tests can set it to 1 without monkey-patching asyncio.sleep
- `bridge.py` required zero code changes — `_EVENT_TYPE_MAP` is dynamically built from all EventType values, so TASK_OUTPUT is picked up automatically

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Python-side L3 output streaming plumbing is complete
- Phase 74 (Dashboard Streaming UI) can now consume TASK_OUTPUT events from the Unix socket
- The event bridge already routes TASK_OUTPUT events to connected clients via the existing _bridge_handler → publish() path

---
*Phase: 71-l3-output-streaming*
*Completed: 2026-03-04*
