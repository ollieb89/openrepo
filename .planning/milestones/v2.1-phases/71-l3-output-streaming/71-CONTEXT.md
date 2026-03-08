# Phase 71: L3 Output Streaming - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Stream L3 container stdout/stderr in real-time from pool.py through the event bridge to the dashboard SSE endpoint. Each output line is tagged with task ID for routing. SSE heartbeat pings keep the connection alive. No new dashboard UI components — Phase 74 handles the terminal panel.

</domain>

<decisions>
## Implementation Decisions

### Event design
- Add `TASK_OUTPUT` to `EventType` enum under the existing `TASK` domain — no new `EventDomain` needed
- Stdout and stderr are separate streams: each event carries `stream: "stdout" | "stderr"` in the payload for dashboard color-coding
- One event per line — no batching. Meets the 2-second latency success criteria with minimal complexity
- Payload shape: `{line: string, stream: "stdout" | "stderr"}` — minimal, task_id comes from the standard OrchestratorEvent envelope
- No sequence numbers — Unix socket transport preserves ordering within a connection

### Emission path
- Direct emit from pool.py's `stream_logs()` async loop — each decoded log line calls `event_bus.emit()` inline
- No intermediate adapter class — follows existing pool.py patterns (direct calls, no abstraction layers)
- No rate limiting or backpressure — fire-and-forget matches Phase 70 event bus philosophy. Dashboard handles its own scroll performance
- No terminal TASK_OUTPUT_END event — rely on existing TASK_COMPLETED/TASK_FAILED events to signal stream end. No new event type needed
- project_id comes from pool context (already available when container is spawned) — no Docker label inspection needed

### Dashboard consumption
- Event bridge only — remove or deprecate `/api/swarm/stream` direct Docker streaming path. All output flows through the event bridge, matching v2.1 programmatic integration vision
- Client-side filtering by task_id — dashboard receives all events on the single SSE stream, JavaScript filters by task_id per panel
- Rolling buffer: last 1000 lines per task in browser memory — prevents performance issues for chatty containers
- Leave UI component work for Phase 74 (Dashboard Streaming UI) — Phase 71 ensures output events reach the SSE stream, Phase 74 builds the terminal panel. Adapt LogViewer minimally if needed for verification

### SSE heartbeat
- Both layers: Python socket server sends periodic heartbeat events (keeps Unix socket alive), Next.js SSE bridge adds SSE-level heartbeats (keeps browser connection alive)
- Format: SSE comment (`: ping\n\n`) — standard keepalive convention. Browsers ignore comments but reset connection timeout. Invisible to event listeners
- Hardcoded 30-second interval — matches success criteria exactly, no configuration needed
- Missed heartbeat handling deferred to Phase 74 — Phase 71 ensures heartbeats are sent, reconnection/warning UI is dashboard streaming scope

### Claude's Discretion
- How to separate stdout vs stderr from Docker's multiplexed log stream (demux parameter vs raw stream parsing)
- Exact integration point in stream_logs() for the emit call (before or after the logger.debug)
- Whether to update the TypeScript event types mirror (events.ts) in this phase or defer to Phase 74
- Heartbeat implementation details (asyncio timer in Python, setInterval in Next.js)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Success criteria are fully prescriptive:
1. L3 stdout appears in dashboard SSE stream within 2 seconds of being written
2. Each output line tagged with task ID for dashboard routing
3. SSE endpoint sends heartbeat pings every 30 seconds visible in browser devtools

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pool.py:696-709` (`stream_logs()`): Already has async Docker log streaming with `container.logs(stream=True, follow=True)` — just needs emit calls added
- `events/protocol.py`: `OrchestratorEvent` dataclass with `task_id` field — output events fit naturally
- `event_bus.py`: Fire-and-forget daemon thread handlers — bridge handler from Phase 70 auto-forwards to socket
- `/api/events/route.ts`: SSE bridge already connects to Unix socket and streams events — output events will flow through automatically
- `LogViewer.tsx`: Existing component with EventSource, connection status, auto-scroll — adaptable for event bridge source

### Established Patterns
- `event_bus.emit()` is the single canonical publish path (Phase 70 decision)
- Events wrapped in try/except — never fail core operations (Phase 68/70 pattern)
- `OrchestratorEvent` envelope: type, domain, project_id, agent_id, task_id, payload, timestamp, correlation_id
- Dashboard SSE bridge reads socket path from `OPENCLAW_ROOT` convention (Phase 70)

### Integration Points
- `pool.py:stream_logs()` (line 696): Add event_bus.emit() call per decoded log line
- `events/protocol.py`: Add `TASK_OUTPUT = "task.output"` to EventType enum
- `dashboard/lib/types/events.ts`: Add TypeScript mirror of TASK_OUTPUT type
- `/api/events/route.ts`: Add heartbeat interval (`: ping` comments every 30s)
- `events/transport.py`: Add heartbeat timer to UnixSocketTransport server
- `LogViewer.tsx` or similar: Switch from `/api/swarm/stream` to `/api/events` with task_id filter (minimal, for verification)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 71-l3-output-streaming*
*Context gathered: 2026-03-04*
