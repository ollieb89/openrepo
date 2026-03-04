---
phase: 65-topology-observability
plan: 02
subsystem: ui
tags: [react-flow, dagre, topology, dag, diff-highlights, proposals, rubric]

# Dependency graph
requires:
  - phase: 65-topology-observability-01
    provides: topology types (TopologyGraph, TopologyDiff, ProposalSet, RubricScore), API routes, hooks, test stubs

provides:
  - React Flow DAG renderer with dagre top-down layout (TopologyGraph.tsx)
  - Custom TopologyNode with level-based coloring and diff highlights
  - Custom TopologyEdge with per-type stroke/dash styling and midpoint label
  - DualPanel: proposed vs approved side-by-side with archetype tabs and diff highlights on both
  - RubricBar: 7-dimension compact badge row with green/yellow/red scoring
  - ProposalComparison: 3-archetype comparison with rubric scores, differentiators, top-pick ring
  - topology-utils.ts: toFlowElements (dagre layout), computeDiffHighlights, EDGE_STYLE constants
  - Real unit tests for toFlowElements, computeDiffHighlights, and ProposalSet parsing

affects: [65-03, dashboard pages that import topology components]

# Tech tracking
tech-stack:
  added: []  # @xyflow/react and @dagrejs/dagre already installed from plan 01
  patterns:
    - "nodeTypes/edgeTypes defined as const OUTSIDE component for stable React Flow reference"
    - "NodeProps<Node<Data>> generic pattern for typed custom nodes in @xyflow/react v12"
    - "EdgeProps<Edge<Data>> generic pattern for typed custom edges in @xyflow/react v12"
    - "DiffHighlightMap built from TopologyDiff — nodes/edges keyed by id / 'from->to' string"
    - "toFlowElements memoized in TopologyGraph.tsx on graph + diffHighlights"
    - "EDGE_STYLE lookup table maps edge_type to CSS stroke properties"

key-files:
  created:
    - packages/dashboard/src/components/topology/topology-utils.ts
    - packages/dashboard/src/components/topology/TopologyNode.tsx
    - packages/dashboard/src/components/topology/TopologyEdge.tsx
    - packages/dashboard/src/components/topology/TopologyGraph.tsx
    - packages/dashboard/src/components/topology/DualPanel.tsx
    - packages/dashboard/src/components/topology/RubricBar.tsx
    - packages/dashboard/src/components/topology/ProposalComparison.tsx
  modified:
    - packages/dashboard/tests/topology/transform.test.ts
    - packages/dashboard/tests/topology/diff.test.ts
    - packages/dashboard/tests/topology/proposals.test.ts

key-decisions:
  - "NodeProps<Node<Data>> not NodeProps<Data> — @xyflow/react v12 generic requires the full Node type as the type parameter"
  - "TopologyNodeData and TopologyEdgeData exported from utils (not node/edge files) to avoid circular imports"
  - "Edge key for diff highlights uses 'from_role->to_role' string format matching computeDiffHighlights output"
  - "ProposalComparison uses smaller graph height via className override (plan specified h-[250px] inline via container)"
  - "DualPanel shows approved null state with 'No approved topology yet — approve a proposal to see it here' message per locked decision"

patterns-established:
  - "All topology component files live under packages/dashboard/src/components/topology/"
  - "useNodesState/useEdgesState initialized from useMemo-derived layout for React Flow"
  - "RubricBar: >=7 = green, 4-6 = yellow, <4 = red badge coloring"

requirements-completed: [TOBS-01, TOBS-02, TOBS-06]

# Metrics
duration: 5min
completed: 2026-03-04
---

# Phase 65 Plan 02: Topology Graph Visualization Summary

**React Flow DAG with dagre layout, dual-panel proposed/approved diff view, 7-dimension rubric bar, and 3-archetype comparison grid — all topology unit tests passing with real assertions**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-04T09:21:46Z
- **Completed:** 2026-03-04T09:26:50Z
- **Tasks:** 2
- **Files modified:** 9 (7 created, 2 updated)

## Accomplishments

- Built complete React Flow DAG rendering pipeline: `toFlowElements` converts `TopologyGraph` JSON to dagre-positioned nodes and styled edges via `TopologyGraph.tsx`
- Implemented all 5 visual components: TopologyNode (level colors + diff highlights), TopologyEdge (edge-type styled bezier paths with labels), DualPanel (proposed/approved side-by-side with archetype tabs), RubricBar (7-dimension color-coded badges), ProposalComparison (3-archetype comparison with top-pick ring)
- Replaced all 3 test file stubs with real assertions: 4 transform tests, 7 diff tests, 4 proposal tests — all passing

## Task Commits

1. **Task 1: Topology utils, custom node, and custom edge components** - `37ba449` (feat)
2. **Task 2: TopologyGraph, DualPanel, RubricBar, ProposalComparison, proposal tests** - `d1cc7e9` (feat)

## Files Created/Modified

- `packages/dashboard/src/components/topology/topology-utils.ts` - toFlowElements (dagre layout), computeDiffHighlights, EDGE_STYLE, DiffHighlightMap type
- `packages/dashboard/src/components/topology/TopologyNode.tsx` - Custom node with level-based border colors (L1=purple/L2=blue/L3=gray) and diff highlight overrides
- `packages/dashboard/src/components/topology/TopologyEdge.tsx` - Custom edge with getBezierPath, per-type stroke/dash, midpoint edge_type label
- `packages/dashboard/src/components/topology/TopologyGraph.tsx` - React Flow wrapper with dagre layout, nodeTypes/edgeTypes outside component, Background + Controls
- `packages/dashboard/src/components/topology/DualPanel.tsx` - Side-by-side proposed (with Lean/Balanced/Robust tabs + confidence badge) vs approved panels; diff highlights on both
- `packages/dashboard/src/components/topology/RubricBar.tsx` - Compact 7-dimension badge row: green>=7, yellow 4-6, red<4
- `packages/dashboard/src/components/topology/ProposalComparison.tsx` - 3-column grid with graph, rubric, differentiators, justification, top-pick ring
- `packages/dashboard/tests/topology/transform.test.ts` - Real assertions for toFlowElements (positions, data fields, edge source/target, diff highlights)
- `packages/dashboard/tests/topology/diff.test.ts` - Real assertions for computeDiffHighlights (added/removed/modified nodes and edges)
- `packages/dashboard/tests/topology/proposals.test.ts` - Real assertions for ProposalSet (archetype access, rubric extraction, highest confidence, null safety)

## Decisions Made

- **NodeProps generic fix:** `@xyflow/react` v12 requires `NodeProps<Node<Data>>` not `NodeProps<Data>` — the full Node type is the type parameter; fixed auto-detected TypeScript errors
- **TopologyNodeData/TopologyEdgeData exported from topology-utils.ts:** Avoids circular imports; both component files and external consumers can import from one place
- **Edge diff key format:** `from_role->to_role` string matches `computeDiffHighlights` output exactly, enabling diff highlight lookup in `toFlowElements`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed NodeProps/EdgeProps generic constraint errors**
- **Found during:** Task 1 verification (TypeScript compile)
- **Issue:** `NodeProps<TopologyNodeData>` and `EdgeProps<TopologyEdgeData>` are invalid — @xyflow/react v12 expects `NodeProps<Node<Data>>` where the type parameter is a full `Node` type, not the data type
- **Fix:** Changed to `NodeProps<TopologyNodeType>` and `EdgeProps<TopologyEdgeType>` where those are `Node<Data>` and `Edge<Data>` type aliases; also moved TopologyNodeData/TopologyEdgeData to topology-utils.ts to be shared
- **Files modified:** TopologyNode.tsx, TopologyEdge.tsx, topology-utils.ts
- **Verification:** TypeScript compiled cleanly with no errors

---

**Total deviations:** 1 auto-fixed (Rule 1 - type constraint bug)
**Impact on plan:** Essential for TypeScript correctness. No scope creep.

## Issues Encountered

None — TypeScript generics issue was caught immediately during verification and auto-fixed.

## Next Phase Readiness

- All 6 topology visualization components are complete and TypeScript-clean
- Unit tests for transform (4), diff (7), and proposals (4) all pass
- Components are ready to be wired into the topology page from plan 65-01 (`TopologyPanel.tsx` already imports structure; plan 65-03 may add the page integration)
- Pre-existing connector test failures (4 tests, `/home/ollie/.openclaw/` permission error) are out of scope and pre-date this work

---
*Phase: 65-topology-observability*
*Completed: 2026-03-04*
