# Phase 24: Dashboard Metrics - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The occc dashboard gains a dedicated Metrics page showing project-specific agent hierarchy and task/pool performance visualizations. Switching projects updates both the agent tree and all metrics. This phase delivers the visualization — backend API endpoints for metrics aggregation are in scope only as needed to serve the frontend.

</domain>

<decisions>
## Implementation Decisions

### Metrics visualization
- Task completion times displayed as a **bar chart** (last N tasks, vertical bars showing duration per task)
- Pool utilization shown as a **radial gauge** — circular progress ring with color shift green→yellow→red as utilization climbs
- Container lifecycle counts (spawned, running, completed, failed) shown as **compact stat cards** — row of small color-coded cards, each with count + label
- Use a **lightweight charting library** (e.g. recharts or chart.js) rather than hand-built CSS/SVG

### Agent hierarchy display
- **Tree view** with expand/collapse — nested L1 → L2 → L3 showing the 3-tier hierarchy naturally
- Global agents (no `project` field) shown in a **separate "Global" section** at the top of the tree with a badge — project-specific agents nested below
- **Status indicator dots** next to each agent: green=idle, yellow=busy, gray=offline (derived from task state data)
- **Instant swap** when switching projects — no transition animation, SWR handles data fetch

### Layout & density
- Metrics live on a **dedicated new tab/page** in the dashboard navigation — not inline or sidebar
- **Side-by-side layout**: agent tree on left (~30% width), metrics charts on right (~70%)
- **Responsive**: stacks vertically on narrow screens
- **Compact stat cards** in a single row above the bar chart — number + label, minimal padding

### Empty & loading states
- Zero completed tasks: **placeholder chart outlines** (grayed-out chart shapes) with centered message: "No tasks completed yet. Spawn a specialist to see metrics."
- No project agents: show **global-only tree** with "No agents assigned to this project" message in the project section
- Loading: **skeleton loaders** — pulsing gray shapes matching chart dimensions
- API errors: **inline error card** replacing the failed component — "Couldn't load metrics. Retry?" with retry button

### Claude's Discretion
- Exact charting library choice (recharts vs chart.js vs similar)
- Bar chart orientation (horizontal vs vertical)
- Radial gauge styling details (ring thickness, color thresholds)
- Typography and spacing to match existing dashboard theme
- Number of tasks shown in "last N tasks" bar chart (10–20 range)
- SWR polling interval for metrics refresh

</decisions>

<specifics>
## Specific Ideas

- The existing dashboard already has project selector (`localStorage('occc-project')`), `useAgents(projectId)` filtering, and `useTasks(projectId)` with SWR polling — these are the foundation
- Stat cards should feel consistent with the existing dashboard's visual language
- The radial gauge should be the visual anchor of the metrics section — the most eye-catching element

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 24-dashboard-metrics*
*Context gathered: 2026-02-24*
