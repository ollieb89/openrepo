# Task Board Real-Time Updates Design

**Date:** 2026-03-05
**Status:** Approved

## Problem

`useTasks` polls `/api/tasks` every 3 seconds. The SSE bridge (`/api/events`) and `useEvents` hook already exist and receive real-time orchestrator events (`task.created`, `task.started`, `task.completed`, `task.failed`, etc.) but are not wired to task state. Task status changes appear up to 3s late.

## Approach

Event-triggered SWR revalidation. `useTasks` subscribes to `useEvents` and calls SWR `mutate()` immediately when any `task.*` event arrives for the current project. 3-second polling remains as a safety fallback.

## Changes

### `packages/dashboard/src/lib/hooks/useTasks.ts`

- Import `useEvents` from `@/hooks/useEvents`
- Import `useEffect` from React
- Destructure `mutate` from the `useSWR` return value
- Add `useEffect` watching `lastEvent`: if `lastEvent.type.startsWith('task.')`, call `mutate()`

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

  return { tasks: data?.tasks || [], isLoading, error };
}
```

## Files Changed

| File | Change |
|------|--------|
| `packages/dashboard/src/lib/hooks/useTasks.ts` | Add `useEvents` + `useEffect` for event-triggered revalidation |

Total: ~5 lines added, 0 new files.

## Behavior

- Task status changes visible within ~50ms of the orchestrator event (vs. up to 3s)
- SSE socket down → 3s polling keeps the board fresh
- Multiple rapid events → SWR deduplicates concurrent in-flight requests
- Cross-project event noise already filtered by `useEvents(projectId)`
- All consumers of `useTasks` benefit automatically (TaskBoard, etc.)
