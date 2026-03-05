# Task Board Real-Time Updates — 2026-03-05

## What was built
SSE-triggered SWR revalidation on the task board (`/tasks`). Task status changes now appear within ~50ms of the orchestrator event instead of up to 3s.

## Architecture decision
`useEvents` is called in `TaskBoard.tsx` (NOT inside `useTasks`). This ensures a single EventSource connection per page load regardless of how many consumers call `useTasks`.

**Why not in `useTasks`:** Every `useTasks` consumer (TaskBoard + AgentTree) would open its own EventSource connection, exhausting the browser's 6-connection-per-origin HTTP/1.1 limit.

## Key files changed
- `packages/dashboard/src/components/tasks/TaskBoard.tsx` — adds `useEvents`, `useSWRConfig`, `TASK_LIFECYCLE_EVENTS` Set, `useEffect` that calls global `mutate('/api/tasks?project=...')`
- `packages/dashboard/src/lib/hooks/useTasks.ts` — unchanged (simple SWR polling, `refreshInterval: 3000` kept as fallback)
- `packages/dashboard/src/hooks/useEvents.ts` — `console.error` → `console.warn` for expected connection failures

## Event filtering
`TASK_LIFECYCLE_EVENTS` (module-level constant in `TaskBoard.tsx`) contains only:
- `task.created`, `task.started`, `task.completed`, `task.failed`, `task.escalated`

**`task.output` is intentionally excluded** — it fires on every stdout line from L3 containers and would flood the API with refetch requests during active execution.

## SWR key
`/api/tasks?project=${projectId}` — matches exactly between `useTasks` SWR key and the global `mutate()` call in `TaskBoard`.

## Bug fixed
`useEvents.ts:37` — `console.error('EventSource error', e)` was logging `{}` (empty EventSource error object) as a console error when the orchestrator socket is unavailable. Changed to `console.warn` with descriptive message. This is expected behavior when orchestrator is not running.

## Commits
- `00f6c87` fix(tasks): move SSE revalidation to TaskBoard, filter to lifecycle events only
- `e01d773` fix(events): downgrade EventSource error to warn

## Design docs
- `docs/plans/2026-03-05-tasks-realtime-updates-design.md`
- `docs/plans/2026-03-05-tasks-realtime-updates.md`
