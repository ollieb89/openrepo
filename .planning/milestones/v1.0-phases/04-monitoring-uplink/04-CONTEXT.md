# Phase 4: Monitoring Uplink - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy the "occc" dashboard for real-time human oversight of the running AI swarm. Renders live agent status (L1/L2/L3 hierarchy), global health metrics, and streamed container logs with sensitive information redaction. This is a monitoring/visibility tool — no agent control or task management capabilities.

**Note:** OpenClaw already ships a built-in Control UI (Vite + Lit) at the gateway port with chat, config editing, skill management, and channel status. The occc dashboard specifically adds swarm-hierarchy monitoring that the existing Control UI doesn't cover: multi-tier agent visualization, container-level log streaming, and Jarvis Protocol state visibility.

</domain>

<decisions>
## Implementation Decisions

### Dashboard layout
- Mission control panel layout — fixed zones: hierarchy overview on left, detail view center, logs right
- Responsive design required — panels stack vertically on smaller screens (tablet/phone)
- Agent hierarchy overview shows: name, status indicator (colored dot), and one-line current task summary (from Jarvis Protocol state.json)
- Clicking an agent in the hierarchy loads its details in the center panel

### Log streaming UX
- One agent at a time — select an agent from the hierarchy to see that agent's log stream
- Filtering: severity level (debug/info/warn/error) plus text search
- No merged multi-agent log view — keep it focused

### Status & metrics
- Global metrics at top: total agents by tier (L1/L2/L3), count of active/idle/errored agents
- Agent state changes surfaced via toast notifications (errors, spawn/despawn events) — brief, dismissible
- Real-time updates via WebSocket (push-based, instant as state.json changes)

### Claude's Discretion
- **App architecture:** Whether to build as standalone Next.js 16 app or extend the existing OpenClaw Control UI (Vite + Lit). Evaluate based on integration complexity, deployment model, and existing gateway WebSocket patterns
- **Detail panel design:** Layout and content when clicking an agent — tabs vs single view, what information to surface
- **Log auto-scroll behavior:** Auto-scroll with pin, manual scroll, or hybrid approach
- **Log persistence model:** Live-only vs buffered history — decide based on memory and UX tradeoffs
- **Jarvis Protocol state display:** Whether to surface state.json data as a dedicated view or integrate it into existing status/task information
- **Loading skeleton and error state design**
- **Exact spacing, typography, and color system**

</decisions>

<specifics>
## Specific Ideas

- Existing OpenClaw Control UI provides admin features (chat, config, skills, channels) — occc adds the swarm-hierarchy monitoring layer that doesn't exist yet
- OpenClaw gateway already exposes WebSocket at port 18789 — dashboard should leverage existing connection infrastructure
- Jarvis Protocol state.json is the source of truth for agent status and task progress
- Mission control aesthetic — think command center, not settings page

</specifics>

<deferred>
## Deferred Ideas

- Agent control capabilities (start/stop/restart agents from dashboard) — separate phase
- Historical metrics and trend graphs — future enhancement
- Redaction rules discussion was selected but not discussed — will be handled as an implementation detail (SEC-02 requirement is clear from roadmap)

</deferred>

---

*Phase: 04-monitoring-uplink*
*Context gathered: 2026-02-18*
