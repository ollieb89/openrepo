# Phase 65: Topology Observability - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

The dashboard surfaces proposed and approved topologies as interactive graphs, shows correction history with structural diffs, and displays confidence and proposal evolution over time. Does NOT include CLI topology commands (Phase 63), structural memory logic (Phase 64), or any new topology computation — purely visualization of existing data.

</domain>

<decisions>
## Implementation Decisions

### Graph Rendering
- Use React Flow for interactive DAG visualization — purpose-built for node-graph UIs in React
- Top-down layout orientation: L1 at top, L2 in middle, L3 at bottom — matches the 3-tier hierarchy mental model
- Edge types visually distinct via color + line style: solid for delegation, dashed for coordination, dotted for escalation, thick for review_gate. Legend shown alongside graph
- Clicking a node opens a side detail panel showing role details: capabilities, delegation edges, pool config, archetype classification contribution
- Zoom and pan enabled on graph panels

### Side-by-Side Layout
- Dual-panel layout: "Proposed" on left, "Approved" on right — two independent graph panels
- Diff highlights appear on BOTH panels: added nodes green on proposed, removed nodes red on approved, modified nodes yellow on both
- Tab bar above proposed panel for archetype selection: "Lean", "Balanced", "Robust" tabs with confidence score badge on active tab
- Compact rubric summary bar below the proposed graph showing all 7 dimensions as small gauges/badges — quick glance without clicking
- Pre-approval empty state: right panel shows placeholder message "No approved topology yet — approve a proposal to see it here"

### Correction Timeline
- Vertical chronological timeline with correction events as cards — similar to git history view
- Each card shows: correction type (soft/hard badge), timestamp, summary of changes, expandable structural diff
- Structural diffs rendered as colored text: green for added nodes/edges, red for removed, yellow for modified. Line-item format: "+ Worker (node)", "- ReviewGate → Coordinator (edge)"
- Pushback notes (confidence warnings) shown inline as amber callout blocks within the relevant timeline card — visually distinct from correction description
- Time-travel: clicking a correction event updates the main topology graph panels to show the topology at that point in history

### Confidence Charts
- Multi-series line chart (Recharts LineChart): one line per archetype (Lean/Balanced/Robust) showing overall confidence across correction cycles
- X-axis = correction events (chronological), Y-axis = confidence 0-10
- Expandable per-dimension view: toggle reveals per-dimension lines (complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence) for the selected archetype
- preference_fit score shown as dashed secondary line on the same chart — shows how well the system learns user preferences over time
- Low-data state: show whatever data points exist, add vertical dashed line at 5-correction threshold labeled "Pattern extraction begins". preference_fit stays flat at 5 (neutral baseline) before threshold

### Claude's Discretion
- React Flow node/edge custom component styling details
- Exact color palette for edge types and diff highlights
- Graph layout algorithm parameters (dagre spacing, node dimensions)
- Timeline card expand/collapse animation
- Chart tooltip formatting and interaction
- Loading skeletons and error states
- API route structure for fetching topology data
- Responsive behavior on smaller screens

</decisions>

<specifics>
## Specific Ideas

- The topology graph should feel like inspecting infrastructure — clear, professional, informative. Not a decorative visualization
- Time-travel through corrections should feel seamless — click a point in history, see the topology at that moment
- Confidence charts should make it obvious whether the system is learning from corrections — the trend should tell a story
- Diff highlights on both panels simultaneously lets you see "what was" and "what's proposed" without mental context-switching

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Card` component (components/common/Card.tsx): Standard panel with title/subtitle/action — use for timeline cards, detail panels, chart containers
- `StatusBadge` (components/common/StatusBadge.tsx): Reusable for correction type badges (soft/hard)
- `Recharts` (already in deps): LineChart, AreaChart, Tooltip, Legend — use directly for confidence evolution charts
- `SWR` (already in deps): Data fetching with caching — use for topology API routes
- `lucide-react` (already in deps): Icons for edge types, expand/collapse, navigation
- Metrics components pattern (components/metrics/): CompletionBarChart, PoolGauge, MetricsSkeleton — reference for chart component structure and skeleton patterns

### Established Patterns
- Dashboard pages as Next.js app routes under `src/app/{feature}/page.tsx`
- Component directories per feature: `src/components/{feature}/`
- API routes under `src/app/api/{feature}/route.ts`
- SWR for client-side data fetching with `useAuthenticatedFetch` hook
- Tailwind CSS with dark mode support (`dark:` variants on all components)
- Card-based panel layout with borders, shadows, rounded corners

### Integration Points
- New route: `src/app/topology/page.tsx` — main topology page
- New API routes: `src/app/api/topology/` — read from project-scoped topology files (current.json, changelog.json, pending-proposals.json, memory-profile.json, patterns.json)
- Sidebar navigation: add "Topology" link in `src/components/layout/Sidebar.tsx`
- Project context: topology data is project-scoped under `workspace/.openclaw/{project_id}/topology/`
- New dependency: `reactflow` (npm package) — not yet installed

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 65-topology-observability*
*Context gathered: 2026-03-04*
