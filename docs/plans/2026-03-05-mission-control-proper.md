# Mission Control: Proper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement proper Mission Control by migrating AttentionQueue to SWR, making LiveEventFeed connection-aware with offline fallback, and wiring gateway cost/token tracking through to SwarmStatusPanel.

**Architecture:** Three independent streams that can each be built and verified separately. Stream 1 replaces manual polling in AttentionQueue with SWR hooks. Stream 2 adds a connection state machine and `/api/events/latest` fallback endpoint to LiveEventFeed. Stream 3 bridges the existing gateway `model.usage` diagnostic events through an append-only NDJSON file to the dashboard metrics endpoint.

**Tech Stack:** Next.js 14 App Router, SWR, Vitest (dashboard), TypeScript gateway (`openclaw/src/`), Node.js `fs/promises`, `Intl.DateTimeFormat` for timezone math

**Design doc:** `docs/plans/2026-03-05-mission-control-proper-design.md`

---

## STREAM 1: AttentionQueue SWR Migration

### Task 1: Add `useEscalatingTasks` hook

**Files:**
- Create: `packages/dashboard/src/lib/hooks/useEscalatingTasks.ts`

**Step 1: Write the hook**

```ts
// packages/dashboard/src/lib/hooks/useEscalatingTasks.ts
import useSWR from 'swr';
import type { Task } from '@/lib/types';
import { apiJson } from '@/lib/api-client';

export function useEscalatingTasks(projectId: string | null) {
  return useSWR<{ tasks: Task[] }>(
    projectId ? `/api/tasks?state=escalating&project=${encodeURIComponent(projectId)}` : null,
    (url: string) => apiJson<{ tasks: Task[] }>(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}
```

**Step 2: Verify it compiles**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -20
```
Expected: no errors for this file.

**Step 3: Commit**

```bash
git add packages/dashboard/src/lib/hooks/useEscalatingTasks.ts
git commit -m "feat(mission-control): add useEscalatingTasks SWR hook"
```

---

### Task 2: Add `useDecisions` hook

**Files:**
- Create: `packages/dashboard/src/lib/hooks/useDecisions.ts`

Note: `/api/decisions` uses `projectId=` query param (not `project=`). It returns `Decision[]` directly (array, not wrapped object).

**Step 1: Check the Decision type location**

```bash
grep -rn "type Decision\|interface Decision" packages/dashboard/src/lib/
```
Expected: finds `packages/dashboard/src/lib/types/decisions.ts` or similar.

**Step 2: Write the hook**

```ts
// packages/dashboard/src/lib/hooks/useDecisions.ts
import useSWR from 'swr';
import type { Decision } from '@/lib/types/decisions';
import { apiJson } from '@/lib/api-client';

export function useDecisions(projectId: string | null) {
  return useSWR<Decision[]>(
    projectId ? `/api/decisions?projectId=${encodeURIComponent(projectId)}` : null,
    (url: string) => apiJson<Decision[]>(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}
```

**Step 3: Verify it compiles**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -20
```

**Step 4: Commit**

```bash
git add packages/dashboard/src/lib/hooks/useDecisions.ts
git commit -m "feat(mission-control): add useDecisions SWR hook"
```

---

### Task 3: Add `useSuggestions` hook

**Files:**
- Create: `packages/dashboard/src/lib/hooks/useSuggestions.ts`

Note: `/api/suggestions` uses `project=` query param. It returns `{ version, last_run, suggestions }`.

**Step 1: Write the hook**

```ts
// packages/dashboard/src/lib/hooks/useSuggestions.ts
import useSWR from 'swr';
import { apiJson } from '@/lib/api-client';

interface SuggestionRecord {
  id: string;
  status: string;
  evidence_count: number;
  title?: string;
  summary?: string;
}

export interface SuggestionsResponse {
  version: string;
  last_run: number | null;
  suggestions: SuggestionRecord[];
}

export function useSuggestions(projectId: string | null) {
  return useSWR<SuggestionsResponse>(
    projectId ? `/api/suggestions?project=${encodeURIComponent(projectId)}` : null,
    (url: string) => apiJson<SuggestionsResponse>(url),
    { refreshInterval: 3000, dedupingInterval: 1500, keepPreviousData: true }
  );
}
```

**Step 2: Verify it compiles**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -20
```

**Step 3: Commit**

```bash
git add packages/dashboard/src/lib/hooks/useSuggestions.ts
git commit -m "feat(mission-control): add useSuggestions SWR hook"
```

---

### Task 4: Rewrite AttentionQueue to use SWR hooks

**Files:**
- Modify: `packages/dashboard/src/components/mission-control/AttentionQueue.tsx`

**Step 1: Read the current file**

```bash
cat packages/dashboard/src/components/mission-control/AttentionQueue.tsx
```

**Step 2: Rewrite the component**

Replace the entire file content with:

```tsx
'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { apiFetch } from '@/lib/api-client';
import { useProject } from '@/context/ProjectContext';
import { useEscalatingTasks } from '@/lib/hooks/useEscalatingTasks';
import { useDecisions } from '@/lib/hooks/useDecisions';
import { useSuggestions } from '@/lib/hooks/useSuggestions';
import type { Decision } from '@/lib/types/decisions';

type ItemKind = 'escalation' | 'decision' | 'suggestion';

interface AttentionItem {
  id: string;
  kind: ItemKind;
  label: string;
}

const MAX_ITEMS = 5;

export default function AttentionQueue() {
  const { projectId } = useProject();
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const [acting, setActing] = useState<Set<string>>(new Set());

  const {
    data: tasksData,
    error: tasksError,
    isLoading: tasksLoading,
  } = useEscalatingTasks(projectId);

  const {
    data: decisionsData,
    error: decisionsError,
    isLoading: decisionsLoading,
  } = useDecisions(projectId);

  const {
    data: suggestionsData,
    error: suggestionsError,
  } = useSuggestions(projectId);

  const isLoading = tasksLoading && decisionsLoading && !tasksData && !decisionsData;
  const anyError = tasksError || decisionsError || suggestionsError;
  const hasStaleData = anyError && (tasksData || decisionsData || suggestionsData);

  // Build combined item list
  const items: AttentionItem[] = [];

  for (const t of tasksData?.tasks ?? []) {
    items.push({ id: t.id, kind: 'escalation', label: (t as any).title ?? t.id });
  }
  for (const d of (decisionsData ?? []) as Decision[]) {
    items.push({ id: d.id, kind: 'decision', label: d.outcome || d.citation || 'Pending decision' });
  }
  const pendingSuggestions = (suggestionsData?.suggestions ?? []).filter(s => s.status === 'pending');
  for (const s of pendingSuggestions) {
    items.push({ id: s.id, kind: 'suggestion', label: s.title ?? s.summary ?? s.id });
  }

  // Sort: escalations → decisions → suggestions
  const kindOrder: Record<ItemKind, number> = { escalation: 0, decision: 1, suggestion: 2 };
  items.sort((a, b) => kindOrder[a.kind] - kindOrder[b.kind]);

  const visibleItems = items.filter(i => !dismissed.has(i.id)).slice(0, MAX_ITEMS);

  const dismissItem = (id: string) => setDismissed(prev => new Set([...prev, id]));

  const handleDecisionDismiss = async (id: string) => {
    setActing(prev => new Set([...prev, id]));
    dismissItem(id);
    try {
      await apiFetch(`/api/decisions/${encodeURIComponent(id)}`, { method: 'DELETE' });
    } catch {
      setDismissed(prev => { const n = new Set(prev); n.delete(id); return n; });
    } finally {
      setActing(prev => { const n = new Set(prev); n.delete(id); return n; });
    }
  };

  const handleSuggestionReject = async (id: string) => {
    setActing(prev => new Set([...prev, id]));
    dismissItem(id);
    try {
      await apiFetch(`/api/suggestions/${encodeURIComponent(id)}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'reject', project: projectId }),
      });
    } catch {
      setDismissed(prev => { const n = new Set(prev); n.delete(id); return n; });
    } finally {
      setActing(prev => { const n = new Set(prev); n.delete(id); return n; });
    }
  };

  if (isLoading) {
    return <div className="text-sm text-gray-500 dark:text-gray-400 py-2">Loading...</div>;
  }

  return (
    <div>
      {hasStaleData && (
        <div className="text-xs text-amber-600 dark:text-amber-400 mb-2 px-1">
          ⚠ Data may be stale
        </div>
      )}
      {!hasStaleData && anyError && visibleItems.length === 0 && (
        <div className="text-sm text-red-500 dark:text-red-400 py-2">Failed to load</div>
      )}
      {visibleItems.length === 0 && !anyError && (
        <div className="text-sm text-gray-500 dark:text-gray-400 py-2 text-center">All clear ✓</div>
      )}
      {visibleItems.length > 0 && (
        <ul className="space-y-2">
          {visibleItems.map((item) => (
            <li
              key={item.id}
              className="flex items-center gap-2 rounded-md border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2"
            >
              <span className={[
                'shrink-0 text-xs font-semibold px-1.5 py-0.5 rounded',
                item.kind === 'escalation'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                  : item.kind === 'decision'
                  ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
                  : 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
              ].join(' ')}>
                {item.kind === 'escalation' ? 'ESC' : item.kind === 'decision' ? 'DEC' : 'SUG'}
              </span>
              <span className="flex-1 text-sm text-gray-700 dark:text-gray-200 truncate">{item.label}</span>
              {item.kind === 'escalation' && (
                <Link href="/escalations" className="shrink-0 text-xs font-medium px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700 transition-colors">
                  Review
                </Link>
              )}
              {item.kind === 'decision' && (
                <button
                  onClick={() => handleDecisionDismiss(item.id)}
                  disabled={acting.has(item.id)}
                  className="shrink-0 text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Dismiss
                </button>
              )}
              {item.kind === 'suggestion' && (
                <div className="flex shrink-0 gap-1">
                  <Link href="/suggestions" className="text-xs px-2 py-1 rounded bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-800 transition-colors">
                    Review
                  </Link>
                  <button
                    onClick={() => handleSuggestionReject(item.id)}
                    disabled={acting.has(item.id)}
                    className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    ✕
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

**Step 3: Verify it compiles**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```
Expected: no type errors.

**Step 4: Smoke test in browser**

```bash
make dashboard
```
Navigate to `http://localhost:6987/occc/mission-control`. AttentionQueue should render with "Loading…" then either "All clear ✓" or items. No console errors about `setInterval`.

**Step 5: Commit**

```bash
git add packages/dashboard/src/components/mission-control/AttentionQueue.tsx
git commit -m "feat(mission-control): migrate AttentionQueue from setInterval to SWR hooks"
```

---

## STREAM 2: LiveEventFeed Robustness

### Task 5: Add `/api/events/latest` endpoint

**Files:**
- Create: `packages/dashboard/src/app/api/events/latest/route.ts`
- Reference: `packages/dashboard/src/app/api/events/route.ts` (has module-level `ringBuffer`)

The existing `ringBuffer` is declared at module scope in `events/route.ts` as `const ringBuffer: { id: number; data: string }[]`. The new endpoint imports and reads it directly.

**Step 1: Check the ring buffer is exported or can be shared**

```bash
grep -n "export\|ringBuffer" packages/dashboard/src/app/api/events/route.ts
```
Expected: `ringBuffer` is NOT exported (it's `const`, not `export const`). You need to export it.

**Step 2: Export the ring buffer from events/route.ts**

In `packages/dashboard/src/app/api/events/route.ts`, change line 9 from:
```ts
const ringBuffer: { id: number; data: string }[] = [];
```
to:
```ts
export const ringBuffer: { id: number; data: string }[] = [];
```

**Step 3: Create the latest endpoint**

```ts
// packages/dashboard/src/app/api/events/latest/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { ringBuffer } from '../route';

export const dynamic = 'force-dynamic';

export interface LiveEventLatest {
  id: number;
  type: string;
  project_id?: string;
  task_id?: string;
  message?: string;
  ts: number;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limit = Math.min(200, Math.max(1, parseInt(searchParams.get('limit') ?? '50', 10)));

  const slice = ringBuffer.slice(-limit);
  const events: LiveEventLatest[] = [];

  for (const entry of slice) {
    try {
      const parsed = JSON.parse(entry.data);
      events.push({
        id: entry.id,
        type: parsed.type ?? 'unknown',
        project_id: parsed.project_id,
        task_id: parsed.task_id,
        message: parsed.message ?? parsed.description,
        ts: Date.now(), // ring buffer doesn't store original ts; use approximate
      });
    } catch {
      // skip malformed entries
    }
  }

  return NextResponse.json({ events });
}
```

**Step 4: Verify it compiles**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -20
```

**Step 5: Test the endpoint manually**

```bash
make dashboard
# In another terminal:
curl -s "http://localhost:6987/occc/api/events/latest?limit=5" | jq .
```
Expected: `{ "events": [] }` (or events if socket is active).

**Step 6: Commit**

```bash
git add packages/dashboard/src/app/api/events/route.ts \
        packages/dashboard/src/app/api/events/latest/route.ts
git commit -m "feat(mission-control): add /api/events/latest endpoint with ring buffer export"
```

---

### Task 6: Create `useLiveEvents` hook with connection state machine

**Files:**
- Create: `packages/dashboard/src/lib/hooks/useLiveEvents.ts`

**Step 1: Write the hook**

```ts
// packages/dashboard/src/lib/hooks/useLiveEvents.ts
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import useSWR from 'swr';
import { apiPath, apiJson } from '@/lib/api-client';
import type { LiveEventLatest } from '@/app/api/events/latest/route';

export type LiveEventStatus = 'connecting' | 'live' | 'reconnecting' | 'offline';

export interface LiveEvent {
  id: number;
  type: string;
  project_id?: string;
  task_id?: string;
  message?: string;
  rawAt: number;
}

const MAX_EVENTS = 50;
const OFFLINE_TIMEOUT_MS = 4000;
const RECONNECT_INTERVAL_MS = 10000;

interface FallbackResponse {
  events: LiveEventLatest[];
}

export function useLiveEvents(projectId: string | null): {
  events: LiveEvent[];
  status: LiveEventStatus;
} {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [status, setStatus] = useState<LiveEventStatus>('connecting');
  const nextIdRef = useRef(0);
  const statusRef = useRef<LiveEventStatus>('connecting');
  const esRef = useRef<EventSource | null>(null);
  const offlineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const updateStatus = useCallback((s: LiveEventStatus) => {
    statusRef.current = s;
    setStatus(s);
  }, []);

  const connect = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    const prevStatus = statusRef.current;
    updateStatus(prevStatus === 'live' ? 'reconnecting' : 'connecting');

    // Set offline fallback timer if we don't reach 'live' within timeout
    if (offlineTimerRef.current) clearTimeout(offlineTimerRef.current);
    offlineTimerRef.current = setTimeout(() => {
      if (statusRef.current !== 'live') {
        updateStatus('offline');
      }
    }, OFFLINE_TIMEOUT_MS);

    const es = new EventSource(apiPath('/api/events'));
    esRef.current = es;

    es.onopen = () => {
      if (offlineTimerRef.current) {
        clearTimeout(offlineTimerRef.current);
        offlineTimerRef.current = null;
      }
      updateStatus('live');
    };

    es.addEventListener('message', (e) => {
      try {
        const parsed = JSON.parse(e.data);
        if (projectId && parsed.project_id && parsed.project_id !== projectId) return;
        const entry: LiveEvent = {
          id: nextIdRef.current++,
          type: parsed.type ?? 'unknown',
          project_id: parsed.project_id,
          task_id: parsed.task_id,
          message: parsed.message ?? parsed.description,
          rawAt: Date.now(),
        };
        setEvents(prev => [...prev.slice(-(MAX_EVENTS - 1)), entry]);
      } catch {
        // ignore
      }
    });

    es.onerror = () => {
      if (statusRef.current === 'live') {
        updateStatus('reconnecting');
      }
    };
  }, [projectId, updateStatus]);

  useEffect(() => {
    connect();

    // Periodic reconnect attempt when offline
    reconnectTimerRef.current = setInterval(() => {
      if (statusRef.current === 'offline' || statusRef.current === 'reconnecting') {
        connect();
      }
    }, RECONNECT_INTERVAL_MS);

    return () => {
      esRef.current?.close();
      esRef.current = null;
      if (offlineTimerRef.current) clearTimeout(offlineTimerRef.current);
      if (reconnectTimerRef.current) clearInterval(reconnectTimerRef.current);
    };
  }, [connect]);

  // Fallback polling when offline
  const { data: fallbackData } = useSWR<FallbackResponse>(
    status === 'offline' ? `/api/events/latest?limit=50` : null,
    (url: string) => apiJson<FallbackResponse>(url),
    { refreshInterval: 3000 }
  );

  // When fallback data arrives and we're still offline, surface it
  useEffect(() => {
    if (status !== 'offline' || !fallbackData?.events?.length) return;
    const fallbackEvents: LiveEvent[] = fallbackData.events
      .filter(e => !projectId || !e.project_id || e.project_id === projectId)
      .map(e => ({
        id: nextIdRef.current++,
        type: e.type,
        project_id: e.project_id,
        task_id: e.task_id,
        message: e.message,
        rawAt: e.ts,
      }));
    // Replace displayed events with fallback snapshot (deduplicated by type)
    setEvents(fallbackEvents.slice(-MAX_EVENTS));
  }, [fallbackData, status, projectId]);

  return { events, status };
}
```

**Step 2: Verify it compiles**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```

**Step 3: Commit**

```bash
git add packages/dashboard/src/lib/hooks/useLiveEvents.ts
git commit -m "feat(mission-control): add useLiveEvents hook with connection state machine"
```

---

### Task 7: Refactor LiveEventFeed to use hook + status pill

**Files:**
- Modify: `packages/dashboard/src/components/mission-control/LiveEventFeed.tsx`

**Step 1: Replace the file**

```tsx
'use client';

import { useRef, useState, useEffect } from 'react';
import { useProject } from '@/context/ProjectContext';
import { useLiveEvents, type LiveEventStatus } from '@/lib/hooks/useLiveEvents';

const TYPE_COLORS: Record<string, string> = {
  task_created: 'bg-blue-500',
  task_started: 'bg-amber-500',
  task_completed: 'bg-green-500',
  task_failed: 'bg-red-500',
  task_escalated: 'bg-purple-500',
  container_started: 'bg-cyan-500',
  container_stopped: 'bg-gray-400',
};

const STATUS_PILL: Record<LiveEventStatus, { label: string; className: string }> = {
  connecting: {
    label: 'connecting…',
    className: 'border-gray-200 dark:border-gray-600 text-gray-500',
  },
  live: {
    label: 'live',
    className: 'bg-green-100 border-green-300 text-green-700 dark:bg-green-900 dark:border-green-700 dark:text-green-300',
  },
  reconnecting: {
    label: 'reconnecting…',
    className: 'bg-amber-100 border-amber-300 text-amber-700 dark:bg-amber-900 dark:border-amber-700 dark:text-amber-300',
  },
  offline: {
    label: 'offline (polling)',
    className: 'bg-red-100 border-red-300 text-red-700 dark:bg-red-900 dark:border-red-700 dark:text-red-300',
  },
};

function relativeTime(ms: number): string {
  const diff = Math.floor((Date.now() - ms) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export default function LiveEventFeed() {
  const { projectId } = useProject();
  const { events, status } = useLiveEvents(projectId);
  const [paused, setPaused] = useState(false);
  const [filterTasks, setFilterTasks] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!paused && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, paused]);

  const displayed = filterTasks ? events.filter(e => e.type.startsWith('task_')) : events;
  const pill = STATUS_PILL[status];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 flex flex-col gap-3 min-h-0">
      <div className="flex items-center justify-between flex-shrink-0">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
          Live Event Feed
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setFilterTasks(f => !f)}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
              filterTasks
                ? 'bg-blue-100 border-blue-300 text-blue-700 dark:bg-blue-900 dark:border-blue-700 dark:text-blue-300'
                : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'
            }`}
          >
            tasks
          </button>
          <button
            onClick={() => setPaused(p => !p)}
            className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
              paused
                ? 'bg-amber-100 border-amber-300 text-amber-700 dark:bg-amber-900 dark:border-amber-700 dark:text-amber-300'
                : 'border-gray-200 dark:border-gray-600 text-gray-500 hover:border-gray-300'
            }`}
          >
            {paused ? 'paused' : 'live'}
          </button>
          {/* Connection status pill */}
          <span className={`text-xs px-2 py-0.5 rounded-full border ${pill.className}`}>
            {pill.label}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1 min-h-0 max-h-48">
        {displayed.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">
            {status === 'offline' ? 'Offline — waiting for events…' : 'Waiting for events…'}
          </p>
        )}
        {displayed.map(ev => (
          <div key={ev.id} className="flex items-start gap-2 text-xs">
            <span
              className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${TYPE_COLORS[ev.type] ?? 'bg-gray-400'}`}
              role="img"
              aria-label={ev.type}
            />
            <span className="text-gray-700 dark:text-gray-300 flex-1 truncate">
              {ev.task_id && (
                <span className="font-mono text-gray-500">{ev.task_id} </span>
              )}
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

**Step 2: Verify it compiles**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```

**Step 3: Smoke test**

```bash
make dashboard
```
Navigate to mission-control. The Live Event Feed header should now show a "connecting…" pill that changes to "live" when the socket connects, or "offline (polling)" when it doesn't.

**Step 4: Commit**

```bash
git add packages/dashboard/src/components/mission-control/LiveEventFeed.tsx
git commit -m "feat(mission-control): LiveEventFeed connection state machine + offline fallback UI"
```

---

## STREAM 3: Cost/Token Tracking

### Task 8: Create `usage-logger.ts` in gateway

**Files:**
- Create: `openclaw/src/infra/usage-logger.ts`

This module subscribes to `model.usage` diagnostic events and appends one NDJSON line per event to `usage.ndjson` in the project workspace.

**Step 1: Find the expandHome utility**

```bash
grep -rn "expandHome\|homedir\|OPENCLAW_ROOT" openclaw/src/infra/ | grep -v test | head -10
```
Note the correct import path.

**Step 2: Write the module**

```ts
// openclaw/src/infra/usage-logger.ts
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { onDiagnosticEvent, type DiagnosticUsageEvent } from "../infra/diagnostic-events.js";

function resolveUsagePath(projectId: string): string {
  const root = process.env.OPENCLAW_ROOT ?? path.join(os.homedir(), ".openclaw");
  return path.join(root, "workspace", ".openclaw", projectId, "usage.ndjson");
}

function appendUsageLine(projectId: string, line: string): void {
  const filePath = resolveUsagePath(projectId);
  try {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.appendFileSync(filePath, line + "\n", "utf-8");
  } catch (err) {
    // Best-effort: log warning but never throw
    console.warn("[usage-logger] Failed to append usage line:", err);
  }
}

function formatUsageEvent(evt: DiagnosticUsageEvent): string | null {
  // Resolve projectId from sessionKey (format: "<projectId>/<agentId>" or similar)
  // Fall back to "unknown" if not derivable
  const projectId = evt.channel?.split("/")?.[0] ?? "unknown";
  if (!projectId || projectId === "unknown") return null;

  const entry = {
    ts: new Date(evt.ts).toISOString(),
    type: "model.usage",
    projectId,
    taskId: evt.sessionKey ?? undefined,
    agentId: evt.sessionId ?? undefined,
    runId: undefined as string | undefined, // not available in DiagnosticUsageEvent
    model: evt.model ?? undefined,
    usage: {
      inputTokens: evt.usage.input ?? 0,
      outputTokens: evt.usage.output ?? 0,
      totalTokens: evt.usage.total ?? (evt.usage.input ?? 0) + (evt.usage.output ?? 0),
    },
    costUsd: evt.costUsd ?? 0,
  };

  return JSON.stringify(entry);
}

export function initUsageLogger(): () => void {
  const unsubscribe = onDiagnosticEvent((evt) => {
    if (evt.type !== "model.usage") return;
    const line = formatUsageEvent(evt as DiagnosticUsageEvent);
    if (line) {
      const projectId = (evt as DiagnosticUsageEvent).channel?.split("/")?.[0] ?? "unknown";
      appendUsageLine(projectId, line);
    }
  });
  return unsubscribe;
}
```

**Important note on projectId resolution:** The `channel` field in `DiagnosticUsageEvent` is the channel/session identifier from the gateway. Its format depends on your agent configuration. After writing this, verify what `channel` looks like in a real run by checking:

```bash
grep -n "channel\|sessionKey" openclaw/src/auto-reply/reply/agent-runner.ts | head -20
```

Adjust `formatUsageEvent` projectId extraction if the channel format is different.

**Step 3: Compile check**

```bash
cd openclaw && npx tsc --noEmit 2>&1 | head -30
```

**Step 4: Write a unit test**

```ts
// openclaw/src/infra/usage-logger.test.ts
import { describe, it, expect, vi, afterEach } from "vitest";
import fs from "node:fs";
import { emitDiagnosticEvent, resetDiagnosticEventsForTest } from "./diagnostic-events.js";

// We need to test that emitting a model.usage event triggers a file write.
// We'll mock fs.appendFileSync and fs.mkdirSync.

vi.mock("node:fs");

describe("usage-logger", () => {
  afterEach(() => {
    resetDiagnosticEventsForTest();
    vi.resetAllMocks();
  });

  it("appends a NDJSON line when a model.usage event is emitted with a channel", async () => {
    const { initUsageLogger } = await import("./usage-logger.js");
    const stop = initUsageLogger();

    emitDiagnosticEvent({
      type: "model.usage",
      channel: "pumplai/pumplai_pm",
      model: "claude-sonnet-4-6",
      usage: { input: 100, output: 50, total: 150 },
      costUsd: 0.005,
    });

    expect(fs.appendFileSync).toHaveBeenCalledOnce();
    const [, content] = (fs.appendFileSync as ReturnType<typeof vi.fn>).mock.calls[0];
    const parsed = JSON.parse((content as string).trim());
    expect(parsed.type).toBe("model.usage");
    expect(parsed.projectId).toBe("pumplai");
    expect(parsed.usage.totalTokens).toBe(150);
    expect(parsed.costUsd).toBe(0.005);

    stop();
  });

  it("does nothing when channel is missing (no projectId derivable)", async () => {
    const { initUsageLogger } = await import("./usage-logger.js");
    const stop = initUsageLogger();

    emitDiagnosticEvent({
      type: "model.usage",
      usage: { input: 10, output: 5, total: 15 },
      costUsd: 0.001,
    });

    expect(fs.appendFileSync).not.toHaveBeenCalled();
    stop();
  });

  it("does not throw if appendFileSync fails", async () => {
    const { initUsageLogger } = await import("./usage-logger.js");
    vi.mocked(fs.appendFileSync).mockImplementationOnce(() => { throw new Error("disk full"); });
    const stop = initUsageLogger();

    expect(() => {
      emitDiagnosticEvent({
        type: "model.usage",
        channel: "myproject/agent",
        usage: { input: 1, output: 1, total: 2 },
        costUsd: 0,
      });
    }).not.toThrow();

    stop();
  });
});
```

**Step 5: Run the tests**

```bash
cd openclaw && npx vitest run src/infra/usage-logger.test.ts
```
Expected: 3 tests pass. If the test runner for this package differs, check `openclaw/package.json` for the `"test"` script.

**Step 6: Commit**

```bash
git add openclaw/src/infra/usage-logger.ts openclaw/src/infra/usage-logger.test.ts
git commit -m "feat(mission-control): add usage-logger that appends model.usage events to NDJSON"
```

---

### Task 9: Wire `initUsageLogger()` at gateway startup

**Files:**
- Modify: `openclaw/src/gateway/server.impl.ts`

**Step 1: Find the exact line to insert after**

```bash
grep -n "startDiagnosticHeartbeat\|diagnosticsEnabled\|initSubagentRegistry" openclaw/src/gateway/server.impl.ts
```
Expected: shows lines ~231-239. Insert `initUsageLogger()` after the diagnostics block, before `initSubagentRegistry`.

**Step 2: Add the import**

Near the top of `server.impl.ts`, add with the other infra imports:

```ts
import { initUsageLogger } from "./infra/usage-logger.js"; // add this
// (adjust relative path if needed — check existing import patterns in this file)
```

Actually, since this is `gateway/server.impl.ts`, the path to infra is:
```ts
import { initUsageLogger } from "../infra/usage-logger.js";
```

**Step 3: Call it at startup**

After line ~234 (after the `startDiagnosticHeartbeat` block), add:

```ts
// Start usage logger — appends model.usage events to per-project usage.ndjson
const stopUsageLogger = initUsageLogger();
```

**Step 4: Store the stop function for clean shutdown**

Find where other cleanup functions are called on server stop (search for `stopDiagnosticHeartbeat` or the server's shutdown handler). Add `stopUsageLogger()` there.

```bash
grep -n "stopDiagnostic\|onShutdown\|cleanup\|SIGTERM" openclaw/src/gateway/server.impl.ts | head -10
```

**Step 5: Compile check**

```bash
cd openclaw && npx tsc --noEmit 2>&1 | head -20
```

**Step 6: Commit**

```bash
git add openclaw/src/gateway/server.impl.ts
git commit -m "feat(mission-control): wire initUsageLogger at gateway startup"
```

---

### Task 10: Add `readTodayUsage` to `/api/metrics` + update types

**Files:**
- Modify: `packages/dashboard/src/lib/types.ts` (add three fields to `MetricsResponse`)
- Modify: `packages/dashboard/src/app/api/metrics/route.ts`

**Step 1: Update MetricsResponse type**

In `packages/dashboard/src/lib/types.ts`, find the `MetricsResponse` interface and add three fields:

```ts
export interface MetricsResponse {
  // ... all existing fields unchanged ...
  todayTokens: number;      // 0 if file absent or no usage today
  todayCostUsd: number;     // 0 if file absent or no cost today
  hasUsageLog: boolean;     // false if usage.ndjson does not exist yet
}
```

**Step 2: Write a test for the Oslo date helper**

Create `packages/dashboard/src/app/api/metrics/usage-aggregator.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { getOsloDateString, aggregateTodayUsage } from './usage-aggregator';

describe('getOsloDateString', () => {
  it('formats a UTC date as Oslo date string', () => {
    // UTC midnight Jan 1 = Dec 31 in Oslo (UTC+1 in winter)
    const utcMidnight = new Date('2026-01-01T00:00:00.000Z');
    const result = getOsloDateString(utcMidnight);
    expect(result).toBe('2025-12-31');
  });

  it('formats an Oslo daytime correctly', () => {
    const noon = new Date('2026-03-05T11:00:00.000Z'); // 12:00 Oslo time (UTC+1)
    const result = getOsloDateString(noon);
    expect(result).toBe('2026-03-05');
  });
});

describe('aggregateTodayUsage', () => {
  it('sums tokens and cost for today only', () => {
    const today = getOsloDateString(new Date());
    const lines = [
      JSON.stringify({ type: 'model.usage', ts: new Date().toISOString(), usage: { totalTokens: 100 }, costUsd: 0.01 }),
      JSON.stringify({ type: 'model.usage', ts: '2020-01-01T00:00:00.000Z', usage: { totalTokens: 999 }, costUsd: 9.99 }),
    ];
    const result = aggregateTodayUsage(lines);
    expect(result.tokens).toBe(100);
    expect(result.costUsd).toBeCloseTo(0.01);
  });

  it('skips malformed lines', () => {
    const lines = ['not json', '', JSON.stringify({ type: 'model.usage', ts: new Date().toISOString(), usage: { totalTokens: 50 }, costUsd: 0.005 })];
    const result = aggregateTodayUsage(lines);
    expect(result.tokens).toBe(50);
  });

  it('returns zeros for empty input', () => {
    const result = aggregateTodayUsage([]);
    expect(result.tokens).toBe(0);
    expect(result.costUsd).toBe(0);
  });
});
```

**Step 3: Run to verify it fails**

```bash
cd packages/dashboard && npx vitest run src/app/api/metrics/usage-aggregator.test.ts
```
Expected: FAIL — file doesn't exist yet.

**Step 4: Create `usage-aggregator.ts`**

```ts
// packages/dashboard/src/app/api/metrics/usage-aggregator.ts
export function getOsloDateString(date: Date): string {
  // sv-SE locale produces YYYY-MM-DD format — robust for string comparison
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Oslo' }).format(date);
}

export interface UsageAggregate {
  tokens: number;
  costUsd: number;
}

export function aggregateTodayUsage(lines: string[]): UsageAggregate {
  const today = getOsloDateString(new Date());
  let tokens = 0;
  let costUsd = 0;

  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const entry = JSON.parse(line);
      if (entry.type !== 'model.usage') continue;
      if (!entry.ts) continue;
      if (getOsloDateString(new Date(entry.ts)) !== today) continue;
      tokens += entry.usage?.totalTokens ?? 0;
      costUsd += entry.costUsd ?? 0;
    } catch {
      // skip malformed
    }
  }

  return { tokens, costUsd };
}
```

**Step 5: Run tests again**

```bash
cd packages/dashboard && npx vitest run src/app/api/metrics/usage-aggregator.test.ts
```
Expected: 5 tests pass.

**Step 6: Integrate into `/api/metrics/route.ts`**

At the top of `route.ts`, add:
```ts
import { aggregateTodayUsage } from './usage-aggregator';
```

Inside the `handler` function, after the existing metrics computation, add:

```ts
// Read today's usage from NDJSON log
let todayTokens = 0;
let todayCostUsd = 0;
let hasUsageLog = false;

try {
  const usagePath = path.join(
    OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'usage.ndjson'
  );
  const raw = await fs.readFile(usagePath, 'utf-8');
  hasUsageLog = true;
  const agg = aggregateTodayUsage(raw.split('\n'));
  todayTokens = agg.tokens;
  todayCostUsd = agg.costUsd;
} catch (err: unknown) {
  if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
    console.error('[metrics] Failed to read usage.ndjson:', err);
  }
  // ENOENT = file not created yet, hasUsageLog stays false
}
```

And add the new fields to the `response` object:

```ts
const response: MetricsResponse = {
  // ... existing fields ...
  todayTokens,
  todayCostUsd,
  hasUsageLog,
};
```

**Step 7: Compile check**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -20
```

**Step 8: Commit**

```bash
git add packages/dashboard/src/lib/types.ts \
        packages/dashboard/src/app/api/metrics/usage-aggregator.ts \
        packages/dashboard/src/app/api/metrics/usage-aggregator.test.ts \
        packages/dashboard/src/app/api/metrics/route.ts
git commit -m "feat(mission-control): add usage.ndjson aggregation to /api/metrics"
```

---

### Task 11: Unlock cost display in SwarmStatusPanel

**Files:**
- Modify: `packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx`

**Step 1: Replace the null placeholder lines**

Find and replace lines ~26-27:
```ts
// Before:
const todayCostUsdVal = null as number | null;
const todayTokensVal = null as number | null;
```

Replace with:
```ts
const showCost = metrics?.hasUsageLog === true;
const todayCostUsdVal = metrics?.todayCostUsd ?? null;
const todayTokensVal = metrics?.todayTokens ?? null;
```

**Step 2: Update the guard condition**

Find the existing guard (line ~90):
```tsx
{todayCostUsdVal != null && todayTokensVal != null && (
```

Replace with:
```tsx
{showCost && todayCostUsdVal != null && todayTokensVal != null && (
```

**Step 3: Compile check**

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -20
```

**Step 4: Smoke test**

```bash
make dashboard
```
Navigate to mission-control. SwarmStatus should:
- Show "—" for cost if gateway hasn't written any `usage.ndjson` yet (`hasUsageLog: false`)
- Show actual cost/tokens once the file exists and has today's entries

**Step 5: Commit**

```bash
git add packages/dashboard/src/components/mission-control/SwarmStatusPanel.tsx
git commit -m "feat(mission-control): unlock cost/token display in SwarmStatusPanel"
```

---

## Final Verification

**Step 1: Full type check**

```bash
cd packages/dashboard && pnpm tsc --noEmit
cd /path/to/openclaw && npx tsc --noEmit
```
Expected: zero errors.

**Step 2: Run all dashboard tests**

```bash
cd packages/dashboard && pnpm test
```
Expected: all pass including new usage-aggregator tests.

**Step 3: Run gateway tests**

```bash
cd openclaw && npx vitest run src/infra/usage-logger.test.ts
```
Expected: 3 tests pass.

**Step 4: End-to-end smoke**

```bash
make dashboard
```
- `http://localhost:6987/occc/mission-control`
- AttentionQueue: items load, no setInterval in React DevTools, error states work
- LiveEventFeed: status pill shows "connecting…" → "live" (or "offline (polling)")
- SwarmStatusPanel: cost row hidden until `usage.ndjson` exists, then shows real data
- TaskPulse: unchanged, still works
