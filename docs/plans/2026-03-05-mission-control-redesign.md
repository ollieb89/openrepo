# Mission Control Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the OpenClaw OCCC dashboard into a full mission control UI — new command center homepage, global Cmd+K command bar, terminal side drawer on the task board, and full-stack token/cost tracking.

**Architecture:** Modern SaaS aesthetic (Linear/Vercel-style). New homepage replaces the inference preview page with a 4-quadrant command center. Global command bar mounts in root layout. Terminal drawer is a right-side slide-over on the task board reusing the existing `TaskTerminalPanel`. Token tracking adds instrumentation to the Python gateway client and a new Usage tab on the metrics page.

**Tech Stack:** Next.js 15 App Router, TypeScript, Tailwind CSS, SWR, lucide-react, Python (httpx, fcntl). All API routes use `withAuth(handler)`. All client-side fetches use `apiJson()` from `@/lib/api-client` which prepends `/occc` basePath automatically.

---

## Phase 1: Command Center Homepage

### Task 1: Create mission-control component directory and SwarmStatusPanel

**Files:**
- Create: `packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx`

This panel shows the agent hierarchy, pool utilization, and today's cost summary.

**Step 1: Create the component**

```tsx
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiJson } from '@/lib/api-client';

interface SwarmStatusData {
  agents: Array<{ id: string; name: string; level: number; status?: string }>;
  poolActive: number;
  poolMax: number;
  successRate: number;
  todayCostUsd: number | null;
  todayTokens: number | null;
}

export default function SwarmStatusPanel() {
  const [data, setData] = useState<SwarmStatusData | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [agentsRes, metricsRes] = await Promise.all([
          apiJson<{ agents: Array<{ id: string; name: string; level: number }> }>('/api/agents'),
          apiJson<{ poolActive: number; poolMax: number; lifecycle: { completed: number; failed: number } }>('/api/metrics'),
        ]);
        const total = metricsRes.lifecycle.completed + metricsRes.lifecycle.failed;
        const successRate = total > 0
          ? Math.round((metricsRes.lifecycle.completed / total) * 100)
          : 100;
        setData({
          agents: agentsRes.agents,
          poolActive: metricsRes.poolActive,
          poolMax: metricsRes.poolMax,
          successRate,
          todayCostUsd: null,
          todayTokens: null,
        });
      } catch {
        // Silently degrade
      }
    }
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, []);

  const l1 = data?.agents.filter(a => a.level === 1) ?? [];
  const l2 = data?.agents.filter(a => a.level === 2) ?? [];
  const l3Active = data?.poolActive ?? 0;
  const poolMax = data?.poolMax ?? 3;
  const poolBars = Array.from({ length: poolMax }, (_, i) => i < l3Active);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        Swarm Status
      </h3>

      {/* Agent hierarchy */}
      <div className="space-y-1 text-sm">
        {l1.map(a => (
          <div key={a.id} className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
            <span className="font-mono text-gray-700 dark:text-gray-300 text-xs">{a.name}</span>
            <span className="text-xs text-gray-400">L1</span>
          </div>
        ))}
        {l2.map(a => (
          <div key={a.id} className="flex items-center gap-2 ml-4">
            <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
            <span className="font-mono text-gray-700 dark:text-gray-300 text-xs">{a.name}</span>
            <span className="text-xs text-gray-400">L2</span>
          </div>
        ))}
        <div className="flex items-center gap-2 ml-8">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${l3Active > 0 ? 'bg-amber-500' : 'bg-gray-300'}`} />
          <span className="font-mono text-gray-700 dark:text-gray-300 text-xs">L3 Specialists</span>
          <span className="text-xs text-gray-400">{l3Active}/{poolMax} active</span>
        </div>
      </div>

      {/* Pool gauge */}
      <div>
        <div className="flex gap-1 mt-1">
          {poolBars.map((active, i) => (
            <div
              key={i}
              className={`h-2 flex-1 rounded-sm ${active ? 'bg-amber-400' : 'bg-gray-200 dark:bg-gray-700'}`}
            />
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-1">Pool: {l3Active}/{poolMax}</p>
      </div>

      {/* Success rate */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500 dark:text-gray-400">Success rate</span>
        <span className="font-semibold text-gray-800 dark:text-gray-100">{data?.successRate ?? '—'}%</span>
      </div>

      {/* Cost (placeholder until token tracking is implemented) */}
      {data?.todayCostUsd != null && (
        <div className="flex items-center justify-between text-xs border-t border-gray-100 dark:border-gray-700 pt-2">
          <span className="text-gray-500 dark:text-gray-400">Today</span>
          <span className="font-mono text-gray-700 dark:text-gray-300">
            ~${data.todayCostUsd.toFixed(2)} · {(data.todayTokens! / 1_000_000).toFixed(1)}M tok
          </span>
        </div>
      )}

      <Link href="/agents" className="text-xs text-blue-600 hover:underline mt-auto">
        View agents →
      </Link>
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles (no test needed for pure UI)**

```bash
cd packages/dashboard && npx tsc --noEmit
```

Expected: No errors

**Step 3: Commit**

```bash
git add packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx
git commit -m "feat(dashboard): add SwarmStatusPanel for mission control homepage"
```

---

### Task 2: Create LiveEventFeed component

**Files:**
- Create: `packages/dashboard/src/components/mission-control/LiveEventFeed.tsx`

Reads from the existing `/api/events` SSE endpoint and renders a scrolling event list.

**Step 1: Create the component**

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { apiPath } from '@/lib/api-client';
import { useProject } from '@/context/ProjectContext';

interface FeedEvent {
  id: number;
  type: string;
  project_id?: string;
  task_id?: string;
  message?: string;
  timestamp?: number;
  rawAt: number; // Date.now() when received
}

const TYPE_COLORS: Record<string, string> = {
  task_created: 'bg-blue-500',
  task_started: 'bg-amber-500',
  task_completed: 'bg-green-500',
  task_failed: 'bg-red-500',
  task_escalated: 'bg-purple-500',
  container_started: 'bg-cyan-500',
  container_stopped: 'bg-gray-400',
  default: 'bg-gray-400',
};

function relativeTime(ms: number): string {
  const diff = Math.floor((Date.now() - ms) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function LiveEventFeed() {
  const { projectId } = useProject();
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(false);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    const url = apiPath('/api/events');
    const es = new EventSource(url, { withCredentials: false });

    es.addEventListener('message', (e) => {
      try {
        const parsed = JSON.parse(e.data);
        const entry: FeedEvent = {
          id: Date.now() + Math.random(),
          type: parsed.type ?? 'unknown',
          project_id: parsed.project_id,
          task_id: parsed.task_id,
          message: parsed.message ?? parsed.description,
          timestamp: parsed.timestamp,
          rawAt: Date.now(),
        };
        // Filter by project
        if (projectId && entry.project_id && entry.project_id !== projectId) return;
        setEvents(prev => [...prev.slice(-49), entry]);
      } catch {
        // Ignore parse errors
      }
    });

    return () => es.close();
  }, [projectId]);

  // Auto-scroll unless paused
  useEffect(() => {
    if (!paused && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, paused]);

  const displayed = filter ? events.filter(e => e.type.includes(filter)) : events;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3 min-h-0">
      <div className="flex items-center justify-between flex-shrink-0">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Live Event Feed
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFilter(prev => prev === 'task' ? null : 'task')}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${filter === 'task' ? 'bg-blue-100 border-blue-300 text-blue-700 dark:bg-blue-900 dark:border-blue-700 dark:text-blue-300' : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'}`}
          >
            tasks
          </button>
          <button
            onClick={() => setPaused(p => !p)}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${paused ? 'bg-amber-100 border-amber-300 text-amber-700' : 'border-gray-200 dark:border-gray-600 text-gray-500'}`}
          >
            {paused ? 'paused' : 'live'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1 min-h-0 max-h-48">
        {displayed.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">Waiting for events…</p>
        )}
        {displayed.map(ev => (
          <div key={ev.id} className="flex items-start gap-2 text-xs">
            <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${TYPE_COLORS[ev.type] ?? TYPE_COLORS.default}`} />
            <span className="text-gray-700 dark:text-gray-300 flex-1 truncate">
              {ev.task_id ? (
                <span className="font-mono text-gray-500">{ev.task_id} </span>
              ) : null}
              {ev.type.replace(/_/g, ' ')}
              {ev.message ? ` — ${ev.message}` : ''}
            </span>
            <span className="text-gray-400 flex-shrink-0">{relativeTime(ev.rawAt)}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
```

**Step 2: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

Expected: No errors

**Step 3: Commit**

```bash
git add packages/dashboard/src/components/mission-control/LiveEventFeed.tsx
git commit -m "feat(dashboard): add LiveEventFeed SSE component for mission control"
```

---

### Task 3: Create TaskPulse component

**Files:**
- Create: `packages/dashboard/src/components/mission-control/TaskPulse.tsx`

Shows active L3 tasks with pulsing indicators.

**Step 1: Create the component**

```tsx
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiJson } from '@/lib/api-client';
import { useProject } from '@/context/ProjectContext';
import type { Task } from '@/lib/types';

export default function TaskPulse() {
  const { projectId } = useProject();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    if (!projectId) return;
    async function load() {
      try {
        const data = await apiJson<Task[]>(`/api/tasks?project=${projectId}`);
        const all = Array.isArray(data) ? data : [];
        setTasks(all.filter(t => t.status === 'in_progress' || t.status === 'starting' || t.status === 'testing'));
        setPendingCount(all.filter(t => t.status === 'pending').length);
      } catch {
        // Silently degrade
      }
    }
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [projectId]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Task Pulse
        </h3>
        {pendingCount > 0 && (
          <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-2 py-0.5 rounded-full">
            +{pendingCount} pending
          </span>
        )}
      </div>

      <div className="space-y-2 flex-1">
        {tasks.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No active tasks</p>
        )}
        {tasks.map(task => (
          <Link
            key={task.id}
            href={`/tasks?open=${task.id}`}
            className="flex items-center gap-3 text-xs hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg px-2 py-1.5 transition-colors"
          >
            {/* Pulsing indicator */}
            <span className="relative flex-shrink-0">
              <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <span className="font-mono text-gray-500 flex-shrink-0">{task.id.slice(0, 12)}…</span>
            <span className="text-gray-700 dark:text-gray-300 truncate flex-1">
              {task.metadata?.skill_hint ?? task.status}
            </span>
          </Link>
        ))}
      </div>

      <Link href="/tasks" className="text-xs text-blue-600 hover:underline mt-auto">
        View all tasks →
      </Link>
    </div>
  );
}
```

**Step 2: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

Expected: No errors

**Step 3: Commit**

```bash
git add packages/dashboard/src/components/mission-control/TaskPulse.tsx
git commit -m "feat(dashboard): add TaskPulse component for mission control"
```

---

### Task 4: Create AttentionQueue component

**Files:**
- Create: `packages/dashboard/src/components/mission-control/AttentionQueue.tsx`

Merges escalations, decisions, and suggestions into one triage queue with inline actions.

**Step 1: Create the component**

```tsx
'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiJson } from '@/lib/api-client';
import { useProject } from '@/context/ProjectContext';

interface AttentionItem {
  id: string;
  kind: 'escalation' | 'decision' | 'suggestion';
  label: string;
  actionUrl?: string; // for suggestions/decisions
  actionPayload?: object;
  navigateTo?: string;
}

export default function AttentionQueue() {
  const { projectId } = useProject();
  const [items, setItems] = useState<AttentionItem[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [acting, setActing] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!projectId) return;
    async function load() {
      const built: AttentionItem[] = [];

      // Escalations — navigate to /escalations
      try {
        const data = await apiJson<any[]>(`/api/escalations?project=${projectId}`);
        (Array.isArray(data) ? data : []).slice(0, 3).forEach(e => {
          built.push({
            id: `esc-${e.id ?? e.task_id ?? Math.random()}`,
            kind: 'escalation',
            label: `Escalation: ${e.reason ?? e.message ?? 'confidence low'}`,
            navigateTo: '/escalations',
          });
        });
      } catch { /* ignore */ }

      // Decisions — inline dismiss or navigate
      try {
        const data = await apiJson<any[]>(`/api/decisions?projectId=${projectId}`);
        (Array.isArray(data) ? data : []).slice(0, 2).forEach(d => {
          built.push({
            id: `dec-${d.id}`,
            kind: 'decision',
            label: `Decision: ${d.summary ?? d.title ?? d.id}`,
            actionUrl: `/api/decisions/${d.id}`,
            actionPayload: { hidden: true },
          });
        });
      } catch { /* ignore */ }

      // Suggestions — inline accept/dismiss
      try {
        const data = await apiJson<any>(`/api/suggestions?project=${projectId}`);
        const suggestions = Array.isArray(data) ? data : (data?.suggestions ?? []);
        suggestions.filter((s: any) => s.status === 'pending').slice(0, 2).forEach((s: any) => {
          built.push({
            id: `sug-${s.id}`,
            kind: 'suggestion',
            label: `Suggestion: ${s.description ?? s.title ?? s.id}`,
            actionUrl: `/api/suggestions/${s.id}/action`,
            actionPayload: { action: 'accept' },
          });
        });
      } catch { /* ignore */ }

      setItems(built);
    }
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, [projectId]);

  async function handleAction(item: AttentionItem, accept: boolean) {
    setActing(prev => new Set(prev).add(item.id));
    try {
      if (item.actionUrl) {
        if (item.kind === 'suggestion') {
          await apiJson(item.actionUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: accept ? 'accept' : 'dismiss' }),
          });
        } else if (item.kind === 'decision') {
          await apiJson(item.actionUrl, {
            method: 'DELETE',
          });
        }
      }
      setDismissed(prev => new Set(prev).add(item.id));
    } catch {
      // Silently fail — non-critical
    } finally {
      setActing(prev => { const s = new Set(prev); s.delete(item.id); return s; });
    }
  }

  const visible = items.filter(i => !dismissed.has(i.id));

  const ICON: Record<string, string> = { escalation: '⚠', decision: '✦', suggestion: '💡' };
  const COLORS: Record<string, string> = {
    escalation: 'text-red-500',
    decision: 'text-purple-500',
    suggestion: 'text-amber-500',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        Attention Queue
      </h3>

      <div className="space-y-2 flex-1">
        {visible.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">All clear ✓</p>
        )}
        {visible.map(item => (
          <div key={item.id} className="flex items-start gap-2">
            <span className={`flex-shrink-0 text-sm ${COLORS[item.kind]}`}>{ICON[item.kind]}</span>
            <p className="text-xs text-gray-700 dark:text-gray-300 flex-1 truncate">{item.label}</p>
            <div className="flex gap-1 flex-shrink-0">
              {item.navigateTo ? (
                <Link
                  href={item.navigateTo}
                  className="text-xs px-2 py-0.5 rounded border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  Review
                </Link>
              ) : (
                <>
                  <button
                    onClick={() => handleAction(item, true)}
                    disabled={acting.has(item.id)}
                    className="text-xs px-2 py-0.5 rounded border border-green-300 text-green-700 hover:bg-green-50 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-900/30 disabled:opacity-50"
                  >
                    ✓
                  </button>
                  <button
                    onClick={() => handleAction(item, false)}
                    disabled={acting.has(item.id)}
                    className="text-xs px-2 py-0.5 rounded border border-gray-200 dark:border-gray-600 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  >
                    ✕
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Step 2: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add packages/dashboard/src/components/mission-control/AttentionQueue.tsx
git commit -m "feat(dashboard): add AttentionQueue triage component"
```

---

### Task 5: Replace homepage with Command Center

**Files:**
- Modify: `packages/dashboard/src/app/page.tsx` (full replacement)

**Step 1: Replace page.tsx**

```tsx
'use client';

import SwarmStatusPanel from '@/components/mission-control/SwarmStatusPanel';
import LiveEventFeed from '@/components/mission-control/LiveEventFeed';
import TaskPulse from '@/components/mission-control/TaskPulse';
import AttentionQueue from '@/components/mission-control/AttentionQueue';

export default function Home() {
  return (
    <div className="flex flex-col gap-6 h-full">
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Mission Control</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          OpenClaw swarm status at a glance
        </p>
      </div>

      {/* 4-quadrant grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-0">
        <SwarmStatusPanel />
        <LiveEventFeed />
        <TaskPulse />
        <AttentionQueue />
      </div>

      {/* CMD+K hint bar */}
      <div className="flex items-center justify-center py-2 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-400">
          Press{' '}
          <kbd className="px-1.5 py-0.5 text-xs font-mono bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">
            ⌘K
          </kbd>
          {' '}to send a directive to ClawdiaPrime
        </p>
      </div>
    </div>
  );
}
```

**Step 2: Build the dashboard to verify it compiles**

```bash
cd packages/dashboard && npx next build 2>&1 | tail -20
```

Expected: Build succeeds (or only pre-existing errors)

**Step 3: Smoke test — start dev server and open homepage**

```bash
cd packages/dashboard && npx next dev -p 6987 &
sleep 5
curl -s http://localhost:6987/occc/ | grep -o "Mission Control"
```

Expected: `Mission Control`

**Step 4: Commit**

```bash
git add packages/dashboard/src/app/page.tsx
git commit -m "feat(dashboard): replace homepage with mission control command center"
```

---

## Phase 2: Global Command Bar (Cmd+K)

### Task 6: Create gateway directive API endpoint

**Files:**
- Create: `packages/dashboard/src/app/api/gateway/directive/route.ts`

This proxies messages to the openclaw gateway at `localhost:18789`.

**Step 1: Create the route**

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { withAuth } from '@/lib/auth-middleware';
import { getActiveProjectId } from '@/lib/openclaw';
import path from 'path';
import os from 'os';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');
const GATEWAY_URL = process.env.OPENCLAW_GATEWAY_URL ?? 'http://localhost:18789';

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const body = await request.json() as { message: string; projectId?: string; type?: string };
    const { message, type = 'directive' } = body;
    const projectId = body.projectId ?? await getActiveProjectId();

    if (!message?.trim()) {
      return NextResponse.json({ error: 'message is required' }, { status: 400 });
    }

    // Read gateway token from config
    let token = '';
    try {
      const { readFile } = await import('fs/promises');
      const raw = await readFile(path.join(OPENCLAW_ROOT, 'openclaw.json'), 'utf-8');
      const config = JSON.parse(raw);
      token = config.gateway?.token ?? '';
    } catch {
      // No token — gateway may not require auth
    }

    // Find the L1 or L2 agent to address
    const agentId = 'clawdia_prime'; // Default to L1; in future, route by projectId

    const gwResponse = await fetch(`${GATEWAY_URL}/api/agent/${agentId}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, projectId, type }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!gwResponse.ok) {
      const err = await gwResponse.text();
      return NextResponse.json(
        { error: 'Gateway rejected directive', detail: err },
        { status: gwResponse.status }
      );
    }

    const data = await gwResponse.json();
    return NextResponse.json({ status: 'sent', response: data.output ?? data.message ?? null });
  } catch (error: any) {
    // Gateway unavailable — return informative error, not 500
    if (error.name === 'TimeoutError' || error.cause?.code === 'ECONNREFUSED') {
      return NextResponse.json(
        { error: 'Gateway unavailable', detail: 'Is the openclaw gateway running on port 18789?' },
        { status: 503 }
      );
    }
    console.error('[gateway/directive] Error:', error);
    return NextResponse.json({ error: 'Failed to send directive' }, { status: 500 });
  }
}

export const POST = withAuth(handler);
```

**Step 2: TypeScript check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

Expected: No errors

**Step 3: Commit**

```bash
git add packages/dashboard/src/app/api/gateway/directive/route.ts
git commit -m "feat(api): add gateway directive proxy endpoint POST /api/gateway/directive"
```

---

### Task 7: Create CommandBar component

**Files:**
- Create: `packages/dashboard/src/components/command/CommandBar.tsx`

**Step 1: Create the component**

```tsx
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiJson, apiFetch } from '@/lib/api-client';
import { useProject } from '@/context/ProjectContext';

interface CommandBarProps {
  onClose: () => void;
}

const PLACEHOLDER = 'Type a directive or /command (try /help)…';

const SYSTEM_COMMANDS: Record<string, { description: string; args: string }> = {
  '/help': { description: 'Show available commands', args: '' },
  '/pause': { description: 'Pause a running task', args: '<task-id>' },
  '/resume': { description: 'Resume a failed task', args: '<task-id>' },
  '/cancel': { description: 'Cancel a task', args: '<task-id>' },
  '/spawn': { description: 'Spawn a new task', args: '<description>' },
};

function CommandBar({ onClose }: CommandBarProps) {
  const { projectId } = useProject();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState('');
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      return JSON.parse(localStorage.getItem('occc-cmd-history') ?? '[]');
    } catch {
      return [];
    }
  });
  const [historyIdx, setHistoryIdx] = useState(-1);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  function saveHistory(cmd: string) {
    const updated = [cmd, ...history.filter(h => h !== cmd)].slice(0, 10);
    setHistory(updated);
    localStorage.setItem('occc-cmd-history', JSON.stringify(updated));
  }

  async function execute() {
    const cmd = value.trim();
    if (!cmd) return;
    saveHistory(cmd);
    setLoading(true);
    setResponse(null);

    try {
      if (cmd.startsWith('/')) {
        await handleSystemCommand(cmd);
      } else {
        // Natural language directive
        const data = await apiJson<{ status: string; response?: string }>(
          '/api/gateway/directive',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: cmd, projectId: projectId ?? undefined }),
          }
        );
        setResponse(data.response ?? 'Directive sent.');
      }
    } catch (err: any) {
      setResponse(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSystemCommand(cmd: string) {
    const parts = cmd.split(' ');
    const verb = parts[0];
    const arg = parts.slice(1).join(' ');

    switch (verb) {
      case '/help':
        setResponse(Object.entries(SYSTEM_COMMANDS)
          .map(([k, v]) => `${k} ${v.args} — ${v.description}`)
          .join('\n'));
        break;

      case '/pause':
        if (!arg) { setResponse('Usage: /pause <task-id>'); break; }
        await apiJson('/api/gateway/directive', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: `pause task ${arg}`, type: 'control', projectId: projectId ?? undefined }),
        });
        setResponse(`Pause signal sent for ${arg}`);
        break;

      case '/resume':
        if (!arg) { setResponse('Usage: /resume <task-id>'); break; }
        await apiFetch(`/api/tasks/${encodeURIComponent(arg)}/resume`, { method: 'POST' });
        setResponse(`Resumed ${arg}`);
        router.refresh();
        break;

      case '/cancel':
        if (!arg) { setResponse('Usage: /cancel <task-id>'); break; }
        await apiFetch(`/api/tasks/${encodeURIComponent(arg)}/fail`, { method: 'POST' });
        setResponse(`Cancelled ${arg}`);
        router.refresh();
        break;

      case '/spawn':
        if (!arg) { setResponse('Usage: /spawn <description>'); break; }
        await apiJson('/api/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ description: arg, project_id: projectId }),
        });
        setResponse(`Task spawned: ${arg}`);
        router.refresh();
        break;

      default:
        setResponse(`Unknown command: ${verb}. Type /help for available commands.`);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      execute();
    } else if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      const idx = Math.min(historyIdx + 1, history.length - 1);
      setHistoryIdx(idx);
      if (history[idx]) setValue(history[idx]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const idx = Math.max(historyIdx - 1, -1);
      setHistoryIdx(idx);
      setValue(idx === -1 ? '' : history[idx]);
    }
  }

  // Suggestions from history
  const suggestions = value.startsWith('/')
    ? Object.keys(SYSTEM_COMMANDS).filter(k => k.startsWith(value))
    : history.filter(h => h.toLowerCase().includes(value.toLowerCase()) && h !== value).slice(0, 3);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-xl bg-white dark:bg-gray-900 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {/* Input row */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100 dark:border-gray-800">
          <span className="text-gray-400">›</span>
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={e => { setValue(e.target.value); setHistoryIdx(-1); setResponse(null); }}
            onKeyDown={handleKeyDown}
            placeholder={PLACEHOLDER}
            className="flex-1 bg-transparent text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 outline-none"
          />
          {loading && (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}
        </div>

        {/* Suggestions */}
        {suggestions.length > 0 && !response && (
          <div className="border-b border-gray-100 dark:border-gray-800">
            {suggestions.map(s => (
              <button
                key={s}
                onClick={() => { setValue(s); inputRef.current?.focus(); }}
                className="w-full text-left px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 font-mono"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Response */}
        {response && (
          <div className="px-4 py-3 bg-gray-50 dark:bg-gray-800/50">
            <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">{response}</pre>
          </div>
        )}

        {/* Footer hint */}
        <div className="px-4 py-2 text-xs text-gray-400 flex gap-4">
          <span><kbd className="font-mono">Enter</kbd> execute</span>
          <span><kbd className="font-mono">↑↓</kbd> history</span>
          <span><kbd className="font-mono">Esc</kbd> close</span>
          <span className="ml-auto">prefix <kbd className="font-mono">/</kbd> for system commands</span>
        </div>
      </div>
    </div>
  );
}

// CommandBarProvider — mounts globally, listens for Cmd+K
export function CommandBarProvider() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(o => !o);
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  if (!open) return null;
  return <CommandBar onClose={() => setOpen(false)} />;
}

export default CommandBarProvider;
```

**Step 2: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

Expected: No errors

**Step 3: Commit**

```bash
git add packages/dashboard/src/components/command/CommandBar.tsx
git commit -m "feat(dashboard): add global CommandBar (Cmd+K) with system commands and gateway directives"
```

---

### Task 8: Mount CommandBar in root layout

**Files:**
- Modify: `packages/dashboard/src/app/layout.tsx`

**Step 1: Add import and component to layout**

Add the import after existing imports:
```typescript
import CommandBarProvider from '@/components/command/CommandBar';
```

Add `<CommandBarProvider />` inside `<ProjectProvider>`, just before `<div className="flex h-screen overflow-hidden">`:

Old:
```tsx
<ProjectProvider>
  <div className="flex h-screen overflow-hidden">
```

New:
```tsx
<ProjectProvider>
  <CommandBarProvider />
  <div className="flex h-screen overflow-hidden">
```

**Step 2: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

**Step 3: Smoke test**

```bash
cd packages/dashboard && npx next build 2>&1 | grep -E "error|Error|✓" | tail -10
```

Expected: Build succeeds

**Step 4: Commit**

```bash
git add packages/dashboard/src/app/layout.tsx
git commit -m "feat(dashboard): mount CommandBarProvider in root layout for global Cmd+K access"
```

---

## Phase 3: Terminal Side Drawer

### Task 9: Create TerminalDrawer component

**Files:**
- Create: `packages/dashboard/src/components/tasks/TerminalDrawer.tsx`

This is a right-side slide-over that wraps the existing `TaskTerminalPanel`.

**Step 1: Create the component**

```tsx
'use client';

import { useEffect, useRef } from 'react';
import type { Task } from '@/lib/types';
import TaskTerminalPanel from './TaskTerminalPanel';
import { X, Maximize2, Minimize2 } from 'lucide-react';
import { useState } from 'react';

interface TerminalDrawerProps {
  tasks: Task[];                // All active tasks for tabs
  selectedTaskId: string;
  onSelectTask: (id: string) => void;
  onClose: () => void;
}

export default function TerminalDrawer({
  tasks,
  selectedTaskId,
  onSelectTask,
  onClose,
}: TerminalDrawerProps) {
  const [fullscreen, setFullscreen] = useState(false);
  const selectedTask = tasks.find(t => t.id === selectedTaskId);

  // Close on Escape
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && !fullscreen) onClose();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, fullscreen]);

  if (!selectedTask) return null;

  const drawerClass = fullscreen
    ? 'fixed inset-0 z-40 flex flex-col bg-gray-950'
    : 'fixed right-0 top-0 bottom-0 z-40 w-[420px] flex flex-col bg-gray-950 border-l border-gray-800 shadow-2xl';

  return (
    <>
      {/* Backdrop — click to close (only in non-fullscreen) */}
      {!fullscreen && (
        <div
          className="fixed inset-0 z-30 bg-transparent"
          onClick={onClose}
        />
      )}

      <div className={drawerClass}>
        {/* Tabs row */}
        <div className="flex items-center gap-0 border-b border-gray-800 bg-gray-900 flex-shrink-0 overflow-x-auto">
          {tasks.map(task => (
            <button
              key={task.id}
              onClick={(e) => { e.stopPropagation(); onSelectTask(task.id); }}
              className={`px-3 py-2 text-xs font-mono flex-shrink-0 border-r border-gray-800 transition-colors ${
                task.id === selectedTaskId
                  ? 'bg-gray-800 text-gray-100'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50'
              }`}
              title={task.id}
            >
              {task.id.slice(0, 10)}…
            </button>
          ))}
          {/* Spacer + controls */}
          <div className="ml-auto flex items-center gap-1 px-2 flex-shrink-0">
            <button
              onClick={() => setFullscreen(f => !f)}
              className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
              title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
            >
              {fullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={onClose}
              className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
              title="Close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Terminal panel — takes remaining height */}
        <div className="flex-1 overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
          <TaskTerminalPanel task={selectedTask} onClose={onClose} />
        </div>
      </div>
    </>
  );
}
```

**Step 2: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add packages/dashboard/src/components/tasks/TerminalDrawer.tsx
git commit -m "feat(dashboard): add TerminalDrawer right-side slide-over for task terminal"
```

---

### Task 10: Integrate TerminalDrawer into TaskBoard

**Files:**
- Modify: `packages/dashboard/src/components/tasks/TaskBoard.tsx`

The TaskBoard already has `selectedTaskId` state and renders `TaskTerminalPanel` — we're replacing the inline panel with the new slide-over drawer.

**Step 1: Read the full TaskBoard to understand the current rendering**

Read `packages/dashboard/src/components/tasks/TaskBoard.tsx` in full to see the existing terminal panel integration.

**Step 2: Identify the section that renders TaskTerminalPanel**

Look for the JSX that renders `<TaskTerminalPanel>` and the wrapping div that controls the layout. Typically this will be a flex container showing the kanban board + the terminal panel side by side.

**Step 3: Replace inline TaskTerminalPanel with TerminalDrawer**

Remove the import of `TaskTerminalPanel` and add `TerminalDrawer`:
```typescript
// Remove: import TaskTerminalPanel from './TaskTerminalPanel';
import TerminalDrawer from './TerminalDrawer';
```

Find where the terminal panel is rendered (the `{selectedTask && <TaskTerminalPanel ...>}` block) and replace it with the drawer:

```tsx
{selectedTask && (
  <TerminalDrawer
    tasks={tasks.filter(t =>
      t.status === 'in_progress' || t.status === 'starting' || t.status === 'testing'
    )}
    selectedTaskId={selectedTask.id}
    onSelectTask={setSelectedTaskId}
    onClose={() => setSelectedTaskId(null)}
  />
)}
```

Also handle the `?open=<taskId>` URL param to pre-open the drawer (for deep links from TaskPulse):

```typescript
import { useSearchParams } from 'next/navigation';

// Inside the component:
const searchParams = useSearchParams();
useEffect(() => {
  const openId = searchParams.get('open');
  if (openId && tasks.find(t => t.id === openId)) {
    setSelectedTaskId(openId);
  }
}, [searchParams, tasks]);
```

**Step 4: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

Expected: No errors

**Step 5: Commit**

```bash
git add packages/dashboard/src/components/tasks/TaskBoard.tsx
git commit -m "feat(tasks): replace inline terminal panel with TerminalDrawer slide-over"
```

---

## Phase 4: Token Tracking — Python Side

### Task 11: Add token usage capture to gateway_client.py

**Files:**
- Modify: `packages/orchestration/src/openclaw/gateway_client.py`

The gateway client dispatches messages to agents and receives responses from the Claude API. We need to capture the `usage` field from responses.

**Step 1: Read the full gateway_client.py** (already read above — 65 lines)

**Step 2: Add token capture to DispatchResult and dispatch methods**

The `DispatchResult` needs `input_tokens` and `output_tokens` fields. The `dispatch()` method needs to extract these from the response and write them to state.

Add to `DispatchResult` dataclass:
```python
input_tokens: int = 0
output_tokens: int = 0
```

Modify the `dispatch()` return to capture usage:
```python
data = response.json()
return DispatchResult(
    run_id=data.get("runId", ""),
    status="ok" if response.is_success else "error",
    output=data.get("output"),
    error=data.get("error"),
    input_tokens=data.get("usage", {}).get("input_tokens", 0),
    output_tokens=data.get("usage", {}).get("output_tokens", 0),
)
```

**Step 3: Create token usage writer function in metrics.py**

Modify `packages/orchestration/src/openclaw/metrics.py` to add:

```python
import time
from datetime import datetime, timezone
from typing import Optional

def record_token_usage(
    project_id: str,
    agent_id: str,
    task_id: Optional[str],
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Append a token usage record to workspace-state.json."""
    from .state_engine import JarvisState
    from .config import get_state_path

    try:
        jarvis = JarvisState(get_state_path(project_id))

        def updater(state: dict) -> dict:
            if "token_usage" not in state:
                state["token_usage"] = []
            state["token_usage"].append({
                "ts": datetime.now(timezone.utc).isoformat(),
                "agent_id": agent_id,
                "task_id": task_id,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            })
            # Keep only last 1000 entries to avoid state file bloat
            if len(state["token_usage"]) > 1000:
                state["token_usage"] = state["token_usage"][-1000:]
            return state

        jarvis.update_state(updater)
    except Exception as e:
        logger.warning(f"Failed to record token usage: {e}")


def get_token_usage(project_id: str, days: int = 1) -> dict:
    """Aggregate token usage for a project over the last N days."""
    from .state_engine import JarvisState
    from .config import get_state_path

    try:
        jarvis = JarvisState(get_state_path(project_id))
        state = jarvis.read_state()
    except Exception:
        state = {}

    records = state.get("token_usage", [])
    cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

    by_agent: dict = {}
    by_task: dict = {}
    total_input = 0
    total_output = 0

    for r in records:
        try:
            ts = datetime.fromisoformat(r["ts"]).timestamp()
        except Exception:
            continue
        if ts < cutoff:
            continue

        ai = r.get("input_tokens", 0)
        ao = r.get("output_tokens", 0)
        total_input += ai
        total_output += ao

        aid = r.get("agent_id", "unknown")
        if aid not in by_agent:
            by_agent[aid] = {"input_tokens": 0, "output_tokens": 0}
        by_agent[aid]["input_tokens"] += ai
        by_agent[aid]["output_tokens"] += ao

        tid = r.get("task_id")
        if tid:
            if tid not in by_task:
                by_task[tid] = {"input_tokens": 0, "output_tokens": 0}
            by_task[tid]["input_tokens"] += ai
            by_task[tid]["output_tokens"] += ao

    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "by_agent": by_agent,
        "by_task": by_task,
        "record_count": len([r for r in records if True]),
    }
```

**Step 4: Write tests**

Create `packages/orchestration/tests/test_token_usage.py`:

```python
"""Tests for token usage recording and aggregation."""
import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone


def test_record_token_usage_creates_entry(tmp_path, monkeypatch):
    """record_token_usage appends an entry to workspace-state.json."""
    from openclaw.state_engine import JarvisState
    from openclaw.metrics import record_token_usage, get_token_usage

    state_file = tmp_path / "workspace-state.json"
    monkeypatch.setattr("openclaw.metrics.get_state_path", lambda pid: str(state_file))

    record_token_usage(
        project_id="test",
        agent_id="clawdia_prime",
        task_id="task-001",
        model="claude-sonnet-4-6",
        input_tokens=1000,
        output_tokens=500,
    )

    with open(state_file) as f:
        state = json.load(f)

    assert "token_usage" in state
    assert len(state["token_usage"]) == 1
    entry = state["token_usage"][0]
    assert entry["agent_id"] == "clawdia_prime"
    assert entry["input_tokens"] == 1000
    assert entry["output_tokens"] == 500


def test_get_token_usage_aggregates(tmp_path, monkeypatch):
    """get_token_usage returns correct totals."""
    from openclaw.metrics import record_token_usage, get_token_usage

    state_file = tmp_path / "workspace-state.json"
    monkeypatch.setattr("openclaw.metrics.get_state_path", lambda pid: str(state_file))

    record_token_usage("test", "agent-a", "task-1", "claude-sonnet-4-6", 1000, 200)
    record_token_usage("test", "agent-b", "task-2", "claude-sonnet-4-6", 2000, 400)

    result = get_token_usage("test", days=1)

    assert result["total_input_tokens"] == 3000
    assert result["total_output_tokens"] == 600
    assert "agent-a" in result["by_agent"]
    assert "agent-b" in result["by_agent"]
    assert result["by_agent"]["agent-a"]["input_tokens"] == 1000


def test_get_token_usage_empty_state(tmp_path, monkeypatch):
    """get_token_usage returns zeros when no data exists."""
    from openclaw.metrics import get_token_usage

    state_file = tmp_path / "workspace-state.json"
    monkeypatch.setattr("openclaw.metrics.get_state_path", lambda pid: str(state_file))

    result = get_token_usage("test", days=1)

    assert result["total_input_tokens"] == 0
    assert result["total_output_tokens"] == 0
    assert result["by_agent"] == {}
```

**Step 5: Run the tests**

```bash
cd packages/orchestration && uv run pytest tests/test_token_usage.py -v
```

Expected: All 3 tests pass

**Step 6: Commit**

```bash
git add packages/orchestration/src/openclaw/metrics.py \
        packages/orchestration/src/openclaw/gateway_client.py \
        packages/orchestration/tests/test_token_usage.py
git commit -m "feat(orchestration): add token usage recording and aggregation to metrics.py"
```

---

## Phase 5: Token Tracking — Dashboard UI

### Task 12: Create Usage metrics API endpoint

**Files:**
- Create: `packages/dashboard/src/app/api/metrics/usage/route.ts`

Reads token_usage from workspace-state.json for the active project.

**Step 1: Create the route**

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getActiveProjectId } from '@/lib/openclaw';
import { withAuth } from '@/lib/auth-middleware';
import path from 'path';
import os from 'os';
import fs from 'fs/promises';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || path.join(os.homedir(), '.openclaw');

// Default model cost rates per 1M tokens (USD)
const DEFAULT_RATES: Record<string, { input: number; output: number }> = {
  'claude-sonnet-4-6': { input: 3.0, output: 15.0 },
  'claude-haiku-4-5': { input: 0.25, output: 1.25 },
  'claude-opus-4-6': { input: 15.0, output: 75.0 },
  default: { input: 3.0, output: 15.0 },
};

interface TokenRecord {
  ts: string;
  agent_id: string;
  task_id?: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
}

async function readTokenUsage(projectId: string): Promise<TokenRecord[]> {
  const statePath = path.join(OPENCLAW_ROOT, projectId, 'workspace-state.json');
  try {
    const raw = await fs.readFile(statePath, 'utf-8');
    const state = JSON.parse(raw);
    return state.token_usage ?? [];
  } catch {
    return [];
  }
}

async function getTokenRates(): Promise<Record<string, { input: number; output: number }>> {
  try {
    const raw = await fs.readFile(path.join(OPENCLAW_ROOT, 'openclaw.json'), 'utf-8');
    const config = JSON.parse(raw);
    return { ...DEFAULT_RATES, ...config.token_rates };
  } catch {
    return DEFAULT_RATES;
  }
}

function calcCost(model: string, inputTokens: number, outputTokens: number, rates: Record<string, { input: number; output: number }>): number {
  const rate = rates[model] ?? rates.default ?? DEFAULT_RATES.default;
  return (inputTokens * rate.input + outputTokens * rate.output) / 1_000_000;
}

async function handler(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project') ?? await getActiveProjectId();
    const days = parseInt(searchParams.get('days') ?? '1', 10);

    const [records, rates] = await Promise.all([
      readTokenUsage(projectId),
      getTokenRates(),
    ]);

    const cutoffMs = Date.now() - days * 86_400_000;

    const filtered = records.filter(r => {
      try {
        return new Date(r.ts).getTime() >= cutoffMs;
      } catch {
        return false;
      }
    });

    let totalInput = 0;
    let totalOutput = 0;
    let totalCost = 0;
    const byAgent: Record<string, { inputTokens: number; outputTokens: number; cost: number }> = {};
    const byTask: Record<string, { inputTokens: number; outputTokens: number; cost: number }> = {};

    for (const r of filtered) {
      const cost = calcCost(r.model, r.input_tokens, r.output_tokens, rates);
      totalInput += r.input_tokens;
      totalOutput += r.output_tokens;
      totalCost += cost;

      if (!byAgent[r.agent_id]) byAgent[r.agent_id] = { inputTokens: 0, outputTokens: 0, cost: 0 };
      byAgent[r.agent_id].inputTokens += r.input_tokens;
      byAgent[r.agent_id].outputTokens += r.output_tokens;
      byAgent[r.agent_id].cost += cost;

      if (r.task_id) {
        if (!byTask[r.task_id]) byTask[r.task_id] = { inputTokens: 0, outputTokens: 0, cost: 0 };
        byTask[r.task_id].inputTokens += r.input_tokens;
        byTask[r.task_id].outputTokens += r.output_tokens;
        byTask[r.task_id].cost += cost;
      }
    }

    return NextResponse.json({
      projectId,
      days,
      summary: {
        inputTokens: totalInput,
        outputTokens: totalOutput,
        totalTokens: totalInput + totalOutput,
        estimatedCostUsd: Math.round(totalCost * 10000) / 10000,
        recordCount: filtered.length,
      },
      byAgent: Object.entries(byAgent)
        .sort((a, b) => b[1].cost - a[1].cost)
        .map(([agentId, data]) => ({ agentId, ...data, cost: Math.round(data.cost * 10000) / 10000 })),
      byTask: Object.entries(byTask)
        .sort((a, b) => b[1].cost - a[1].cost)
        .slice(0, 20)
        .map(([taskId, data]) => ({ taskId, ...data, cost: Math.round(data.cost * 10000) / 10000 })),
    });
  } catch (error) {
    console.error('[metrics/usage] Error:', error);
    return NextResponse.json({ error: 'Failed to load usage metrics' }, { status: 500 });
  }
}

export const GET = withAuth(handler);
```

**Step 2: TypeScript check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add packages/dashboard/src/app/api/metrics/usage/route.ts
git commit -m "feat(api): add GET /api/metrics/usage endpoint for token/cost tracking"
```

---

### Task 13: Create UsageTab component

**Files:**
- Create: `packages/dashboard/src/components/metrics/UsageTab.tsx`

**Step 1: Create the component**

```tsx
'use client';

import { useEffect, useState } from 'react';
import { apiJson } from '@/lib/api-client';
import { MetricCard } from './MetricCard';
import { TimeRangeSelector, type TimeRange } from './TimeRangeSelector';

interface UsageSummary {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  estimatedCostUsd: number;
  recordCount: number;
}

interface AgentUsage {
  agentId: string;
  inputTokens: number;
  outputTokens: number;
  cost: number;
}

interface TaskUsage {
  taskId: string;
  inputTokens: number;
  outputTokens: number;
  cost: number;
}

interface UsageData {
  summary: UsageSummary;
  byAgent: AgentUsage[];
  byTask: TaskUsage[];
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

interface UsageTabProps {
  projectId: string | null;
}

export function UsageTab({ projectId }: UsageTabProps) {
  const [timeRange, setTimeRange] = useState<TimeRange>('1d');
  const [data, setData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const days = timeRange === '1d' ? 1 : timeRange === '7d' ? 7 : 30;

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    apiJson<UsageData>(`/api/metrics/usage?project=${projectId}&days=${days}`)
      .then(setData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [projectId, days]);

  if (loading) return <div className="flex items-center justify-center h-32 text-sm text-gray-500">Loading usage data…</div>;
  if (error) return <div className="text-sm text-red-500 p-4">Error: {error}</div>;
  if (!data) return null;

  const { summary, byAgent, byTask } = data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Token & Cost Usage</h3>
        <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Tokens"
          value={fmtTokens(summary.totalTokens)}
          trend="neutral"
          trendValue=""
        />
        <MetricCard
          label="Input Tokens"
          value={fmtTokens(summary.inputTokens)}
          trend="neutral"
          trendValue=""
        />
        <MetricCard
          label="Output Tokens"
          value={fmtTokens(summary.outputTokens)}
          trend="neutral"
          trendValue=""
        />
        <MetricCard
          label="Est. Cost (USD)"
          value={`$${summary.estimatedCostUsd.toFixed(4)}`}
          trend="neutral"
          trendValue=""
        />
      </div>

      {/* Agent breakdown */}
      {byAgent.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
            By Agent
          </h4>
          <div className="space-y-2">
            {byAgent.map(a => (
              <div key={a.agentId} className="flex items-center gap-3 text-sm">
                <span className="font-mono text-gray-600 dark:text-gray-400 w-40 truncate">{a.agentId}</span>
                <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-blue-500 h-full rounded-full"
                    style={{
                      width: `${Math.min(100, (a.cost / Math.max(...byAgent.map(x => x.cost))) * 100)}%`
                    }}
                  />
                </div>
                <span className="text-gray-600 dark:text-gray-400 w-20 text-right font-mono text-xs">
                  {fmtTokens(a.inputTokens + a.outputTokens)} tok
                </span>
                <span className="text-gray-800 dark:text-gray-200 w-16 text-right font-mono text-xs">
                  ${a.cost.toFixed(4)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Task breakdown */}
      {byTask.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-3">
            Top Tasks by Cost
          </h4>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 pr-4 font-medium text-gray-500">Task ID</th>
                  <th className="text-right py-2 pr-4 font-medium text-gray-500">Input</th>
                  <th className="text-right py-2 pr-4 font-medium text-gray-500">Output</th>
                  <th className="text-right py-2 font-medium text-gray-500">Cost</th>
                </tr>
              </thead>
              <tbody>
                {byTask.slice(0, 10).map(t => (
                  <tr key={t.taskId} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-1.5 pr-4 font-mono text-gray-600 dark:text-gray-400">{t.taskId}</td>
                    <td className="py-1.5 pr-4 text-right font-mono">{fmtTokens(t.inputTokens)}</td>
                    <td className="py-1.5 pr-4 text-right font-mono">{fmtTokens(t.outputTokens)}</td>
                    <td className="py-1.5 text-right font-mono">${t.cost.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {summary.recordCount === 0 && (
        <div className="text-center py-8 text-sm text-gray-400">
          No token usage data recorded yet.
          <br />
          <span className="text-xs">Token tracking requires the openclaw gateway to be running.</span>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

**Step 3: Commit**

```bash
git add packages/dashboard/src/components/metrics/UsageTab.tsx
git commit -m "feat(metrics): add UsageTab component for token/cost tracking"
```

---

### Task 14: Add Usage tab to metrics page

**Files:**
- Modify: `packages/dashboard/src/app/metrics/page.tsx`

The metrics page has content organized by sections. We need to add a tab system (or simply add UsageTab at the bottom) without breaking existing content.

**Step 1: Read the full metrics page** (already partially read — read lines 60-end)

```bash
# Read the remaining half of the file
```

Read `packages/dashboard/src/app/metrics/page.tsx` from line 60 to end to understand the rendering structure.

**Step 2: Add tab state and UsageTab to the page**

At the top of the file, add:
```typescript
import { UsageTab } from '@/components/metrics/UsageTab';
```

Add tab state:
```typescript
const [activeTab, setActiveTab] = useState<'overview' | 'usage'>('overview');
```

Add tab selector UI just below the page header (before the existing content):
```tsx
<div className="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-6">
  {(['overview', 'usage'] as const).map(tab => (
    <button
      key={tab}
      onClick={() => setActiveTab(tab)}
      className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
        activeTab === tab
          ? 'border-blue-600 text-blue-700 dark:text-blue-400'
          : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
      }`}
    >
      {tab}
    </button>
  ))}
</div>
```

Wrap existing content in `{activeTab === 'overview' && (...)}` and add:
```tsx
{activeTab === 'usage' && <UsageTab projectId={projectId} />}
```

**Step 3: Compile check**

```bash
cd packages/dashboard && npx tsc --noEmit
```

**Step 4: Final build check**

```bash
cd packages/dashboard && npx next build 2>&1 | tail -20
```

Expected: Build succeeds

**Step 5: Commit**

```bash
git add packages/dashboard/src/app/metrics/page.tsx
git commit -m "feat(metrics): add Usage tab to metrics page with token/cost tracking UI"
```

---

### Task 15: Add Usage to sidebar navigation

**Files:**
- Modify: `packages/dashboard/src/components/layout/Sidebar.tsx`

**Step 1: Add Usage nav item to the navItems array**

In `Sidebar.tsx`, add to the `navItems` array after the Metrics entry:

```typescript
{
  href: '/metrics?tab=usage',
  label: 'Usage',
  icon: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
},
```

**Step 2: Commit**

```bash
git add packages/dashboard/src/components/layout/Sidebar.tsx
git commit -m "feat(nav): add Usage link to sidebar navigation"
```

---

### Task 16: Update SwarmStatusPanel to show real cost data

**Files:**
- Modify: `packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx`

Now that the `/api/metrics/usage` endpoint exists, wire the cost data into the SwarmStatusPanel.

**Step 1: Add usage data fetching to SwarmStatusPanel**

In the `load()` function inside `useEffect`, add a third parallel fetch:

```typescript
const [agentsRes, metricsRes, usageRes] = await Promise.all([
  apiJson<...>('/api/agents'),
  apiJson<...>('/api/metrics'),
  apiJson<{ summary: { estimatedCostUsd: number; totalTokens: number } }>('/api/metrics/usage?days=1').catch(() => null),
]);
```

Update `setData()` to include cost:
```typescript
setData({
  // ... existing fields ...
  todayCostUsd: usageRes?.summary.estimatedCostUsd ?? null,
  todayTokens: usageRes?.summary.totalTokens ?? null,
});
```

**Step 2: Compile check and final build**

```bash
cd packages/dashboard && npx tsc --noEmit && npx next build 2>&1 | tail -5
```

Expected: No errors, build succeeds

**Step 3: Run Python tests to ensure nothing broken**

```bash
cd packages/orchestration && uv run pytest tests/ -v 2>&1 | tail -20
```

Expected: All tests pass

**Step 4: Final commit**

```bash
git add packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx
git commit -m "feat(dashboard): wire real token/cost data into SwarmStatusPanel command center"
```

---

## Verification Checklist

After all tasks are complete, verify:

1. **Homepage** (`/` or `/occc/`) shows 4 quadrants: Swarm Status, Live Events, Task Pulse, Attention Queue
2. **Cmd+K** opens command bar from any page; `/help` shows commands; `/resume <id>` and `/cancel <id>` work; natural language is sent to gateway
3. **Task Board** — clicking an in-progress task opens the right-side terminal drawer; tabs switch between active tasks; Escape closes
4. **Metrics page** — "Usage" tab shows token/cost summary and by-agent breakdown (may show zeros until gateway emits usage data)
5. **Python tests pass**: `uv run pytest packages/orchestration/tests/ -v`
6. **TypeScript compiles**: `cd packages/dashboard && npx tsc --noEmit`
7. **Next.js build succeeds**: `cd packages/dashboard && npx next build`
