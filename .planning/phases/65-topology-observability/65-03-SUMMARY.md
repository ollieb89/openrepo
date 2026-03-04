---
phase: 65-topology-observability
plan: 03
subsystem: ui
tags: [nextjs, recharts, react-flow, typescript, vitest, topology, time-travel]

requires:
  - phase: 65-01
    provides: TypeScript types (topology.ts), SWR hooks (useTopology, useTopologyChangelog), API routes
  - phase: 65-02
    provides: TopologyGraph, DualPanel, ProposalComparison, RubricBar, topology-utils.ts with computeDiffHighlights

provides:
  - CorrectionTimeline component with sortChangelog/extractDiffLines pure utilities
  - ConfidenceChart component with transformChangelogToChartData pure utility and per-dimension expansion
  - NodeDetailPanel slide-in component showing role info, edges, archetype presence
  - /topology page wiring all components with time-travel state management
  - 20 passing unit tests (12 timeline + 8 confidence) with real assertions replacing placeholder stubs

affects:
  - Any future phase adding correction history visualization
  - Phase 65 human verification checkpoint

tech-stack:
  added: []
  patterns:
    - "Pure utility functions co-located with components (sortChangelog, extractDiffLines, transformChangelogToChartData) exported for vitest unit testing without DOM"
    - "Time-travel via diff highlights overlay on current topology (not full historical state reconstruction)"
    - "selectedEventIndex null = live state; set = time-travel mode with amber banner"
    - "Node detail panel: fixed right side panel with backdrop click and Escape key dismissal"
    - "Recharts with ResponsiveContainer (width 100%, height 220) for chart rendering"

key-files:
  created:
    - packages/dashboard/src/components/topology/CorrectionTimeline.tsx
    - packages/dashboard/src/components/topology/ConfidenceChart.tsx
    - packages/dashboard/src/components/topology/NodeDetailPanel.tsx
    - packages/dashboard/src/app/topology/page.tsx
  modified:
    - packages/dashboard/tests/topology/timeline.test.ts
    - packages/dashboard/tests/topology/confidence.test.ts

key-decisions:
  - "Time-travel v1 simplification: shows diff highlights on current topology rather than reconstructing full historical state — deferred for future gap closure plan if needed"
  - "sortChangelog exported as pure function (not internal) — enables unit testing without React DOM setup"
  - "extractDiffLines returns DiffLine[] with type and text fields — both needed for rendering and test assertions"
  - "transformChangelogToChartData skips entries without rubric_scores — sparse changelog is valid, chart shows only annotated corrections"
  - "preference_fit taken from first available archetype score — consistent single value across archetypes rather than per-archetype dashed lines"
  - "ReferenceLine at x=5 only renders when chartData.length >= 5 — avoids misleading reference on sparse data"

requirements-completed: [TOBS-01, TOBS-02, TOBS-03, TOBS-04, TOBS-05, TOBS-06]

duration: 4min
completed: 2026-03-04
---

# Phase 65 Plan 03: Topology Observability Visualization Summary

**Correction timeline with expandable structural diffs, confidence evolution chart with per-archetype Recharts lines, node detail slide-in panel, and /topology page with time-travel correction navigation assembled into a single navigable view**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-04T09:29:13Z
- **Completed:** 2026-03-04T09:33:27Z
- **Tasks:** 2/3 (Task 3 is checkpoint:human-verify, pending user verification)
- **Files modified:** 6

## Accomplishments

- CorrectionTimeline renders vertical timeline with colored diff expansion (green/red/yellow lines), pushback note amber callout blocks, and click-to-select time-travel triggering
- ConfidenceChart shows multi-series Recharts line chart with lean/balanced/robust solid lines, dashed preference_fit, 5-correction reference line, and per-dimension expandable view for a selected archetype
- NodeDetailPanel is a fixed right-side slide-in showing role id, level, risk badge, intent, edge list (with direction arrows and type badges), and archetype presence; closes on Escape or backdrop click
- /topology page wires all components with selectedEventIndex state driving time-travel: amber banner with correction number and summary, diff highlights passed to DualPanel, "Back to current" button
- All 20 topology unit tests pass (12 timeline + 8 confidence) with real assertions replacing placeholder stubs

## Task Commits

1. **Task 1: CorrectionTimeline, ConfidenceChart, NodeDetailPanel, and unit tests** - `43b2f81` (feat)
2. **Task 2: Topology page assembly with time-travel state** - `2e84bdd` (feat)
3. **Task 3: Visual verification** - pending checkpoint:human-verify

## Files Created/Modified

- `packages/dashboard/src/components/topology/CorrectionTimeline.tsx` - Vertical timeline with expandable diff cards, pushback callouts; exports sortChangelog and extractDiffLines for testing
- `packages/dashboard/src/components/topology/ConfidenceChart.tsx` - Multi-series Recharts chart; exports transformChangelogToChartData; per-dimension expansion toggle
- `packages/dashboard/src/components/topology/NodeDetailPanel.tsx` - Fixed right-side panel for node details with role info, edges, and archetype presence
- `packages/dashboard/src/app/topology/page.tsx` - Main /topology page (274 lines) assembling all components with time-travel state management
- `packages/dashboard/tests/topology/timeline.test.ts` - 12 real assertions for sortChangelog (4 tests) and extractDiffLines (8 tests)
- `packages/dashboard/tests/topology/confidence.test.ts` - 8 real assertions for transformChangelogToChartData covering empty, sparse, partial, and preference_fit extraction

## Decisions Made

- **Time-travel v1 simplification**: Shows diff highlights overlaid on current topology when clicking a timeline event rather than reconstructing full historical topology state from cumulative diffs. Amber banner makes this distinction clear to users. Full reconstruction deferred and explicitly called out in the checkpoint for user review.
- **Pure utility co-location**: sortChangelog, extractDiffLines, transformChangelogToChartData exported from their respective component files. No separate utils file needed — keeps test imports simple.
- **preference_fit from first available archetype**: Takes preference_fit from the first archetype that has a rubric score. This ensures a single consistent dashed line rather than three overlapping preference_fit lines.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Pre-existing connector test failures (5 tests in tests/connectors/) are out of scope and unrelated to this phase.

## User Setup Required

None - all changes are frontend components using existing hooks and API routes from plans 01 and 02.

## Self-Check: PASSED

All files confirmed present. Both task commits verified in git log.

## Next Phase Readiness

- All 6 TOBS requirements have corresponding UI elements on the /topology page
- Awaiting human visual verification at checkpoint (Task 3)
- If time-travel simplification is accepted as-is, phase 65 is complete
- If full historical state reconstruction is needed, a gap closure plan will be needed

---
*Phase: 65-topology-observability*
*Completed: 2026-03-04*
