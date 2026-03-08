---
phase: 71-l3-output-streaming
plan: 02
subsystem: dashboard
tags: [sse, event-bridge, heartbeat, log-viewer, typescript, reconnect]

# Dependency graph
requires:
  - phase: 71-01
    provides: TASK_OUTPUT EventType in Python, pool.py stream_logs() emission, UnixSocketTransport heartbeat
provides:
  - TASK_OUTPUT in TypeScript EventType enum with TaskOutputPayload interface
  - SSE /api/events endpoint with 30s heartbeat pings
  - SSE event IDs and ring buffer (100 events) for reconnection replay
  - LogViewer consuming /api/events with task_id filtering and auto-reconnect
affects:
  - 74-dashboard-streaming-ui

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSE heartbeat uses setInterval inside ReadableStream start() with clearInterval in close/abort handlers"
    - "Ring buffer as module-level array with addToRingBuffer() helper — shared across SSE connections"
    - "LogViewer auto-reconnect uses useRef for delay tracking to avoid stale closure issues"
    - "connectToEventSource() extracted as useCallback for safe reuse in initial + reconnect paths"
    - "Rolling buffer cap: setLogs(prev => [...prev, entry].slice(-MAX_LOG_ENTRIES))"

key-files:
  created: []
  modified:
    - packages/dashboard/src/lib/types/events.ts
    - packages/dashboard/src/app/api/events/route.ts
    - packages/dashboard/src/components/LogViewer.tsx

key-decisions:
  - "Ring buffer is module-level (shared across all SSE connections) — acceptable for replay purposes since events are not per-user sensitive"
  - "LogViewer uses isMountedRef to guard state updates after unmount — prevents React warnings on reconnect cleanup"
  - "containerId prop kept as deprecated backward-compat fallback with JSDoc @deprecated annotation"

# Metrics
duration: ~2min
completed: 2026-03-04
---

# Phase 71 Plan 02: SSE Heartbeat and LogViewer Event Bridge Summary

**Dashboard SSE endpoint extended with heartbeat keepalive and ring buffer replay; LogViewer rewired from deprecated swarm/stream to event bridge with auto-reconnect and stderr color-coding**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-04T21:35:07Z
- **Completed:** 2026-03-04T21:36:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `TASK_OUTPUT = 'task.output'` to TypeScript EventType enum — mirrors the Python EventType added in Plan 01
- Added `TaskOutputPayload` interface with `line: string` and `stream: 'stdout' | 'stderr'` fields
- Added 30-second `setInterval` heartbeat in SSE route sending `: ping\n\n` SSE comments
- Python-side heartbeat messages (type: "heartbeat") are forwarded as SSE comments rather than events
- Added incrementing event IDs to all SSE messages for reconnection support
- Added in-memory ring buffer (100 events) for reconnection replay via `Last-Event-ID` header
- Rewrote LogViewer to connect to `/api/events` instead of deprecated `/api/swarm/stream`
- LogViewer filters events by `type === TASK_OUTPUT` and `task_id` match
- Color-codes stderr lines red (`text-red-400`) vs stdout (`text-gray-100`)
- Exponential backoff auto-reconnect (1s base, 2x multiplier, 30s cap)
- Rolling 1000-line client-side buffer prevents memory bloat
- TypeScript compiles cleanly (zero errors)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SSE heartbeat and TypeScript TASK_OUTPUT type** - `06a2e23` (feat)
2. **Task 2: Switch LogViewer to event bridge with auto-reconnect** - `c4ca4ba` (feat)

## Files Created/Modified

- `packages/dashboard/src/lib/types/events.ts` — Added TASK_OUTPUT enum value and TaskOutputPayload interface
- `packages/dashboard/src/app/api/events/route.ts` — Added heartbeat interval, event IDs, ring buffer, reconnection replay, heartbeat message filtering
- `packages/dashboard/src/components/LogViewer.tsx` — Rewired to /api/events, added task_id filtering, auto-reconnect with backoff, stderr coloring, 1000-line rolling buffer

## Decisions Made

- Ring buffer is module-level (shared across all SSE connections) — acceptable since events are not user-sensitive; simplest approach for this phase
- `isMountedRef` guard prevents React state updates after component unmount during reconnect delay
- `containerId` prop retained as deprecated backward-compat fallback to avoid breaking existing usages
- Python-side heartbeat messages filtered to SSE comments rather than events — keeps event stream clean

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Dashboard SSE plumbing is complete end-to-end
- TypeScript TASK_OUTPUT type mirrors Python EventType.TASK_OUTPUT
- LogViewer is wired to the event bridge and ready for Phase 74 terminal panel UI
- Auto-reconnect and heartbeat ensure the connection stays live in production

## Self-Check: PASSED

All files present and commits verified.

---
*Phase: 71-l3-output-streaming*
*Completed: 2026-03-04*
