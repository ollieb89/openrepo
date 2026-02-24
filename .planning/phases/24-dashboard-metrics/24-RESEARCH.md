# Phase 24: Dashboard Metrics - Research

**Researched:** 2026-02-24
**Domain:** Next.js 14 / React 18 dashboard — charting, agent tree refinement, metrics API, SWR polling
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Task completion times: **bar chart** (last N tasks, vertical bars showing duration per task)
- Pool utilization: **radial gauge** — circular progress ring with color shift green→yellow→red
- Container lifecycle counts: **compact stat cards** — row of small color-coded cards (count + label)
- Use a **lightweight charting library** (recharts or chart.js), not hand-built CSS/SVG
- Agent hierarchy: **tree view** with expand/collapse — nested L1 → L2 → L3
- Global agents (no `project` field): shown in a **separate "Global" section** at top with badge
- **Status indicator dots** next to each agent: green=idle, yellow=busy, gray=offline (from task state)
- **Instant swap** on project switch — no transition animation, SWR handles data fetch
- Metrics live on a **dedicated new tab/page** in the dashboard navigation
- **Side-by-side layout**: agent tree left (~30%), metrics charts right (~70%)
- **Responsive**: stacks vertically on narrow screens
- **Compact stat cards** in a single row above the bar chart
- Zero completed tasks: **placeholder chart outlines** (grayed-out shapes) + centered message
- No project agents: **global-only tree** + "No agents assigned to this project" message
- Loading: **skeleton loaders** — pulsing gray shapes matching chart dimensions
- API errors: **inline error card** — "Couldn't load metrics. Retry?" with retry button

### Claude's Discretion
- Exact charting library choice (recharts vs chart.js vs similar)
- Bar chart orientation (horizontal vs vertical)
- Radial gauge styling details (ring thickness, color thresholds)
- Typography and spacing to match existing dashboard theme
- Number of tasks shown in "last N tasks" bar chart (10–20 range)
- SWR polling interval for metrics refresh

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSH-09 | Agent hierarchy view filters by selected project, showing only relevant L2/L3 agents | `useAgents(projectId)` already filters by project; need to split global vs project agents into two visual sections with status dots derived from `useTasks` |
| DSH-10 | Usage metrics panel shows task completion times, pool utilization, and container lifecycle stats | `getTaskState()` already returns tasks with `completed_at`, `container_started_at`, `retry_count` metrics; need new `/api/metrics` route + recharts visualizations |
</phase_requirements>

---

## Summary

Phase 24 is a pure frontend/API expansion on an already solid foundation. The occc dashboard (`workspace/occc/`) is Next.js 14 with React 18, Tailwind CSS 3, SWR 2, and TypeScript. The existing pattern — SWR hook + Next.js API route reading state JSON — directly applies. No new infrastructure is needed: the state engine already writes `container_started_at`, `completed_at`, and `retry_count` per task via `set_task_metric()` in `pool.py`. The API layer just needs to aggregate that into a metrics shape.

The primary new work is: (1) a `/api/metrics?project=` route that computes completion durations, container lifecycle counts, and reads live pool utilization from the state file; (2) a `/metrics` page in the Next.js app with a side-by-side layout; (3) recharts `BarChart` for task durations and `RadialBarChart` for pool utilization; (4) compact stat cards using Tailwind; (5) enhancing `AgentTree` to split global vs project agents and add status dots.

**Primary recommendation:** Use recharts (already chosen as the ecosystem standard for React+D3, HIGH reputation in Context7). It is `'use client'` compatible and works naturally with Next.js App Router — just wrap charts in a client component. Install with `bun add recharts`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| recharts | ^2.x / ^3.x | BarChart + RadialBarChart visualizations | React+D3 declarative charts, 112 code snippets in Context7, HIGH reputation, no Canvas — pure SVG |
| swr | ^2.4.0 (already installed) | Polling metrics refresh | Already used for `/api/tasks` and `/api/agents`; `refreshInterval` for live updates |
| tailwindcss | ^3.4.0 (already installed) | Skeleton loaders, stat cards, layout | Already the styling system |
| react | ^18 (already installed) | Component state (expand/collapse tree) | Project baseline |
| next | 14.2.5 (already installed) | New `/metrics` route + `/api/metrics` route | Project baseline |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| recharts `Cell` | (part of recharts) | Per-bar conditional fill colors | Not needed for simple bar chart but available if color-coding by status |
| recharts `Tooltip` | (part of recharts) | On-hover value labels for bar chart | Always include — shows raw ms values |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| recharts | chart.js + react-chartjs-2 | chart.js uses Canvas (harder to style with Tailwind dark mode); recharts SVG integrates naturally |
| recharts RadialBarChart | Pure CSS `conic-gradient` ring | CSS approach is simpler but less accessible; recharts gives consistent theming with the bar chart |
| recharts RadialBarChart | Custom SVG `<circle>` stroke-dasharray | Works but hand-rolled — exactly what the user said to avoid |

**Installation:**
```bash
bun add recharts
```

---

## Architecture Patterns

### Recommended Project Structure
```
workspace/occc/src/
├── app/
│   ├── metrics/
│   │   └── page.tsx              # New: /metrics page (side-by-side layout)
│   └── api/
│       └── metrics/
│           └── route.ts          # New: GET /api/metrics?project=
├── components/
│   ├── agents/
│   │   ├── AgentTree.tsx         # Modify: split global/project sections + status dots
│   │   └── AgentCard.tsx         # Modify: add status dot prop
│   └── metrics/                  # New directory
│       ├── CompletionBarChart.tsx
│       ├── PoolGauge.tsx
│       ├── LifecycleStatCards.tsx
│       ├── MetricsSkeleton.tsx
│       └── MetricsErrorCard.tsx
└── lib/
    └── hooks/
        └── useMetrics.ts         # New: SWR hook for /api/metrics
```

### Pattern 1: Metrics API Route — Compute on Read
**What:** GET `/api/metrics?project=` reads `workspace-state.json` for the given project, computes completion durations in seconds from `completed_at - container_started_at` per task, counts lifecycle states, and returns a JSON payload ready for recharts.
**When to use:** Metrics are derived from existing state data — no separate metrics store needed.
**Example:**
```typescript
// Source: inferred from existing /api/tasks/route.ts pattern in codebase
import { NextRequest } from 'next/server';
import { getTaskState, getActiveProjectId } from '@/lib/openclaw';
import type { Task } from '@/lib/types';

function computeMetrics(tasks: Task[]) {
  const completed = tasks.filter(t => t.status === 'completed');
  // Duration from metrics fields stamped by pool.py
  const durations = completed
    .filter(t => (t as any).completed_at && (t as any).container_started_at)
    .map(t => ({
      id: t.id,
      durationS: Math.round(((t as any).completed_at - (t as any).container_started_at) * 10) / 10,
    }))
    .slice(-15); // last 15 tasks

  const byStatus = (status: string) => tasks.filter(t => t.status === status).length;

  return {
    completionDurations: durations,
    lifecycle: {
      pending:    byStatus('pending'),
      in_progress: byStatus('in_progress') + byStatus('starting') + byStatus('testing'),
      completed:  byStatus('completed'),
      failed:     byStatus('failed') + byStatus('rejected'),
    },
    // Pool utilization: in_progress / max_concurrent (read from project.json l3_overrides)
    // pool_active and pool_max are passed separately from project config
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project') || await getActiveProjectId();
  const tasks = await getTaskState(projectId);
  return Response.json({ ...computeMetrics(tasks), projectId });
}
```

### Pattern 2: useMetrics SWR Hook
**What:** SWR hook following the exact same pattern as `useTasks` — project-scoped key, polling interval.
**When to use:** Every metric component on the `/metrics` page uses this single hook.
**Example:**
```typescript
// Source: modeled on /workspace/occc/src/lib/hooks/useTasks.ts
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export function useMetrics(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR(
    projectId ? `/api/metrics?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 5000 }  // 5s — metrics are less urgent than task status
  );
  return { metrics: data || null, isLoading, error, refresh: mutate };
}
```

### Pattern 3: recharts BarChart for Completion Durations
**What:** Responsive bar chart showing last N tasks' `durationS` values. X-axis = truncated task ID (or task index), Y-axis = seconds.
**When to use:** Completion durations section of the metrics panel.
**Example:**
```tsx
// Source: Context7 recharts /recharts/recharts — BarChart pattern
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

function CompletionBarChart({ data }: { data: { id: string; durationS: number }[] }) {
  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-40 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
        <div className="w-full h-full bg-gray-100 dark:bg-gray-800 rounded-lg opacity-50" />
        <p className="absolute text-sm text-gray-500 dark:text-gray-400 text-center px-4">
          No tasks completed yet. Spawn a specialist to see metrics.
        </p>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
        <XAxis dataKey="id" tick={{ fontSize: 10 }} tickFormatter={id => id.slice(-6)} />
        <YAxis unit="s" tick={{ fontSize: 10 }} />
        <Tooltip formatter={(v) => [`${v}s`, 'Duration']} />
        <Bar dataKey="durationS" fill="#3b82f6" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
```

### Pattern 4: recharts RadialBarChart for Pool Gauge
**What:** A radial bar chart used as a circular gauge. Single data entry with `value = saturation_pct`. Color shifts via a gradient or conditional fill based on threshold. `startAngle={180}` `endAngle={0}` creates a semicircular gauge; full circle with `startAngle={90}` `endAngle={-270}` for a full ring.
**When to use:** Pool utilization percentage display.
**Example:**
```tsx
// Source: Context7 recharts /recharts/recharts — RadialBarChart + ResponsiveContainer
import { RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer } from 'recharts';

function PoolGauge({ pct }: { pct: number }) {
  const color = pct >= 80 ? '#ef4444' : pct >= 50 ? '#f59e0b' : '#22c55e';
  const data = [{ value: pct, fill: color }];
  return (
    <ResponsiveContainer width="100%" height={160}>
      <RadialBarChart
        innerRadius="60%"
        outerRadius="90%"
        data={data}
        startAngle={90}
        endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
        <RadialBar dataKey="value" angleAxisId={0} background={{ fill: '#e5e7eb' }} />
      </RadialBarChart>
    </ResponsiveContainer>
  );
}
```

### Pattern 5: Pool Utilization Data Source
**What:** Pool utilization (`active / max_concurrent * 100`) cannot come purely from the state file at `/api/metrics` time — the state file tracks task status but not the live semaphore value. The practical approach: compute `active = count of tasks with status in_progress/starting/testing`, `max_concurrent = project.json l3_overrides.max_concurrent` (default 3). This gives a stateless, file-based approximation that matches what the monitor CLI does.
**When to use:** Always. The pool process is ephemeral (asyncio) so in-memory semaphore values aren't accessible from the dashboard process.
**Example:**
```typescript
// Read max_concurrent from project config (already done in project_config.py, mirrored here)
import { getProject } from '@/lib/openclaw';

async function getPoolMax(projectId: string): Promise<number> {
  const project = await getProject(projectId);
  return project?.l3_overrides?.max_concurrent ?? 3;
}
// then: saturation_pct = Math.round((activeCount / poolMax) * 100)
```

### Pattern 6: Agent Status Dots
**What:** Agent status (`idle`/`busy`/`offline`) derived from task data — not a separate API call. If any task for this project is in `in_progress`/`starting`/`testing` and the agent `id` matches `task.metadata.agent_id` (if present), mark as busy. Fallback: if no tasks are running, all agents are idle.
**When to use:** AgentCard component — status dot as a colored circle `w-2.5 h-2.5 rounded-full`.

The `Task` type's `metadata` field is `Record<string, unknown>`. Tasks created by `pool.py` don't currently stamp an `agent_id` into metadata. The simplest approach: mark L3 agents as `busy` when `active_task_count > 0` (any task running = L3 busy), L2 agents as `busy` when any task is in a non-terminal state, L1 always idle (strategic, no direct task ownership).

### Anti-Patterns to Avoid
- **SSR recharts components:** Recharts requires a browser DOM. Any component importing recharts MUST have `'use client'` at the top. Next.js App Router will throw on SSR if forgotten.
- **Wrapping recharts in a div without explicit height:** `ResponsiveContainer` with `height="100%"` needs a parent with a defined pixel height — always set `height={N}` on `ResponsiveContainer` or give the parent a Tailwind `h-XX` class.
- **Fetching pool stats from the pool process:** The pool is an asyncio Python process with in-memory state. The dashboard cannot query it directly. Use state-file-derived approximations (task status counts).
- **Project-scoped SWR key without `?project=`:** Without the project in the SWR key, SWR will return stale data from a previous project. Always use `` `/api/metrics?project=${projectId}` `` as the key.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bar chart | SVG `<rect>` elements with JS math | recharts `BarChart` | Tooltip, responsive container, axis labels, accessibility all built-in |
| Circular progress ring | CSS `conic-gradient` or SVG `stroke-dasharray` | recharts `RadialBarChart` | Consistent theming, dark mode compatibility, tooltip support |
| Skeleton loaders | Complex animated CSS | Tailwind `animate-pulse bg-gray-200 dark:bg-gray-700 rounded` on a div | One class, exact shape match to chart dimensions |
| Status color logic | Custom color utility | Inline conditional — `pct >= 80 ? '#ef4444' : pct >= 50 ? '#f59e0b' : '#22c55e'` | Three threshold values — not worth abstracting |

**Key insight:** All charts in this phase map to recharts primitives with no custom math. The data transformation (filtering completed tasks, computing duration) is trivial arithmetic on fields already in the state JSON.

---

## Common Pitfalls

### Pitfall 1: recharts `'use client'` Boundary
**What goes wrong:** Next.js App Router will error at build/runtime if a server component tries to render recharts — "You're importing a component that needs `useState`" or DOM API errors.
**Why it happens:** recharts uses browser APIs internally. App Router defaults to server components.
**How to avoid:** Add `'use client'` as the very first line of every file that imports from recharts. Keep chart components in separate files so the `'use client'` boundary is isolated.
**Warning signs:** Build error mentioning `useLayoutEffect` or `window is not defined`.

### Pitfall 2: ResponsiveContainer Height Zero
**What goes wrong:** Chart renders as a 0-height invisible element.
**Why it happens:** `ResponsiveContainer height="100%"` inherits from parent; if parent has no computed height, chart collapses.
**How to avoid:** Always use a fixed height on `ResponsiveContainer` (e.g., `height={200}`) or give the parent an explicit Tailwind height (`h-48`).
**Warning signs:** Chart appears in DOM inspector but is invisible.

### Pitfall 3: Metrics Fields Missing on Older Tasks
**What goes wrong:** `completed_at` and `container_started_at` are `undefined` for tasks created before Phase 22 instrumentation. Duration calculation produces `NaN`.
**Why it happens:** `set_task_metric()` was added in Phase 22 — older state files won't have these fields.
**How to avoid:** Filter before computing: `tasks.filter(t => t.completed_at && t.container_started_at)`. This produces an empty array (empty state shown) for pre-Phase-22 state files — correct behavior.
**Warning signs:** `NaN` in chart Y-axis values.

### Pitfall 4: SWR Key Mismatch on Project Switch
**What goes wrong:** After switching projects, the metrics panel briefly shows the previous project's data.
**Why it happens:** SWR uses the key as a cache identity — if the key doesn't include `projectId`, different projects share a cache entry.
**How to avoid:** Always include `?project=${projectId}` in the SWR key. This matches the established pattern in `useTasks`.
**Warning signs:** Metrics don't update after project selection change.

### Pitfall 5: Expand/Collapse State Survives Project Switch
**What goes wrong:** AgentTree expand/collapse state (`useState`) persists when the project changes, so a collapsed subtree for project A appears collapsed for project B.
**Why it happens:** React state in a component is only reset when the component unmounts. If `AgentTree` is always mounted, its state persists across project changes.
**How to avoid:** Key the `AgentTree` on `projectId` — `<AgentTree key={projectId} />` — forcing a fresh mount and fresh state on every project switch.
**Warning signs:** Expanded/collapsed state from previous project carries over.

---

## Code Examples

### Skeleton Loader Pattern (Tailwind)
```tsx
// Source: Tailwind CSS utility classes — established pattern in the ecosystem
function MetricsSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Stat cards row */}
      <div className="flex gap-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex-1 h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
        ))}
      </div>
      {/* Bar chart placeholder */}
      <div className="h-48 bg-gray-200 dark:bg-gray-700 rounded-lg" />
      {/* Gauge placeholder */}
      <div className="h-40 w-40 mx-auto bg-gray-200 dark:bg-gray-700 rounded-full" />
    </div>
  );
}
```

### Error Card Pattern (matches existing dashboard conventions)
```tsx
// Source: modeled on existing Card.tsx pattern in workspace/occc/src/components/common/Card.tsx
function MetricsErrorCard({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
      <p className="text-sm text-red-700 dark:text-red-300 mb-3">
        Couldn't load metrics. Retry?
      </p>
      <button
        onClick={onRetry}
        className="px-3 py-1.5 text-xs font-medium bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}
```

### Navigation Tab Addition
```tsx
// Source: workspace/occc/src/components/layout/Sidebar.tsx — add to navItems array
{
  href: '/metrics',
  label: 'Metrics',
  icon: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
    </svg>
  ),
}
```

### AgentTree Global vs Project Split
```tsx
// Source: workspace/occc/src/components/agents/AgentTree.tsx — modification pattern
// Split agents into two sections
const globalAgents = agents.filter(a => !a.project);
const projectAgents = agents.filter(a => a.project === projectId);

// Render global section first with "Global" badge header
// Render project section below with "Project" label
// Use key={projectId} on the outer AgentTree wrapper to reset expand state
```

### Stat Card Pattern
```tsx
// Source: Tailwind CSS utilities — consistent with existing StatusBadge color vocabulary
interface StatCardProps {
  label: string;
  count: number;
  colorClass: string; // e.g. 'text-green-600 dark:text-green-400'
  bgClass: string;    // e.g. 'bg-green-50 dark:bg-green-900/20'
}
function StatCard({ label, count, colorClass, bgClass }: StatCardProps) {
  return (
    <div className={`flex-1 px-3 py-2 rounded-lg ${bgClass}`}>
      <p className={`text-xl font-bold ${colorClass}`}>{count}</p>
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
    </div>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Canvas-based charts (Chart.js) | SVG-based declarative (recharts) | ~2018 | Dark mode via CSS, no canvas context management |
| Polling with `setInterval` | SWR `refreshInterval` | SWR v1 (2020) | Deduplication, cache, background revalidation |
| `pages/` router API routes | `app/` App Router route handlers | Next.js 13 | `Response.json()` instead of `res.json()` — already used in this codebase |

**Deprecated/outdated:**
- `getServerSideProps`: Not applicable in App Router — this codebase uses API routes correctly.
- `react-chartjs-2` wrapper: Still maintained but recharts is more idiomatic for React.

---

## Open Questions

1. **Pool utilization source — live vs approximated**
   - What we know: Pool semaphore is in-memory in the asyncio pool process; dashboard is a separate Next.js process. State file tracks task statuses. The Phase 22 monitor CLI already computes pool stats from state file (confirmed in STATE.md: "Monitor pool subcommand computes aggregates on-the-fly from state file").
   - What's unclear: Whether `max_concurrent` from `project.json` is the right denominator when `pool_mode=shared` (shared semaphore across projects means utilization is cross-project).
   - Recommendation: For Phase 24, use per-project denominator (`project.json l3_overrides.max_concurrent` or 3). Label it "Project Pool" utilization. Shared-mode nuance can be deferred.

2. **Agent status dot — how to map agent to active tasks**
   - What we know: `Task` objects don't currently stamp `agent_id` in metadata (pool.py uses project_id, not agent_id). Agents have `id`, `level`, `project` fields.
   - What's unclear: Can we infer L3 agent busyness from task count alone, or do we need per-agent mapping?
   - Recommendation: Simplest correct approach — mark ALL L3 agents for the project as busy when `active_task_count > 0`, idle when 0. Mark L2 as busy when any task is non-terminal. L1 always idle. This is accurate at the swarm level even if not per-agent.

3. **recharts version — v2 vs v3**
   - What we know: Context7 shows v3.2.1 and v3.3.0 as latest versions. `npm` latest is in the v2.x series as of late 2024 but v3 may have been released.
   - What's unclear: Whether the recharts v3 API differs significantly from v2 (especially `RadialBarChart`).
   - Recommendation: Install latest stable via `bun add recharts` and verify version after install. The patterns above (BarChart, RadialBarChart, ResponsiveContainer) are stable across both major versions.

---

## Validation Architecture

> workflow.nyquist_validation not set in config.json — no test framework specified. Skip automated validation section.

The config.json only defines `workflow.research: true` and preferences. No `nyquist_validation` key found. Testing is therefore manual (browser inspection).

**Manual validation checklist per requirement:**
- DSH-09: Switch project in header selector → agent tree updates, global agents remain, project agents swap
- DSH-10: `/metrics` page loads → bar chart shows last N completed tasks, gauge shows utilization %, stat cards show lifecycle counts; all refresh without page reload

---

## Sources

### Primary (HIGH confidence)
- Context7 `/recharts/recharts` — BarChart, ResponsiveContainer, RadialBarChart, Cell patterns
- Context7 `/vercel/swr` — refreshInterval, conditional key, isLoading/error patterns
- Codebase direct read — `workspace/occc/src/` (types.ts, openclaw.ts, hooks/, components/, API routes)
- Codebase direct read — `skills/spawn_specialist/pool.py` — confirmed `container_started_at`, `completed_at`, `retry_count`, `lock_wait_ms` stamped via `set_task_metric()`

### Secondary (MEDIUM confidence)
- STATE.md accumulated decisions — confirmed monitor pool stats computed from state file (Phase 22 decision)
- CONTEXT.md phase decisions — all visualization choices locked

### Tertiary (LOW confidence)
- recharts v3 API stability — verified by Context7 snippets but exact version boundary not confirmed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — recharts confirmed via Context7 (112 snippets, HIGH reputation); SWR already in project; Tailwind already in project
- Architecture: HIGH — data shape confirmed by reading actual pool.py and state_engine.py source; API route pattern confirmed by reading existing routes
- Pitfalls: HIGH — `'use client'` requirement for recharts is documented; other pitfalls derived from codebase analysis (SWR key pattern, React key for state reset)

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (recharts API stable; SWR stable; Next.js 14 LTS)
