# Dashboard Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stabilize the OpenClaw OCCC dashboard (fix all errors, stale data, and broken pages), then add real-time agent monitoring, end-to-end task visibility, and in-app alerting.

**Architecture:** Three sequential phases — Audit (discover all bugs), Fix (repair by priority), Feature (add monitoring, task drill-down, and alerts on top of a stable foundation). All features reuse existing infrastructure (SWR, SSE via useLiveEvents, Dockerode, react-toastify).

**Tech Stack:** Next.js 15 App Router, React 19, TypeScript, SWR, Tailwind CSS, Vitest, react-toastify, Dockerode, Recharts, @xyflow/react

---

## Phase 1: Audit

The goal of Phase 1 is to produce `AUDIT.md` — a complete, prioritized list of every broken thing in the dashboard. Do NOT fix anything during Phase 1. Just document.

---

### Task 1: TypeScript & Build Audit

**Files:**
- Create: `AUDIT.md` (at repo root)

**Step 1: Run TypeScript check**

```bash
cd packages/dashboard
npx tsc --noEmit 2>&1 | tee /tmp/ts-errors.txt
echo "Exit code: $?"
```

Expected: Either 0 (clean) or a list of type errors. Copy all errors into `AUDIT.md`.

**Step 2: Run Next.js build**

```bash
cd packages/dashboard
npm run build 2>&1 | tee /tmp/build-errors.txt
```

Expected: Either successful build or errors. Copy all build errors into `AUDIT.md`.

**Step 3: Run existing tests**

```bash
cd packages/dashboard
npm run test 2>&1 | tee /tmp/test-results.txt
```

Expected: Pass/fail summary. Note any failing tests in `AUDIT.md`.

**Step 4: Run ESLint**

```bash
cd packages/dashboard
npm run lint 2>&1 | tee /tmp/lint-errors.txt
```

Note any errors (not warnings) in `AUDIT.md`.

**Step 5: Write initial AUDIT.md**

Create `AUDIT.md` at repo root with this structure:

```markdown
# Dashboard Audit

**Date:** YYYY-MM-DD

## Build & Type Errors
[paste tsc and next build errors here]

## Failing Tests
[paste test failures here]

## Lint Errors
[paste lint errors here]

## API Issues
[to be filled in Task 2]

## Page Issues
[to be filled in Task 3]

## SSE / Real-time Issues
[to be filled in Task 4]

## Priority Classification
### P1: Crashes / Errors (blockers)

### P2: Stale or Wrong Data

### P3: Cosmetic / Minor
```

**Step 6: Commit**

```bash
git add AUDIT.md
git commit -m "chore: initialize dashboard audit log"
```

---

### Task 2: API Route Sweep

Test every API endpoint. The dev server must be running.

**Step 1: Start the dev server**

```bash
cd packages/dashboard
cp .env.example .env.local  # if .env.local doesn't exist
npm run dev &
sleep 5
curl -s http://localhost:6987/api/health | python3 -m json.tool
```

If health returns 200, proceed. If not, note the startup error in AUDIT.md and investigate `packages/dashboard/src/app/api/health/route.ts`.

**Step 2: Test each API endpoint**

Run each curl below and note: status code, response shape, and whether data is present or empty. Mark any that return 4xx/5xx or empty `{}` as P1 or P2 in AUDIT.md.

```bash
BASE="http://localhost:6987"

# Health
curl -s -o /dev/null -w "%{http_code} /api/health\n" $BASE/api/health
curl -s -o /dev/null -w "%{http_code} /api/health/gateway\n" $BASE/api/health/gateway
curl -s -o /dev/null -w "%{http_code} /api/health/filesystem\n" $BASE/api/health/filesystem
curl -s -o /dev/null -w "%{http_code} /api/health/memory\n" $BASE/api/health/memory

# Projects
curl -s -o /dev/null -w "%{http_code} /api/projects\n" $BASE/api/projects
curl -s -o /dev/null -w "%{http_code} /api/projects/active\n" $BASE/api/projects/active

# Tasks
curl -s -o /dev/null -w "%{http_code} /api/tasks\n" $BASE/api/tasks

# Agents
curl -s -o /dev/null -w "%{http_code} /api/agents\n" $BASE/api/agents

# Decisions
curl -s -o /dev/null -w "%{http_code} /api/decisions\n" $BASE/api/decisions

# Metrics
curl -s -o /dev/null -w "%{http_code} /api/metrics\n" $BASE/api/metrics
curl -s -o /dev/null -w "%{http_code} /api/metrics/summary\n" $BASE/api/metrics/summary
curl -s -o /dev/null -w "%{http_code} /api/metrics/agents\n" $BASE/api/metrics/agents
curl -s -o /dev/null -w "%{http_code} /api/metrics/distribution\n" $BASE/api/metrics/distribution
curl -s -o /dev/null -w "%{http_code} /api/metrics/trends\n" $BASE/api/metrics/trends

# Pipeline
curl -s -o /dev/null -w "%{http_code} /api/pipeline\n" $BASE/api/pipeline

# Events
curl -s -o /dev/null -w "%{http_code} /api/events/latest\n" $BASE/api/events/latest

# Suggestions
curl -s -o /dev/null -w "%{http_code} /api/suggestions\n" $BASE/api/suggestions

# Memory
curl -s -o /dev/null -w "%{http_code} /api/memory\n" $BASE/api/memory

# Topology
curl -s -o /dev/null -w "%{http_code} /api/topology\n" $BASE/api/topology

# Swarm
curl -s -o /dev/null -w "%{http_code} /api/swarm/stream\n" $BASE/api/swarm/stream

# Connectors
curl -s -o /dev/null -w "%{http_code} /api/connectors\n" $BASE/api/connectors
curl -s -o /dev/null -w "%{http_code} /api/connectors/health\n" $BASE/api/connectors/health

# Config
curl -s -o /dev/null -w "%{http_code} /api/config/gateway\n" $BASE/api/config/gateway

# Graph
curl -s -o /dev/null -w "%{http_code} /api/graph/ripple-effects\n" $BASE/api/graph/ripple-effects
```

**Step 3: For any 500 errors — read the route handler**

For each 500 error, read the corresponding `route.ts` file and look for:
- Missing env vars or config reads
- File system reads that assume paths exist
- Python subprocess calls that may fail silently

Note the root cause in `AUDIT.md` under **API Issues**.

**Step 4: Update AUDIT.md with API findings**

For each broken endpoint, write:
```
- /api/[route]: [status code] — [root cause] — [P1/P2/P3]
```

**Step 5: Commit**

```bash
git add AUDIT.md
git commit -m "chore: document API audit findings"
```

---

### Task 3: Page-by-Page Walkthrough

With dev server running, visit each page in the browser (or use curl to check for render errors in server components). Check browser console for errors.

**Pages to check** (visit each, note any console errors or blank/broken sections):

| Page | URL | What to check |
|------|-----|---------------|
| Home | `/` | Inference preview loads, decisions show |
| Mission Control | `/mission-control` | SwarmStatusPanel, AttentionQueue, LiveEventFeed, TaskPulse all render |
| Tasks | `/tasks` | TaskBoard shows tasks, terminal panel opens |
| Metrics | `/metrics` | Charts render, PipelineSection loads |
| Memory | `/memory` | MemoryPanel shows entries, search works |
| Topology | `/topology` | Graph renders, node detail panel works |
| Decisions | `/decisions` | Decision history loads |
| Agents | `/agents` | Agent tree renders |
| Escalations | `/escalations` | Escalation list loads |
| Suggestions | `/suggestions` | Suggestions list loads |
| Catch-up | `/catch-up` | Sync status shows |
| Settings | `/settings` | Settings page renders |
| Environment | `/environment` | Environment info renders |
| Containers | `/containers` | Container list renders |

**For each page, note in AUDIT.md:**
- Does it render without errors?
- Are there console errors?
- Is data showing or is it empty/loading forever?

**Step 2: Update AUDIT.md with page findings**

**Step 3: Commit**

```bash
git add AUDIT.md
git commit -m "chore: document page walkthrough audit findings"
```

---

### Task 4: SSE & Real-time Audit

**Files to read:**
- `packages/dashboard/src/lib/hooks/useLiveEvents.ts`
- `packages/dashboard/src/app/api/events/route.ts`
- `packages/dashboard/src/app/api/events/latest/route.ts`

**Step 1: Read useLiveEvents**

```bash
cat packages/dashboard/src/lib/hooks/useLiveEvents.ts
```

Look for:
- The EventSource URL — does it match `/api/events`?
- The fallback SWR URL — does it match `/api/events/latest`?
- The 4000ms offline timeout — is it still correct?
- Any hardcoded project IDs or stale filters

**Step 2: Test the SSE endpoint directly**

```bash
curl -N -H "Accept: text/event-stream" http://localhost:6987/api/events &
sleep 3
kill %1
```

Does it connect and stream? Or does it immediately close?

**Step 3: Test the fallback polling endpoint**

```bash
curl -s http://localhost:6987/api/events/latest | python3 -m json.tool
```

Does it return `{ events: [...] }` or error?

**Step 4: Note findings in AUDIT.md**

Document:
- Whether SSE connects successfully
- Whether fallback polling works
- Any connection errors

**Step 5: Commit AUDIT.md final state**

```bash
git add AUDIT.md
git commit -m "chore: complete dashboard audit — SSE and real-time findings"
```

---

## Phase 2: Fix

Phase 2 fixes are driven by the AUDIT.md output. This section provides the process for each priority level. For each bug:
1. Read the relevant file(s)
2. Write a failing test (if testable)
3. Fix the code
4. Verify the fix
5. Commit

The general fix workflow for each issue:

---

### Task 5: Fix P1 — Crashes & Errors

Work through every P1 item in AUDIT.md. For each:

**Step 1: Read the broken file**

```bash
cat packages/dashboard/src/app/api/[route]/route.ts
```

**Step 2: Identify the root cause**

Common patterns:
- `fs.readFileSync` without existence check → wrap with `safeReadJson` from `lib/fs-utils.ts`
- Missing env var → add a fallback or early return with clear error message
- Python subprocess failure → check error handling around `execFileSync`/`spawn`

**Step 3: Write a test for the fix (if the bug is in an API route)**

Tests live in `packages/dashboard/tests/`. Follow existing test patterns.

```bash
# Example: run a specific test file
cd packages/dashboard
npx vitest run tests/[relevant-test-file].test.ts
```

**Step 4: Apply the fix**

Make the minimal change to fix the issue. Do not refactor surrounding code.

**Step 5: Verify**

```bash
# Re-test the endpoint
curl -s http://localhost:6987/api/[route] | python3 -m json.tool

# Run tests
cd packages/dashboard && npm run test
```

**Step 6: Commit each fix separately**

```bash
git add packages/dashboard/src/app/api/[route]/route.ts
git commit -m "fix: [brief description of what was broken]"
```

**Step 7: Update AUDIT.md — mark item as fixed**

---

### Task 6: Fix P2 — Stale or Wrong Data

Work through every P2 item in AUDIT.md. For each:

**Step 1: Trace the data flow**

For a page showing stale data:
1. Identify which SWR hook is used (check the page component)
2. Find the hook in `packages/dashboard/src/lib/hooks/`
3. Identify the API endpoint the hook calls
4. Check that endpoint returns fresh data

**Step 2: Common P2 patterns and fixes**

*SWR fetching from wrong endpoint:*
```typescript
// In the hook, check the fetcher URL
const { data } = useSWR('/api/correct-endpoint', fetcher, {
  refreshInterval: 5000,  // Add refresh if missing
})
```

*API returns stale file cache:*
Check `packages/dashboard/src/lib/fs-utils.ts` — look for mtime checks and cache invalidation.

*ProjectContext not applied:*
Check that the hook passes the active project ID as a query param:
```typescript
const { projectId } = useProject()
const { data } = useSWR(projectId ? `/api/tasks?project=${projectId}` : null, fetcher)
```

**Step 3: Verify data is now fresh**

Re-run the curl for the endpoint and confirm it returns expected data.

**Step 4: Commit each fix**

```bash
git commit -m "fix: [stale data description]"
```

---

### Task 7: Fix P3 — Stability & Hardening

Work through every P3 item in AUDIT.md.

**Step 1: Silent error swallowing in metrics API**

Read `packages/dashboard/src/app/api/metrics/route.ts`. Find where Python snapshot failures are caught silently. Add an explicit error state to the response:

```typescript
// Before (silent):
try {
  snapshot = readSnapshot()
} catch {
  // nothing
}

// After (visible):
try {
  snapshot = readSnapshot()
} catch (err) {
  snapshotError = err instanceof Error ? err.message : 'unknown error'
}

return NextResponse.json({
  ...metrics,
  meta: { snapshot_missing: !snapshot, snapshot_error: snapshotError }
})
```

**Step 2: Dark mode consistency**

For any components with broken dark mode, check Tailwind `dark:` classes are applied consistently. Pattern to follow:

```tsx
// Consistent pattern used throughout:
className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
```

**Step 3: Run full test suite**

```bash
cd packages/dashboard && npm run test
```

All tests should pass.

**Step 4: Commit**

```bash
git commit -m "fix: improve error visibility and dark mode consistency"
```

---

## Phase 3: Features

Phase 3 adds three new capabilities on top of the stable, audited foundation.

---

### Task 8: Real-time Agent Monitoring — Container Metrics

Extend `SwarmStatusPanel` to show live container-level metrics (CPU %, memory MB) for each running L3 container.

**Files:**
- Modify: `packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx`
- Modify: `packages/dashboard/src/app/api/swarm/stream/route.ts` (or create `/api/agents/containers/route.ts`)
- Test: `packages/dashboard/tests/components/swarm-status-panel.test.ts` (create if missing)

**Step 1: Understand the existing Dockerode integration**

```bash
cat packages/dashboard/src/lib/docker.ts
```

Note: what functions exist for listing containers and getting stats?

**Step 2: Create (or verify) a containers API endpoint**

Check `packages/dashboard/src/app/api/containers/` — if no route.ts exists, create one:

```typescript
// packages/dashboard/src/app/api/containers/route.ts
import { NextResponse } from 'next/server'
import { listContainers } from '@/lib/docker'

export async function GET() {
  try {
    const containers = await listContainers()
    return NextResponse.json({ containers })
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'docker unavailable' },
      { status: 503 }
    )
  }
}
```

**Step 3: Write a failing test**

```typescript
// packages/dashboard/tests/api/containers.test.ts
import { describe, it, expect, vi } from 'vitest'

vi.mock('@/lib/docker', () => ({
  listContainers: vi.fn().mockResolvedValue([
    { id: 'abc123', name: 'openclaw-proj-l3-task1', cpu_percent: 12.5, memory_mb: 256 }
  ])
}))

describe('GET /api/containers', () => {
  it('returns container list with metrics', async () => {
    const { GET } = await import('@/app/api/containers/route')
    const res = await GET()
    const data = await res.json()
    expect(data.containers).toHaveLength(1)
    expect(data.containers[0]).toHaveProperty('cpu_percent')
  })
})
```

**Step 4: Run test to verify it fails**

```bash
cd packages/dashboard && npx vitest run tests/api/containers.test.ts
```

Expected: FAIL (route doesn't exist yet or docker mock not wired)

**Step 5: Implement the route**

Create or update `packages/dashboard/src/app/api/containers/route.ts` as shown in Step 2.

**Step 6: Add a `useContainers` SWR hook**

```typescript
// packages/dashboard/src/lib/hooks/useContainers.ts
import useSWR from 'swr'
import { apiJson } from '@/lib/api-client'

export function useContainers() {
  const { data, error, isLoading } = useSWR(
    '/api/containers',
    apiJson,
    { refreshInterval: 3000 }
  )
  return {
    containers: data?.containers ?? [],
    error,
    isLoading,
  }
}
```

**Step 7: Extend SwarmStatusPanel**

Read the current `SwarmStatusPanel.tsx`, then add a container metrics section below the agent hierarchy:

```tsx
// Inside SwarmStatusPanel
const { containers } = useContainers()

// In JSX, add after existing content:
{containers.length > 0 && (
  <div className="mt-4">
    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
      Active Containers
    </h3>
    <div className="space-y-1">
      {containers.map(c => (
        <div key={c.id} className="flex items-center justify-between text-xs">
          <span className="text-gray-700 dark:text-gray-300 truncate">{c.name}</span>
          <span className="text-gray-500 dark:text-gray-400 ml-2 shrink-0">
            {c.cpu_percent.toFixed(1)}% CPU · {c.memory_mb}MB
          </span>
        </div>
      ))}
    </div>
  </div>
)}
```

**Step 8: Run tests**

```bash
cd packages/dashboard && npm run test
```

**Step 9: Commit**

```bash
git add packages/dashboard/src/app/api/containers/route.ts \
        packages/dashboard/src/lib/hooks/useContainers.ts \
        packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx \
        packages/dashboard/tests/api/containers.test.ts
git commit -m "feat: add live container metrics to SwarmStatusPanel"
```

---

### Task 9: End-to-End Task Visibility — Task Detail Drill-Down

Add a task detail panel to the Tasks page showing a task's full journey: L1 dispatch → L2 assignment → L3 execution → completion, with logs and branch info.

**Files:**
- Read: `packages/dashboard/src/components/tasks/TaskCard.tsx`
- Read: `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx`
- Modify: `packages/dashboard/src/app/api/tasks/[id]/route.ts`
- Create: `packages/dashboard/src/components/tasks/TaskJourneyPanel.tsx`
- Test: `packages/dashboard/tests/components/task-journey-panel.test.ts`

**Step 1: Read the existing task detail API**

```bash
cat packages/dashboard/src/app/api/tasks/[id]/route.ts
```

Note what fields the task object includes. We need: `stage`, `assigned_agent`, `l3_branch`, `created_at`, `started_at`, `completed_at`, `logs`.

**Step 2: Extend the task detail API if fields are missing**

If the task response is missing journey fields, extend the route handler to include them from the state engine snapshot:

```typescript
// In tasks/[id]/route.ts, add to the response:
return NextResponse.json({
  ...task,
  journey: {
    dispatched_at: task.created_at,
    assigned_at: task.started_at,
    branch: task.l3_branch ?? null,
    completed_at: task.completed_at ?? null,
    stage: task.stage ?? 'unknown',
  }
})
```

**Step 3: Write a failing test for TaskJourneyPanel**

```typescript
// packages/dashboard/tests/components/task-journey-panel.test.ts
import { render, screen } from '@testing-library/react'
import { TaskJourneyPanel } from '@/components/tasks/TaskJourneyPanel'

const mockTask = {
  id: 'task-1',
  journey: {
    dispatched_at: '2026-03-06T10:00:00Z',
    assigned_at: '2026-03-06T10:00:05Z',
    branch: 'l3/task-task-1',
    completed_at: '2026-03-06T10:05:00Z',
    stage: 'completed',
  }
}

describe('TaskJourneyPanel', () => {
  it('renders journey stages', () => {
    render(<TaskJourneyPanel task={mockTask} />)
    expect(screen.getByText('L1 Dispatch')).toBeInTheDocument()
    expect(screen.getByText('L3 Execution')).toBeInTheDocument()
    expect(screen.getByText('l3/task-task-1')).toBeInTheDocument()
  })
})
```

**Step 4: Run test to verify it fails**

```bash
cd packages/dashboard && npx vitest run tests/components/task-journey-panel.test.ts
```

**Step 5: Create TaskJourneyPanel component**

```typescript
// packages/dashboard/src/components/tasks/TaskJourneyPanel.tsx
'use client'

type JourneyStage = {
  label: string
  time: string | null
  detail?: string
}

type Props = {
  task: {
    id: string
    journey: {
      dispatched_at: string
      assigned_at: string | null
      branch: string | null
      completed_at: string | null
      stage: string
    }
  }
}

function fmt(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString()
}

export function TaskJourneyPanel({ task }: Props) {
  const { journey } = task
  const stages: JourneyStage[] = [
    { label: 'L1 Dispatch', time: fmt(journey.dispatched_at) },
    { label: 'L2 Assignment', time: fmt(journey.assigned_at) },
    { label: 'L3 Execution', time: fmt(journey.assigned_at), detail: journey.branch ?? undefined },
    { label: 'Completion', time: fmt(journey.completed_at) },
  ]

  return (
    <div className="p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        Task Journey
      </h3>
      <ol className="space-y-3">
        {stages.map((s, i) => (
          <li key={i} className="flex items-start gap-3">
            <span className="mt-0.5 w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-xs text-indigo-700 dark:text-indigo-300 shrink-0">
              {i + 1}
            </span>
            <div>
              <div className="text-xs font-medium text-gray-700 dark:text-gray-300">{s.label}</div>
              <div className="text-xs text-gray-500 dark:text-gray-400">{s.time}</div>
              {s.detail && (
                <div className="mt-0.5 text-xs font-mono text-indigo-600 dark:text-indigo-400">{s.detail}</div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
```

**Step 6: Wire TaskJourneyPanel into the Tasks page**

Read `packages/dashboard/src/app/tasks/page.tsx`. Find where `TaskTerminalPanel` is rendered (it's shown when a task is selected). Add `TaskJourneyPanel` below it:

```tsx
import { TaskJourneyPanel } from '@/components/tasks/TaskJourneyPanel'

// In the JSX, after TaskTerminalPanel:
{selectedTask?.journey && (
  <TaskJourneyPanel task={selectedTask} />
)}
```

**Step 7: Run all tests**

```bash
cd packages/dashboard && npm run test
```

**Step 8: Commit**

```bash
git add packages/dashboard/src/components/tasks/TaskJourneyPanel.tsx \
        packages/dashboard/src/app/tasks/page.tsx \
        packages/dashboard/tests/components/task-journey-panel.test.ts
git commit -m "feat: add end-to-end task journey panel"
```

---

### Task 10: In-App Alerting

Add an alert feed for agent failures, escalations, task timeouts, and API errors. Extend existing LiveEventFeed + AttentionQueue infrastructure. Add toasts for urgent events.

**Files:**
- Read: `packages/dashboard/src/lib/hooks/useLiveEvents.ts`
- Read: `packages/dashboard/src/components/mission-control/LiveEventFeed.tsx`
- Create: `packages/dashboard/src/lib/hooks/useAlerts.ts`
- Create: `packages/dashboard/src/components/common/AlertFeed.tsx`
- Modify: `packages/dashboard/src/app/layout.tsx` (add toast provider if missing)
- Test: `packages/dashboard/tests/components/alert-feed.test.ts`

**Step 1: Read LiveEventFeed and useLiveEvents**

```bash
cat packages/dashboard/src/lib/hooks/useLiveEvents.ts
cat packages/dashboard/src/components/mission-control/LiveEventFeed.tsx
```

Note the event shape (type, message, timestamp, project_id, severity).

**Step 2: Create useAlerts hook**

```typescript
// packages/dashboard/src/lib/hooks/useAlerts.ts
'use client'
import { useLiveEvents } from './useLiveEvents'
import { useMemo } from 'react'

const ALERT_EVENT_TYPES = ['agent_failure', 'escalation', 'task_timeout', 'api_error']

export type Alert = {
  id: string
  type: string
  message: string
  timestamp: string
  severity: 'critical' | 'warning' | 'info'
}

export function useAlerts(projectId?: string) {
  const { events } = useLiveEvents(projectId)

  const alerts = useMemo(() =>
    events
      .filter(e => ALERT_EVENT_TYPES.includes(e.type))
      .map(e => ({
        id: e.id,
        type: e.type,
        message: e.message,
        timestamp: e.timestamp,
        severity: e.type === 'agent_failure' || e.type === 'escalation'
          ? 'critical' as const
          : 'warning' as const,
      })),
    [events]
  )

  return { alerts }
}
```

**Step 3: Write failing test for AlertFeed**

```typescript
// packages/dashboard/tests/components/alert-feed.test.ts
import { render, screen } from '@testing-library/react'
import { AlertFeed } from '@/components/common/AlertFeed'

const mockAlerts = [
  { id: '1', type: 'agent_failure', message: 'L3 agent crashed', timestamp: new Date().toISOString(), severity: 'critical' as const },
  { id: '2', type: 'task_timeout', message: 'Task timed out after 10m', timestamp: new Date().toISOString(), severity: 'warning' as const },
]

describe('AlertFeed', () => {
  it('renders all alerts', () => {
    render(<AlertFeed alerts={mockAlerts} />)
    expect(screen.getByText('L3 agent crashed')).toBeInTheDocument()
    expect(screen.getByText('Task timed out after 10m')).toBeInTheDocument()
  })

  it('renders empty state when no alerts', () => {
    render(<AlertFeed alerts={[]} />)
    expect(screen.getByText('No alerts')).toBeInTheDocument()
  })
})
```

**Step 4: Run test to verify it fails**

```bash
cd packages/dashboard && npx vitest run tests/components/alert-feed.test.ts
```

**Step 5: Create AlertFeed component**

```tsx
// packages/dashboard/src/components/common/AlertFeed.tsx
'use client'
import type { Alert } from '@/lib/hooks/useAlerts'

const severityStyles = {
  critical: 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200',
  warning:  'bg-yellow-50 dark:bg-yellow-950 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200',
  info:     'bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200',
}

export function AlertFeed({ alerts }: { alerts: Alert[] }) {
  if (alerts.length === 0) {
    return (
      <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-4">No alerts</p>
    )
  }

  return (
    <ul className="space-y-2">
      {alerts.map(a => (
        <li key={a.id} className={`rounded border px-3 py-2 text-xs ${severityStyles[a.severity]}`}>
          <div className="flex items-center justify-between gap-2">
            <span className="font-medium uppercase tracking-wide">{a.type.replace(/_/g, ' ')}</span>
            <span className="opacity-60">{new Date(a.timestamp).toLocaleTimeString()}</span>
          </div>
          <p className="mt-0.5 opacity-80">{a.message}</p>
        </li>
      ))}
    </ul>
  )
}
```

**Step 6: Add toast notifications for critical alerts**

Read `packages/dashboard/src/app/layout.tsx`. Add ToastContainer if not present, and wire up critical alert toasts.

```tsx
// In layout.tsx, add:
import { ToastContainer, toast } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

// Add <ToastContainer position="bottom-right" /> inside the body

// Create a client component for toast dispatch:
// packages/dashboard/src/components/common/AlertToastEmitter.tsx
'use client'
import { useEffect, useRef } from 'react'
import { toast } from 'react-toastify'
import { useAlerts } from '@/lib/hooks/useAlerts'

export function AlertToastEmitter({ projectId }: { projectId?: string }) {
  const { alerts } = useAlerts(projectId)
  const seenIds = useRef(new Set<string>())

  useEffect(() => {
    alerts.forEach(a => {
      if (a.severity === 'critical' && !seenIds.current.has(a.id)) {
        seenIds.current.add(a.id)
        toast.error(`${a.type.replace(/_/g, ' ')}: ${a.message}`, { toastId: a.id })
      }
    })
  }, [alerts])

  return null
}
```

**Step 7: Add AlertFeed to Mission Control**

Read `packages/dashboard/src/app/mission-control/page.tsx`. Add AlertFeed section:

```tsx
import { AlertFeed } from '@/components/common/AlertFeed'
import { useAlerts } from '@/lib/hooks/useAlerts'

// In the component:
const { alerts } = useAlerts(projectId)

// In JSX, add a new section:
<section>
  <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">Alerts</h2>
  <AlertFeed alerts={alerts} />
</section>
```

**Step 8: Run all tests**

```bash
cd packages/dashboard && npm run test
```

**Step 9: Commit**

```bash
git add packages/dashboard/src/lib/hooks/useAlerts.ts \
        packages/dashboard/src/components/common/AlertFeed.tsx \
        packages/dashboard/src/components/common/AlertToastEmitter.tsx \
        packages/dashboard/src/app/layout.tsx \
        packages/dashboard/src/app/mission-control/page.tsx \
        packages/dashboard/tests/components/alert-feed.test.ts
git commit -m "feat: add in-app alert feed and critical event toasts"
```

---

## Final Verification

After all tasks complete:

```bash
# Full test suite
cd packages/dashboard && npm run test

# TypeScript check
cd packages/dashboard && npx tsc --noEmit

# Build check
cd packages/dashboard && npm run build

# Spot check key pages
curl -s http://localhost:6987/api/health | python3 -m json.tool
curl -s http://localhost:6987/api/tasks | python3 -m json.tool
curl -s http://localhost:6987/api/metrics | python3 -m json.tool
```

All tests pass, no TS errors, build succeeds.
