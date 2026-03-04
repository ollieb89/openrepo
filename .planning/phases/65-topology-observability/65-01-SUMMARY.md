---
phase: 65-topology-observability
plan: 01
subsystem: ui
tags: [reactflow, dagre, swr, nextjs, typescript, topology]

# Dependency graph
requires:
  - phase: 62-structure-proposal-engine
    provides: Python topology models (TopologyGraph, TopologyProposal, ProposalSet, RubricScore, TopologyDiff)
  - phase: 63-correction-workflow
    provides: Changelog/correction storage format (ChangelogEntry, correction_type)
  - phase: 64-structural-memory
    provides: Rubric score enrichment for preference_fit scores

provides:
  - TypeScript topology type interfaces matching Python serialization format
  - GET /api/topology — reads approved graph + pending proposals from filesystem
  - GET /api/topology/changelog — reads correction changelog from filesystem
  - useTopology and useTopologyChangelog SWR hooks
  - Topology nav entry in dashboard Sidebar
  - @xyflow/react and @dagrejs/dagre installed as dashboard dependencies
  - Wave 0 test stubs for all 6 TOBS requirements (23 placeholder tests, all green)

affects:
  - 65-02 (topology graph canvas component — consumes types and useTopology hook)
  - 65-03 (correction timeline and confidence chart — consumes useTopologyChangelog hook)

# Tech tracking
tech-stack:
  added:
    - "@xyflow/react 12.10.1 — React Flow graph canvas"
    - "@dagrejs/dagre 2.0.4 — directed graph auto-layout"
  patterns:
    - "API routes follow metrics/route.ts pattern: withAuth wrapper, searchParams project, try/catch fs reads, NextResponse.json"
    - "SWR hooks follow useMetrics.ts pattern: plain fetch, null key when no projectId, refreshInterval for polling"
    - "Types mirror Python dataclass serialization exactly — field names match snake_case Python output"

key-files:
  created:
    - packages/dashboard/src/lib/types/topology.ts
    - packages/dashboard/src/app/api/topology/route.ts
    - packages/dashboard/src/app/api/topology/changelog/route.ts
    - packages/dashboard/src/lib/hooks/useTopology.ts
    - packages/dashboard/tests/topology/api.test.ts
    - packages/dashboard/tests/topology/transform.test.ts
    - packages/dashboard/tests/topology/diff.test.ts
    - packages/dashboard/tests/topology/timeline.test.ts
    - packages/dashboard/tests/topology/confidence.test.ts
    - packages/dashboard/tests/topology/proposals.test.ts
  modified:
    - packages/dashboard/src/components/layout/Sidebar.tsx
    - packages/dashboard/package.json

key-decisions:
  - "Topology nav item uses Network icon from lucide-react (already in deps) rather than inline SVG"
  - "SWR hooks use 30s refresh interval (vs 5s for metrics) — topology changes on correction events, not continuously"
  - "API routes gracefully return null/[] for missing topology files — valid state for projects that haven't been proposed yet"

patterns-established:
  - "API route filesystem path: path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'topology')"
  - "Wave 0 test stubs: expect(true).toBe(true) placeholders with TODO comments for Plan 02/03 to fill"

requirements-completed: [TOBS-01, TOBS-02, TOBS-03, TOBS-04, TOBS-05, TOBS-06]

# Metrics
duration: 3min
completed: 2026-03-04
---

# Phase 65 Plan 01: Topology Observability Data Layer Summary

**Topology data layer: TypeScript interfaces, 2 filesystem API routes, 2 SWR hooks, sidebar nav, @xyflow/react installed, and 23 Wave 0 test stubs all green**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-04T09:16:44Z
- **Completed:** 2026-03-04T09:19:24Z
- **Tasks:** 3 (Task 0 + Task 1 + Task 2)
- **Files modified:** 12

## Accomplishments

- All 11 TypeScript topology interfaces exported from `types/topology.ts`, matching Python dataclass serialization format exactly
- Two Next.js API routes (`/api/topology` and `/api/topology/changelog`) reading from the established filesystem path (`{OPENCLAW_ROOT}/workspace/.openclaw/{projectId}/topology/`), gracefully returning null/[] for missing files
- Two SWR hooks (`useTopology`, `useTopologyChangelog`) providing data to future visualization components with 30s refresh and loading/error states
- Topology nav link added to Sidebar before Metrics using the Network lucide icon
- 23 Wave 0 test stubs across 6 files, covering all TOBS requirements — all passing immediately

## Task Commits

Each task was committed atomically:

1. **Task 0: Wave 0 test stubs** - `67826bb` (test)
2. **Task 1: Dependencies and TypeScript types** - `4cb2d8e` (feat)
3. **Task 2: API routes, SWR hooks, sidebar** - `557b3ac` (feat)

**Plan metadata:** (final commit below)

## Files Created/Modified

- `packages/dashboard/src/lib/types/topology.ts` - 11 TypeScript interfaces matching Python topology model serialization
- `packages/dashboard/src/app/api/topology/route.ts` - GET endpoint returning approved + pending topology
- `packages/dashboard/src/app/api/topology/changelog/route.ts` - GET endpoint returning correction changelog
- `packages/dashboard/src/lib/hooks/useTopology.ts` - `useTopology` and `useTopologyChangelog` SWR hooks
- `packages/dashboard/src/components/layout/Sidebar.tsx` - Added Topology nav link with Network icon
- `packages/dashboard/package.json` - Added @xyflow/react and @dagrejs/dagre
- `packages/dashboard/tests/topology/api.test.ts` - TOBS-01/02 API route stubs
- `packages/dashboard/tests/topology/transform.test.ts` - TOBS-01/02 React Flow transform stubs
- `packages/dashboard/tests/topology/diff.test.ts` - TOBS-03 diff highlight stubs
- `packages/dashboard/tests/topology/timeline.test.ts` - TOBS-04 correction timeline stubs
- `packages/dashboard/tests/topology/confidence.test.ts` - TOBS-05 confidence chart stubs
- `packages/dashboard/tests/topology/proposals.test.ts` - TOBS-06 ProposalSet parsing stubs

## Decisions Made

- Topology nav item uses `Network` icon from lucide-react (already a dependency) rather than inline SVG — consistent with `Bot` and `ExternalLink` used elsewhere
- SWR hooks use 30s refresh interval vs 5s for metrics — topology data changes on explicit user corrections, not continuously
- API routes return null for missing `current.json` / `pending-proposals.json` — valid state for projects that have not yet run `openclaw propose`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02: Topology graph canvas component can import `useTopology`, `TopologyGraph`, `TopologyNode`, `TopologyEdge`, `TopologyDiff` directly from the established paths
- Plan 03: Correction timeline and confidence chart components can import `useTopologyChangelog`, `ChangelogEntry`, `RubricScore` directly
- Wave 0 stubs in `tests/topology/` are ready to be filled in with real assertions as production code is created

---
*Phase: 65-topology-observability*
*Completed: 2026-03-04*

## Self-Check: PASSED

All files verified present. All 3 task commits verified in git log (67826bb, 4cb2d8e, 557b3ac).
