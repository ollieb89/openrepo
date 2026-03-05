# Task Board Real-Time Updates Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire the existing SSE event bridge into `useTasks` so task status changes appear immediately instead of on the 3-second polling clock.

**Architecture:** `useTasks` subscribes to `useEvents(projectId)`. When any `task.*` event arrives, it calls SWR's `mutate()` to immediately re-fetch. 3-second polling stays as a fallback when SSE is unavailable.

**Tech Stack:** React, SWR, TypeScript, existing `useEvents` hook (`src/hooks/useEvents.ts`), existing `useTasks` hook (`src/lib/hooks/useTasks.ts`).

---

### Task 1: Update `useTasks` to trigger revalidation on SSE task events

**Files:**
- Modify: `packages/dashboard/src/lib/hooks/useTasks.ts`

**Step 1: Read the current file**

Open `packages/dashboard/src/lib/hooks/useTasks.ts` and confirm it looks like:

```ts
import useSWR from 'swr';
import type { Task } from '@/lib/types';
import { apiJson } from '@/lib/api-client';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

export function useTasks(projectId: string | null) {
  const { data, error, isLoading } = useSWR<{ tasks: Task[] }>(
    projectId ? `/api/tasks?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 3000 }
  );

  return {
    tasks: data?.tasks || [],
    isLoading,
    error,
  };
}
```

**Step 2: Write the updated file**

Replace the entire file with:

```ts
import useSWR from 'swr';
import { useEffect } from 'react';
import type { Task } from '@/lib/types';
import { apiJson } from '@/lib/api-client';
import { useEvents } from '@/hooks/useEvents';

const fetcher = <T>(url: string): Promise<T> => apiJson<T>(url);

export function useTasks(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<{ tasks: Task[] }>(
    projectId ? `/api/tasks?project=${projectId}` : null,
    fetcher,
    { refreshInterval: 3000 }
  );

  const { lastEvent } = useEvents(projectId ?? undefined);

  useEffect(() => {
    if (!lastEvent) return;
    if (lastEvent.type.startsWith('task.')) mutate();
  }, [lastEvent, mutate]);

  return {
    tasks: data?.tasks || [],
    isLoading,
    error,
  };
}
```

Key changes:
- Added `useEffect` import from React
- Added `useEvents` import from `@/hooks/useEvents`
- Destructured `mutate` from `useSWR` return value
- Added `useEffect` that calls `mutate()` on any `task.*` event

**Step 3: Check TypeScript compiles cleanly**

```bash
cd packages/dashboard && npx tsc --noEmit 2>&1 | grep -E "useTasks|useEvents|error TS"
```

Expected: no output (no errors).

**Step 4: Commit**

```bash
git add packages/dashboard/src/lib/hooks/useTasks.ts
git commit -m "feat(tasks): trigger immediate SWR revalidation on SSE task events"
```

---

### Task 2: Smoke test the integration

**Files:** none (verification only)

**Step 1: Start the dashboard**

```bash
make dashboard
```

Open http://localhost:6987/tasks in a browser.

**Step 2: Verify SSE connection**

Open browser DevTools → Network tab → filter by "events". You should see a persistent `/api/events` request with `text/event-stream` content type and status 200 (or a connection error if the socket isn't running — that's expected in dev if orchestrator isn't running).

**Step 3: Verify fast update (if orchestrator is running)**

Trigger a task state change via the orchestrator (or via `openclaw` CLI). Confirm the task board updates within ~1 second instead of up to 3 seconds.

**Step 4: Verify fallback polling (with SSE down)**

If the orchestrator socket is not running, the event stream will show an error in the console. Confirm the task board still updates on the 3-second polling interval (no regression).

---

## Summary

| File | Lines changed | Purpose |
|------|--------------|---------|
| `packages/dashboard/src/lib/hooks/useTasks.ts` | +5 | Event-triggered revalidation |

Total: 5 lines added, 0 new files.
