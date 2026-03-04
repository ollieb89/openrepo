# Phase 74: Dashboard Streaming UI — Design

**Date:** 2026-03-05
**Phase:** 74
**Requirements:** DASH-01, DASH-02, DASH-03
**Depends on:** Phase 71 (L3 Output Streaming)

---

## Goal

Users can open any active task on the task board and watch its L3 output stream live in a terminal-style panel. Completed and failed tasks show stored output from the activity log.

---

## Architecture

Three focused changes, all in `packages/dashboard/`:

| File | Change |
|------|--------|
| `src/components/LogViewer.tsx` | Add `staticLines` prop for non-active tasks |
| `src/components/tasks/TaskTerminalPanel.tsx` | New: compact header + LogViewer wrapper |
| `src/components/tasks/TaskBoard.tsx` | Replace existing detail panel with TaskTerminalPanel |

---

## Data Flow

```
User clicks TaskCard
  → setSelectedTask(task)
  → TaskBoard renders <TaskTerminalPanel task={selectedTask} onClose={...} />

TaskTerminalPanel
  → isActive = task.status === 'in_progress' || task.status === 'starting'
  → if isActive: passes taskId to LogViewer → SSE /api/events → TASK_OUTPUT filtered by task_id
  → if not active: maps task.activity_log to LogEntry[] → passes as staticLines to LogViewer

LogViewer (extended)
  → if staticLines && !isActive: renders static lines, no SSE connection opened
  → if isActive: EventSource('/api/events'), filters TASK_OUTPUT by task_id, appends lines
  → auto-scroll and pause behavior (see below)
```

---

## Component Design

### `TaskTerminalPanel.tsx`

```
┌──────────────────────┬──────────────────────────────┐
│  Kanban columns      │  ▶ task-abc-123   [running] × │  ← compact header
│                      │  ──────────────────────────── │
│  [Task A]  [Task B]  │  $ Cloning repository...      │
│  [Task C]            │  > Step 1 done                │
│                      │  > Installing deps            │
│                      │  stderr: warn: missing peer   │
│                      │                               │
│                      │  ↓ scroll to resume           │  ← scroll indicator
└──────────────────────┴──────────────────────────────┘
```

**Header:** task ID (monospace, truncated with ellipsis), `StatusBadge`, close button (`×`)
**Body:** dark background (`bg-gray-950`), `LogViewer` fills remaining height

### `LogViewer.tsx` changes

New prop: `staticLines?: LogEntry[]`

Behavior:
- If `staticLines` provided and task is not active → render static lines, skip SSE setup
- If active → existing SSE logic unchanged (EventSource, filter, reconnect)

Empty states:
- Active, no output yet: "Waiting for output..."
- Not active, no activity_log: "No output recorded"

---

## Auto-Scroll Behavior

- `autoScrollRef = useRef(true)` — enabled on mount
- `onScroll`: compare `scrollTop + clientHeight ≥ scrollHeight - 20px`
  - At bottom → `autoScrollRef.current = true`
  - Scrolled up → `autoScrollRef.current = false`
- `useEffect([logs])`: if `autoScrollRef.current`, set `container.scrollTop = scrollHeight`
- "↓ scroll to resume" badge: visible when auto-scroll paused; clicking scrolls to bottom and re-enables

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| SSE disconnects | Existing exponential backoff reconnect in LogViewer handles it |
| Active task, no output yet | "Waiting for output..." placeholder |
| Completed task, no activity_log | "No output recorded" |
| Panel open latency | Renders instantly (< 16ms); SSE connects async in background |

---

## Success Criteria Mapping

| Criteria | Implementation |
|----------|---------------|
| DASH-01: Terminal-style output panel renders live L3 output per active task | LogViewer with SSE TASK_OUTPUT events |
| DASH-02: Click task row opens stream within 500ms | Panel renders synchronously on click |
| DASH-03: Auto-scroll with pause-on-scroll-up and resume-on-scroll-to-bottom | autoScrollRef + onScroll + "↓ resume" badge |

---

## Files Changed

1. `packages/dashboard/src/components/LogViewer.tsx` — add `staticLines` prop + empty states
2. `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx` — new component
3. `packages/dashboard/src/components/tasks/TaskBoard.tsx` — replace detail panel with TaskTerminalPanel
