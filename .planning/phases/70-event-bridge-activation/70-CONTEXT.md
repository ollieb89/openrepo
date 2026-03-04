# Phase 70: Event Bridge Activation - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Start the Unix socket server automatically during orchestration and wire the event bus to the socket transport so all published events flow to connected clients. No new event types, no dashboard UI changes — just activate the existing infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Server startup trigger
- Socket server starts on first orchestration import for long-running commands (monitor, gateway, agent runs) — not for short-lived CLI commands like `project list` or `monitor status`
- Runs in the same process as a daemon thread with its own asyncio event loop — dies when main process exits
- True singleton: before starting, check if socket exists and is connectable — if another process already runs the server, skip and just bridge events to it
- Uses atexit for cleanup (remove socket file on graceful exit)

### Bus-to-bridge wiring
- Auto-register a bridge handler on event_bus when the socket server starts — event_bus.emit() stays the single publish path
- Bridge handler auto-maps existing envelope dict keys (event_type, project_id, etc.) to OrchestratorEvent dataclass fields — zero changes to existing publishers
- Unify all publishers through event_bus.emit(): remove direct event_bridge.publish() calls from state_engine.py and autonomy/hooks.py — single event path for everything
- Failed forwards silently drop with a log warning — fire-and-forget semantics preserved, matches existing event_bus philosophy

### Socket path & scope
- Derive socket path from OPENCLAW_ROOT (e.g., $OPENCLAW_ROOT/run/events.sock) — follows Phase 68 portability precedent (DEBT-03)
- Single global socket shared by all projects — events include project_id for client-side filtering
- Discovery via shared constant + env override: default path from OPENCLAW_ROOT, OPENCLAW_EVENTS_SOCK env var for override, dashboard reads same convention

### Startup failure policy
- Warn and degrade gracefully — log a warning, disable event forwarding, orchestration continues without events
- Core functionality (spawning, state, memory) must never depend on event bridge availability
- Stale socket files auto-cleaned on startup: if socket exists but no process is listening, remove and start fresh
- Health indicator in `openclaw-monitor status` showing event bridge state (running/stopped/degraded)

### Claude's Discretion
- Exact mapping logic from event_bus envelope keys to OrchestratorEvent fields
- Thread/asyncio bridging implementation details (how sync handler pushes to async loop)
- Threshold for distinguishing "long-running" vs "short-lived" commands
- Stale socket detection mechanism (connect attempt with timeout vs PID file)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `event_bus.py`: Sync pub/sub with fire-and-forget daemon threads — the universal publish path all code already uses
- `events/transport.py`: `UnixSocketTransport` with full server/client/publish/subscribe — ready to activate
- `events/protocol.py`: 17 event types across 5 domains (Task, Agent, Autonomy, Memory, Pool) — complete protocol
- Dashboard `api/events/route.ts`: SSE bridge that connects to Unix socket — ready to consume events
- Dashboard `lib/types/events.ts`: TypeScript mirror of Python protocol — already in sync

### Established Patterns
- `event_bus.py` uses daemon threads for handler isolation — bridge handler should follow same pattern
- `state_engine.py` wraps event publishing in try/except — events never fail core operations (Phase 68 decision)
- Singleton pattern: `event_bridge = UnixSocketTransport()` at module level in transport.py

### Integration Points
- `state_engine.py` (lines 393-401, 485-493): Currently publishes directly to event_bridge — needs migration to event_bus.emit()
- `autonomy/hooks.py` (lines 97-99): Currently publishes directly to event_bridge — needs migration
- `autonomy/events.py` (lines 313-318, 367): Already uses event_bus.emit() — no change needed
- `cli/project.py` (lines 313, 475): Already uses event_bus.emit() — no change needed
- `cli/monitor.py` (lines 765-793): Currently starts its own server — should use shared singleton instead
- Dashboard SSE route: Hardcodes `/tmp/openclaw-events.sock` — needs to read from OPENCLAW_ROOT convention

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 70-event-bridge-activation*
*Context gathered: 2026-03-04*
