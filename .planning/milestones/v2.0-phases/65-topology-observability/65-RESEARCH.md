# Phase 65: Topology Observability - Research

**Researched:** 2026-03-04
**Domain:** Next.js dashboard, React Flow graph visualization, Recharts charting, filesystem topology data
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Graph Rendering
- Use React Flow for interactive DAG visualization — purpose-built for node-graph UIs in React
- Top-down layout orientation: L1 at top, L2 in middle, L3 at bottom — matches the 3-tier hierarchy mental model
- Edge types visually distinct via color + line style: solid for delegation, dashed for coordination, dotted for escalation, thick for review_gate. Legend shown alongside graph
- Clicking a node opens a side detail panel showing role details: capabilities, delegation edges, pool config, archetype classification contribution
- Zoom and pan enabled on graph panels

#### Side-by-Side Layout
- Dual-panel layout: "Proposed" on left, "Approved" on right — two independent graph panels
- Diff highlights appear on BOTH panels: added nodes green on proposed, removed nodes red on approved, modified nodes yellow on both
- Tab bar above proposed panel for archetype selection: "Lean", "Balanced", "Robust" tabs with confidence score badge on active tab
- Compact rubric summary bar below the proposed graph showing all 7 dimensions as small gauges/badges — quick glance without clicking
- Pre-approval empty state: right panel shows placeholder message "No approved topology yet — approve a proposal to see it here"

#### Correction Timeline
- Vertical chronological timeline with correction events as cards — similar to git history view
- Each card shows: correction type (soft/hard badge), timestamp, summary of changes, expandable structural diff
- Structural diffs rendered as colored text: green for added nodes/edges, red for removed, yellow for modified. Line-item format: "+ Worker (node)", "- ReviewGate → Coordinator (edge)"
- Pushback notes (confidence warnings) shown inline as amber callout blocks within the relevant timeline card — visually distinct from correction description
- Time-travel: clicking a correction event updates the main topology graph panels to show the topology at that point in history

#### Confidence Charts
- Multi-series line chart (Recharts LineChart): one line per archetype (Lean/Balanced/Robust) showing overall confidence across correction cycles
- X-axis = correction events (chronological), Y-axis = confidence 0-10
- Expandable per-dimension view: toggle reveals per-dimension lines (complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference_fit, overall confidence) for the selected archetype
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOBS-01 | Dashboard displays the currently proposed topology as a visual graph (nodes = roles, edges = relationships) | React Flow `@xyflow/react` with dagre layout; topology data from `pending-proposals.json` via API route |
| TOBS-02 | Dashboard displays the approved topology alongside the proposed topology for comparison | Dual-panel React Flow layout; approved topology from `current.json`; diff highlights via TopologyDiff model |
| TOBS-03 | Dashboard shows correction history for a project with structural diffs between versions | `changelog.json` data model maps directly to timeline cards; TopologyDiff `added_nodes/removed_nodes/modified_nodes/added_edges/removed_edges` fields drive colored text rendering |
| TOBS-04 | Dashboard shows a structural diff timeline — chronological view of how topology evolved across proposals and corrections | Changelog entries sorted by timestamp; time-travel state management drives topology graph panel updates |
| TOBS-05 | Dashboard shows confidence evolution — how proposal confidence scores changed across correction cycles | Recharts LineChart with multi-series; `overall_confidence` from `rubric_score` in changelog entries per archetype |
| TOBS-06 | Dashboard shows the multi-proposal comparison view with rubric scores, key deltas, and archetype labels | `pending-proposals.json` contains full `ProposalSet` with all 3 `TopologyProposal` objects including `RubricScore` and `key_differentiators` |
</phase_requirements>

## Summary

Phase 65 is a pure frontend visualization phase. All backend data already exists from phases 61-64. The work is reading existing filesystem data through new Next.js API routes and rendering it via React Flow graphs, Recharts line charts, and custom timeline components.

The core dependency gap is `@xyflow/react` — not yet in `packages/dashboard/package.json`. This must be installed (along with `@dagrejs/dagre` for automatic top-down layout). Everything else is already available: Recharts 3.7.0 for confidence charts, SWR 2.2 for data fetching, Tailwind CSS for styling, and `lucide-react` for icons.

The data model is fully understood from reading the topology Python modules. `current.json` holds the approved `TopologyGraph`, `pending-proposals.json` holds the full `ProposalSet` (3 archetypes, each with `TopologyGraph` + `RubricScore`), and `changelog.json` is an append-only list of correction events each containing a `TopologyDiff` dict. These map cleanly to the 6 UI requirements.

**Primary recommendation:** Install `@xyflow/react@^12` and `@dagrejs/dagre`, build 4 API routes reading from the topology directory, implement 6 React components, wire them into a new `/topology` page following existing dashboard conventions.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@xyflow/react` | ^12.10.x | Interactive DAG graph rendering | Purpose-built for node-graph UIs in React; locked decision from CONTEXT.md |
| `@dagrejs/dagre` | ^1.x | Automatic top-down DAG layout | Official React Flow recommendation for tree/hierarchy graphs; minimal bundle (~40KB) |
| `recharts` | 3.7.0 (already installed) | Multi-series line charts for confidence evolution | Already in deps; LineChart with multiple `<Line>` components is the standard pattern |
| `swr` | 2.4.0 (already installed) | Client-side data fetching with cache | Already established pattern in all dashboard hooks |
| `tailwindcss` | 3.4.0 (already installed) | Styling with dark mode support | All existing components use Tailwind with `dark:` variants |
| `lucide-react` | 0.575.0 (already installed) | Icons for edge type legend, expand/collapse | Already in deps; used throughout dashboard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `next/server` (NextResponse, NextRequest) | 15.5.12 (already installed) | API route handlers | All 4 topology API routes follow withAuth(handler) pattern |
| `fs/promises` (Node built-in) | — | Reads topology JSON files from disk | API routes read from `OPENCLAW_ROOT/workspace/.openclaw/{project}/topology/` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `@dagrejs/dagre` | `elkjs` | ELK is more powerful (1.4MB) but overkill for this 3-tier hierarchy; dagre is 40KB and handles simple DAGs perfectly |
| `@dagrejs/dagre` | `d3-hierarchy` | d3-hierarchy requires single root and assigns uniform dimensions; dagre supports arbitrary DAG topology |

**Installation:**
```bash
cd ~/Development/Tools/openrepo/packages/dashboard
pnpm add @xyflow/react @dagrejs/dagre
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── app/
│   ├── topology/
│   │   └── page.tsx              # Main topology page (TOBS-01 through TOBS-06)
│   └── api/
│       └── topology/
│           ├── route.ts           # GET /api/topology?project=X — current + pending
│           ├── changelog/
│           │   └── route.ts       # GET /api/topology/changelog?project=X
│           └── proposals/
│               └── route.ts       # GET /api/topology/proposals?project=X (optional split)
├── components/
│   └── topology/
│       ├── TopologyGraph.tsx      # React Flow wrapper with dagre layout
│       ├── TopologyNode.tsx       # Custom node component (role card)
│       ├── TopologyEdge.tsx       # Custom edge with label
│       ├── DualPanel.tsx          # Proposed + Approved side-by-side
│       ├── CorrectionTimeline.tsx # Vertical timeline with diff cards
│       ├── ConfidenceChart.tsx    # Multi-series Recharts LineChart
│       ├── ProposalComparison.tsx # 3-archetype comparison view
│       └── RubricBar.tsx          # 7-dimension gauge/badge row
└── lib/
    └── hooks/
        └── useTopology.ts         # SWR hook for topology data
```

### Pattern 1: API Route — Read Topology Files
**What:** Next.js API route reads JSON files from disk, returns structured response
**When to use:** All 4 topology endpoints; follows `metrics/route.ts` pattern exactly

```typescript
// Source: packages/dashboard/src/app/api/metrics/route.ts (established pattern)
import { NextRequest, NextResponse } from 'next/server';
import { getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import fs from 'fs/promises';
import path from 'path';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '~/.openclaw';

function topologyDir(projectId: string) {
  return path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'topology');
}

async function handler(request: NextRequest): Promise<NextResponse> {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project') || await getActiveProjectId();

  const dir = topologyDir(projectId);

  // Read current.json (approved topology)
  let approved = null;
  try {
    const raw = await fs.readFile(path.join(dir, 'current.json'), 'utf-8');
    approved = JSON.parse(raw);
  } catch { /* no approved topology yet */ }

  // Read pending-proposals.json
  let proposals = null;
  try {
    const raw = await fs.readFile(path.join(dir, 'pending-proposals.json'), 'utf-8');
    proposals = JSON.parse(raw);
  } catch { /* no proposals yet */ }

  return NextResponse.json({ approved, proposals, projectId });
}

export const GET = withAuth(handler);
```

### Pattern 2: React Flow DAG with Dagre Layout
**What:** Convert topology nodes/edges into React Flow format, apply dagre for top-down layout
**When to use:** Both the Proposed and Approved graph panels

```typescript
// Source: https://reactflow.dev/examples/layout/dagre
import '@xyflow/react/dist/style.css';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState } from '@xyflow/react';
import Dagre from '@dagrejs/dagre';
import type { Node, Edge } from '@xyflow/react';

const NODE_WIDTH = 180;
const NODE_HEIGHT = 60;

function getLayoutedElements(nodes: Node[], edges: Edge[]) {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80 });

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  Dagre.layout(g);

  return {
    nodes: nodes.map((n) => {
      const { x, y } = g.node(n.id);
      return { ...n, position: { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 } };
    }),
    edges,
  };
}

// Convert Python topology model to React Flow format
function toFlowNodes(topologyGraph: TopologyGraphJSON): Node[] {
  return topologyGraph.nodes.map((n) => ({
    id: n.id,
    type: 'topologyNode',   // custom node type
    data: { id: n.id, level: n.level, intent: n.intent, risk_level: n.risk_level },
    position: { x: 0, y: 0 }, // dagre will set this
  }));
}

function toFlowEdges(topologyGraph: TopologyGraphJSON, diffHighlights?: DiffMap): Edge[] {
  return topologyGraph.edges.map((e) => ({
    id: `${e.from_role}-${e.to_role}`,
    source: e.from_role,
    target: e.to_role,
    type: 'topologyEdge',
    data: { edge_type: e.edge_type, highlight: diffHighlights?.edges[`${e.from_role}-${e.to_role}`] },
  }));
}
```

### Pattern 3: Custom React Flow Node
**What:** Styled card component for topology nodes with level-based coloring and diff highlights
**When to use:** Both proposed and approved graph panels; NodeProps from @xyflow/react

```typescript
// Source: https://reactflow.dev/learn/customization/custom-nodes
import { Handle, Position, type NodeProps } from '@xyflow/react';

type TopologyNodeData = {
  id: string;
  level: number;
  intent: string;
  risk_level: string;
  highlight?: 'added' | 'removed' | 'modified';
};

const highlightStyles = {
  added: 'border-green-500 bg-green-50 dark:bg-green-900/20',
  removed: 'border-red-500 bg-red-50 dark:bg-red-900/20',
  modified: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20',
};

const levelStyles = {
  1: 'border-purple-400',
  2: 'border-blue-400',
  3: 'border-gray-400',
};

export function TopologyNodeComponent({ data, selected }: NodeProps) {
  const d = data as TopologyNodeData;
  const highlightClass = d.highlight ? highlightStyles[d.highlight] : '';
  const levelClass = levelStyles[d.level as 1|2|3] ?? 'border-gray-400';
  return (
    <div className={`px-3 py-2 rounded-lg border-2 bg-white dark:bg-gray-800 shadow-sm text-xs ${levelClass} ${highlightClass} ${selected ? 'ring-2 ring-blue-500' : ''}`}>
      <Handle type="target" position={Position.Top} className="!w-2 !h-2" />
      <p className="font-semibold text-gray-900 dark:text-white truncate max-w-[140px]">{d.id}</p>
      <p className="text-gray-500 dark:text-gray-400 truncate max-w-[140px]">{d.intent}</p>
      <Handle type="source" position={Position.Bottom} className="!w-2 !h-2" />
    </div>
  );
}
```

### Pattern 4: SWR Hook
**What:** SWR hook following the established `useMetrics` pattern for topology data
**When to use:** topology page to fetch all topology data

```typescript
// Source: packages/dashboard/src/lib/hooks/useMetrics.ts (established pattern)
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useTopology(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR(
    projectId ? `/api/topology?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 30000 }  // topology changes infrequently
  );
  return { topology: data ?? null, isLoading, error, refresh: mutate };
}

export function useTopologyChangelog(projectId: string | null) {
  const { data, error, isLoading } = useSWR(
    projectId ? `/api/topology/changelog?project=${projectId}` : null,
    fetcher,
  );
  return { changelog: data?.changelog ?? [], isLoading, error };
}
```

### Pattern 5: Multi-Series Recharts LineChart
**What:** Confidence evolution across correction cycles, one line per archetype + dashed preference_fit line
**When to use:** TOBS-05 confidence chart component

```typescript
// Source: recharts.github.io/en-US/api/LineChart + project pattern from CompletionBarChart.tsx
'use client';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';

// Data shape (derived from changelog entries):
// [{ event: 0, lean: 7, balanced: 6, robust: 5, preference_fit: 5 }, ...]

export function ConfidenceChart({ data, thresholdIdx }: Props) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
        <XAxis dataKey="event" tick={{ fontSize: 10 }} label={{ value: 'Correction', position: 'insideBottom' }} />
        <YAxis domain={[0, 10]} tick={{ fontSize: 10 }} width={28} />
        <Tooltip />
        <Legend />
        {thresholdIdx !== undefined && (
          <ReferenceLine x={thresholdIdx} stroke="#f59e0b" strokeDasharray="4 4"
            label={{ value: 'Pattern extraction begins', fontSize: 9, fill: '#f59e0b' }} />
        )}
        <Line type="monotone" dataKey="lean" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="balanced" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="robust" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="preference_fit" stroke="#f59e0b" strokeWidth={1}
          strokeDasharray="5 3" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### Anti-Patterns to Avoid
- **Forgetting the React Flow CSS import:** `@xyflow/react/dist/style.css` MUST be imported in the topology page or a parent layout — without it, the graph will not render correctly.
- **Rendering React Flow outside a sized container:** `<ReactFlow>` requires a parent with explicit `width` and `height` — use `h-[400px]` or similar Tailwind class. A container with `height: 0` will produce an invisible graph.
- **Re-running dagre on every render:** Compute layout once (on data load), store in state, only recompute when topology data changes. Running dagre in the render path causes jitter.
- **Using the old `reactflow` npm package:** The current package is `@xyflow/react`. The legacy `reactflow` package is outdated and not React 19 compatible.
- **Reading topology files synchronously in API routes:** Use `fs/promises` (async), not `fs` (sync). All existing API routes use async fs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DAG layout algorithm | Custom node positioning math | `@dagrejs/dagre` | Edge crossing minimization, rank assignment, proper spacing are NP-hard problems with decades of research |
| Interactive pan/zoom graph | Canvas + mouse event handling | `@xyflow/react` | Handles viewport transforms, node drag, edge rendering, minimap, controls out of the box |
| Graph edge routing | Custom bezier path calculation | React Flow built-in edge types | Smooth bezier, step, straight edges with proper handle attachment are already implemented |
| Multi-series chart | SVG path drawing + axes | `recharts` (already installed) | Recharts handles scales, tooltips, legend, responsive container |
| Topology data models | Re-implement Python models in TS | Inline TypeScript interfaces matching Python dicts | Data comes as plain JSON; TS interfaces suffice for type safety without duplication |

**Key insight:** All the data is already modeled and stored by phases 61-64. This phase is a visualization layer only — do not re-implement any topology logic.

## Common Pitfalls

### Pitfall 1: React Flow CSS Not Imported
**What goes wrong:** Graph renders with no styling — nodes appear as unstyled divs, edges may be invisible
**Why it happens:** `@xyflow/react` requires `import '@xyflow/react/dist/style.css'` in the component or page file
**How to avoid:** Add the import at the top of `topology/page.tsx` or in the topology layout
**Warning signs:** Nodes render as plain rectangles with no handles; edges invisible; minimap missing

### Pitfall 2: ReactFlow Container Height Not Set
**What goes wrong:** Graph panel renders with zero height (invisible)
**Why it happens:** React Flow measures its parent container for the viewport — a container with `height: auto` collapses to 0
**How to avoid:** Use explicit height: `<div className="h-[400px] w-full relative">` wrapping `<ReactFlow>`
**Warning signs:** No visible graph output; browser inspector shows 0px height on the container

### Pitfall 3: Topology Data May Not Exist
**What goes wrong:** API route throws trying to read non-existent topology files
**Why it happens:** New projects have no topology yet — `current.json` and `pending-proposals.json` don't exist until the user runs proposals
**How to avoid:** Wrap all file reads in try/catch, return `null` for missing files, render appropriate empty states in the UI
**Warning signs:** 500 errors from topology API routes; crashed API routes preventing page load

### Pitfall 4: Changelog Entry Shape Assumptions
**What goes wrong:** Confidence chart crashes or shows flat line because it can't find rubric scores
**Why it happens:** Changelog entries vary in structure — not all entries have a `rubric_score` or `annotations.approved_archetype`
**How to avoid:** Defensive access with optional chaining; skip entries that lack required fields; compute chart data only from well-formed entries
**Warning signs:** Chart renders with no data points; `Cannot read properties of undefined` errors in console

### Pitfall 5: `OPENCLAW_ROOT` Path in API Routes
**What goes wrong:** API routes fail in production because they use hardcoded `~/.openclaw`
**Why it happens:** `openclaw.ts` has `const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '~/.openclaw'` — this is a known project quirk
**How to avoid:** Import `OPENCLAW_ROOT` from `@/lib/openclaw` or use the same pattern — don't hardcode in new routes
**Warning signs:** 404 errors or "file not found" in topology API when running under a different user

### Pitfall 6: React Flow Node Types Must Be Stable References
**What goes wrong:** React Flow re-mounts all nodes on every render, causing flickering
**Why it happens:** Defining `nodeTypes` inline in JSX (e.g., `nodeTypes={{ topologyNode: MyNode }}`) creates a new object every render
**How to avoid:** Define `nodeTypes` as a const OUTSIDE the component: `const nodeTypes = { topologyNode: TopologyNodeComponent };`
**Warning signs:** Nodes flash or re-render visibly on unrelated state changes

## Code Examples

### Topology Data Types (TypeScript interfaces matching Python models)

```typescript
// Source: packages/orchestration/src/openclaw/topology/models.py (verified)
// Matches to_dict() output exactly

export interface TopologyNode {
  id: string;
  level: 1 | 2 | 3;
  intent: string;
  risk_level: 'low' | 'medium' | 'high';
  resource_constraints?: Record<string, unknown>;
  estimated_load?: number;
}

export interface TopologyEdge {
  from_role: string;
  to_role: string;
  edge_type: 'delegation' | 'coordination' | 'review_gate' | 'information_flow' | 'escalation';
}

export interface TopologyGraph {
  project_id: string;
  proposal_id?: string;
  version: number;
  created_at: string;  // ISO 8601
  metadata?: Record<string, unknown>;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface RubricScore {
  complexity: number;          // 0-10
  coordination_overhead: number;
  risk_containment: number;
  time_to_first_output: number;
  cost_estimate: number;
  preference_fit: number;      // 5 if below threshold
  overall_confidence: number;
  key_differentiators: string[];
}

export interface TopologyProposal {
  archetype: 'lean' | 'balanced' | 'robust';
  topology: TopologyGraph;
  delegation_boundaries: string;
  coordination_model: string;
  risk_assessment: string;
  justification: string;
  rubric_score?: RubricScore;
}

export interface ProposalSet {
  proposals: TopologyProposal[];
  assumptions: string[];
  outcome: string;
}

// Source: packages/orchestration/src/openclaw/topology/diff.py (verified)
export interface TopologyDiff {
  added_nodes: TopologyNode[];
  removed_nodes: TopologyNode[];
  modified_nodes: Array<{ id: string; changes: Record<string, { old: unknown; new: unknown }> }>;
  added_edges: TopologyEdge[];
  removed_edges: TopologyEdge[];
  modified_edges: Array<{ from_role: string; to_role: string; old_edge_type: string; new_edge_type: string }>;
  summary: string;
  annotations?: Record<string, unknown>;
}

// Source: packages/orchestration/src/openclaw/topology/storage.py (verified)
// changelog.json structure (each entry is appended by correction/approval flows)
export interface ChangelogEntry {
  timestamp: string;          // ISO 8601
  correction_type: 'initial' | 'soft' | 'hard';
  diff?: TopologyDiff;        // structural diff (may be absent on initial)
  annotations?: {
    approved_archetype?: 'lean' | 'balanced' | 'robust';
    pushback_note?: string;   // amber warning if high-confidence overridden
    rubric_scores?: Record<string, RubricScore>;  // per-archetype scores at this event
  };
}
```

### Topology File Locations
```typescript
// Source: packages/orchestration/src/openclaw/topology/storage.py (verified)
// All files live under:
// {OPENCLAW_ROOT}/workspace/.openclaw/{project_id}/topology/

const TOPOLOGY_FILES = {
  current: 'current.json',            // approved TopologyGraph
  pending: 'pending-proposals.json',  // ProposalSet (all 3 archetypes)
  changelog: 'changelog.json',        // ChangelogEntry[]
  memoryProfile: 'memory-profile.json', // archetype_affinity, threshold_status
  patterns: 'patterns.json',          // extracted structural patterns
};
```

### Edge Type Visual Mapping
```typescript
// From CONTEXT.md locked decisions — implement exactly this
export const EDGE_STYLE: Record<string, { stroke: string; strokeDasharray?: string; strokeWidth: number }> = {
  delegation:       { stroke: '#3b82f6', strokeWidth: 2 },         // solid blue
  coordination:     { stroke: '#10b981', strokeDasharray: '6 3', strokeWidth: 1.5 }, // dashed green
  escalation:       { stroke: '#f59e0b', strokeDasharray: '2 2', strokeWidth: 1.5 }, // dotted amber
  review_gate:      { stroke: '#8b5cf6', strokeWidth: 3 },          // thick purple
  information_flow: { stroke: '#6b7280', strokeDasharray: '4 4', strokeWidth: 1 }, // dashed gray
};
```

### Sidebar Nav Addition
```typescript
// Source: packages/dashboard/src/components/layout/Sidebar.tsx (established pattern)
// Add to navItems array:
{
  href: '/topology',
  label: 'Topology',
  icon: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
    </svg>
  ),
},
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `reactflow` (npm package) | `@xyflow/react` (npm package) | React Flow v12 (2024) | Must use `@xyflow/react` — old package is legacy and not React 19 compatible |
| CSS bundled in JS | Explicit CSS import required | React Flow v11+ | `import '@xyflow/react/dist/style.css'` is mandatory — easy to forget |
| Peer React 16/17 | React 18/19 supported | React Flow 12.x (2024-2025) | Project uses React 19; React Flow 12.x works |

**Deprecated/outdated:**
- `reactflow` package: superseded by `@xyflow/react`. Do not install the old name.
- `dagre-d3`: superseded by `@dagrejs/dagre`. Use the scoped package.

## Open Questions

1. **Changelog entry rubric_score availability**
   - What we know: `changelog.json` stores correction diffs and annotations; the Python approval code enriches entries with `approved_archetype`
   - What's unclear: Whether per-archetype rubric scores are stored in changelog entries (for the confidence evolution chart to have data per correction cycle)
   - Recommendation: Read `pending-proposals.json` history alongside changelog. If rubric scores are not in changelog entries, the confidence chart must reconstruct from the proposals file. Wave 0 should verify what rubric data is actually present in a real changelog entry.

2. **Changelog `annotations.rubric_scores` field**
   - What we know: `TopologyDiff.annotations` is a mutable dict; Phase 64 approval.py adds `approved_archetype` annotation
   - What's unclear: Whether `rubric_score` per archetype is serialized into changelog entries at approval time
   - Recommendation: Read `approval.py` before building the confidence chart data transformer to confirm exact field names.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 3.2.4 |
| Config file | `packages/dashboard/vitest.config.ts` |
| Quick run command | `cd packages/dashboard && pnpm test` |
| Full suite command | `cd packages/dashboard && pnpm test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOBS-01 | Topology API returns correct JSON from `current.json` and `pending-proposals.json` | unit | `cd packages/dashboard && pnpm test -- tests/topology/api.test.ts` | Wave 0 |
| TOBS-02 | Dual-panel data transformation (TopologyGraph JSON → React Flow nodes/edges) | unit | `cd packages/dashboard && pnpm test -- tests/topology/transform.test.ts` | Wave 0 |
| TOBS-03 | Changelog diff rendering (added/removed/modified display logic) | unit | `cd packages/dashboard && pnpm test -- tests/topology/diff.test.ts` | Wave 0 |
| TOBS-04 | Timeline sort order and time-travel state selection | unit | `cd packages/dashboard && pnpm test -- tests/topology/timeline.test.ts` | Wave 0 |
| TOBS-05 | Confidence chart data transformation from changelog entries | unit | `cd packages/dashboard && pnpm test -- tests/topology/confidence.test.ts` | Wave 0 |
| TOBS-06 | Multi-proposal comparison data shape (3 archetypes with rubric scores) | unit | `cd packages/dashboard && pnpm test -- tests/topology/proposals.test.ts` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd ~/Development/Tools/openrepo/packages/dashboard && pnpm test`
- **Per wave merge:** `cd ~/Development/Tools/openrepo/packages/dashboard && pnpm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/topology/api.test.ts` — API route data reading (TOBS-01, TOBS-02)
- [ ] `tests/topology/transform.test.ts` — TopologyGraph JSON to React Flow node/edge conversion (TOBS-01, TOBS-02)
- [ ] `tests/topology/diff.test.ts` — Diff highlight classification logic (TOBS-03)
- [ ] `tests/topology/timeline.test.ts` — Changelog sort and time-travel state (TOBS-04)
- [ ] `tests/topology/confidence.test.ts` — Confidence score data transformation (TOBS-05)
- [ ] `tests/topology/proposals.test.ts` — ProposalSet parsing and archetype access (TOBS-06)

Note: React Flow and Recharts component rendering tests are manual-only (browser visual verification). The unit tests above cover data transformation and API logic which are fully testable in a Node environment.

## Sources

### Primary (HIGH confidence)
- Verified from source: `packages/orchestration/src/openclaw/topology/models.py` — TopologyNode, TopologyEdge, TopologyGraph serialization format
- Verified from source: `packages/orchestration/src/openclaw/topology/storage.py` — file paths, file names, all topology file functions
- Verified from source: `packages/orchestration/src/openclaw/topology/proposal_models.py` — RubricScore (7 dimensions), TopologyProposal, ProposalSet
- Verified from source: `packages/orchestration/src/openclaw/topology/diff.py` — TopologyDiff fields (added/removed/modified nodes and edges)
- Verified from source: `packages/orchestration/src/openclaw/topology/memory.py` — MemoryProfiler, archetype_affinity, memory-profile.json schema
- Verified from source: `packages/dashboard/package.json` — recharts 3.7.0, swr 2.4.0, lucide-react 0.575.0 confirmed; @xyflow/react NOT present
- Verified from source: `packages/dashboard/src/app/api/metrics/route.ts` — withAuth pattern, searchParams.get('project'), async file reads
- Verified from source: `packages/dashboard/src/components/layout/Sidebar.tsx` — navItems pattern, nav link structure
- Verified from source: `packages/dashboard/vitest.config.ts` — Vitest 3.2.4, `tests/**/*.test.ts` glob pattern
- [React Flow docs](https://reactflow.dev/learn/getting-started/installation-and-requirements) — package name `@xyflow/react`, CSS import requirement, parent container sizing
- [React Flow dagre example](https://reactflow.dev/examples/layout/dagre) — `getLayoutedElements` function, dagre `TB` direction, node positioning math

### Secondary (MEDIUM confidence)
- WebSearch confirmed: `@xyflow/react` version 12.10.x supports React 19; React Flow UI updated Oct 2025
- WebSearch confirmed: `@dagrejs/dagre` is the current scoped package name (not legacy `dagre`)
- [React Flow layouting overview](https://reactflow.dev/learn/layouting/layouting) — dagre recommended for simple tree/DAG layouts, ~40KB bundle

### Tertiary (LOW confidence)
- Changelog `annotations.rubric_scores` field presence — inferred from Phase 64 code but not verified by reading `approval.py` directly. The open question in this research document flags this for Wave 0 investigation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from package.json and official docs
- Architecture: HIGH — data models verified from Python source; dashboard patterns verified from existing code
- Pitfalls: HIGH — React Flow CSS/container pitfalls verified from official docs; empty-state pitfall verified from storage.py (files are created on demand)
- Validation architecture: HIGH — vitest config verified from vitest.config.ts; test structure follows existing tests/ directory pattern

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable libraries; React Flow and Recharts APIs change slowly)
