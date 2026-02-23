# Phase 15: Dashboard Project Switcher - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the occc dashboard multi-project aware. Users can switch the active project from the UI; all data panels (tasks, agents, metrics, logs) reflect only the selected project's state. Project CRUD and management are not in scope.

</domain>

<decisions>
## Implementation Decisions

### Project selector UX
- Compact dropdown in the dashboard header, next to the OpenClaw logo/title
- Each project entry shows name + colored status badge (active/idle/error)
- Projects auto-discovered by scanning the `projects/` directory for `project.json` files — no manual config needed

### Switch transition
- Brief loading skeleton (~200-500ms) while new project data loads
- Old project data clears immediately on switch — no stale data visible
- Panels show loading state, then populate with new project's data

### Data scoping
- Strictly one project at a time — no aggregate/cross-project view
- SSE stream reconnects per project switch: close current connection, open new one with `?project=<id>`
- API routes accept `?project=<id>` parameter for scoping
- Unknown project ID returns 404; missing parameter defaults to first available project

### Claude's Discretion
- Loading skeleton design and animation
- Exact dropdown component styling and positioning
- How status badge color/state is determined from project data
- Default project selection logic on first load (first alphabetical, most recent, etc.)
- localStorage persistence of last-selected project

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-dashboard-project-switcher*
*Context gathered: 2026-02-23*
