# Phase 74: Dashboard Streaming UI — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire live L3 output into the task board — clicking a task opens a terminal-style panel with streaming output (active tasks) or stored activity log (completed/failed tasks).

**Architecture:** Add `staticLines`/`isActive`/`hideHeader` props to the existing `LogViewer` component; create a `TaskTerminalPanel` wrapper that handles mode selection and provides the compact header; update `TaskBoard` to show `TaskTerminalPanel` instead of the old detail panel. Auto-scroll with pause-on-scroll-up and resume-on-scroll-to-bottom is added to `LogViewer`.

**Tech Stack:** React, Next.js App Router, SSE (`EventSource`), Tailwind CSS, TypeScript

---

## Context

- **Event pipe is already wired:** Phase 71 built L3 stdout/stderr → `TASK_OUTPUT` events → Unix socket → SSE `/api/events` → browser.
- **`LogViewer.tsx`** already connects to `/api/events`, filters by `task_id`, and handles reconnect with exponential backoff.
- **Auto-scroll** currently always scrolls to bottom (no pause/resume). We're adding that.
- **`TaskActivityEntry`** has fields `{ timestamp: number; status: string; entry: string }` — `timestamp` is Unix seconds (multiply by 1000 for `Date`).

### Key files
| File | Role |
|------|------|
| `packages/dashboard/src/components/LogViewer.tsx` | SSE consumer, terminal renderer — we extend this |
| `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx` | New: compact header + LogViewer |
| `packages/dashboard/src/components/tasks/TaskBoard.tsx` | Replace detail panel with TaskTerminalPanel |
| `packages/dashboard/src/lib/types.ts` | `TaskActivityEntry`, `Task`, `TaskStatus` — read-only |
| `packages/dashboard/src/components/common/StatusBadge.tsx` | `<StatusBadge status={...} />` — use as-is |

### Run tests
```bash
cd packages/dashboard && pnpm test --watchAll=false 2>/dev/null || echo "no test runner configured"
```
(If no test runner: verify by running `pnpm dev` and checking the UI manually.)

---

## Task 1: Export `LogEntry` type and add `staticLines`/`isActive`/`hideHeader` props to LogViewer

**Files:**
- Modify: `packages/dashboard/src/components/LogViewer.tsx`

The existing `LogEntry` interface is file-private. We need to export it so `TaskTerminalPanel` can construct static entries from `activity_log`.

We also need three new props:
- `staticLines?: LogEntry[]` — pre-built lines to render (no SSE)
- `isActive?: boolean` — when `false` and `staticLines` provided, skips SSE setup
- `hideHeader?: boolean` — suppresses the built-in "Task Output / Connected / Clear" header

### Step 1: Open the file and read it
Read `packages/dashboard/src/components/LogViewer.tsx` (already read above — 191 lines).

### Step 2: Export the `LogEntry` interface

Change line 6 from:
```typescript
interface LogEntry {
```
to:
```typescript
export interface LogEntry {
```

### Step 3: Extend the `LogViewerProps` interface

Replace the existing `LogViewerProps` (lines 12–16):
```typescript
interface LogViewerProps {
  taskId?: string;
  /** @deprecated Use taskId instead */
  containerId?: string;
}
```
with:
```typescript
interface LogViewerProps {
  taskId?: string;
  /** @deprecated Use taskId instead */
  containerId?: string;
  /** Pre-built log lines for completed/failed tasks (skips SSE when isActive=false) */
  staticLines?: LogEntry[];
  /** When false and staticLines provided, SSE is not opened. Default: true when taskId present */
  isActive?: boolean;
  /** Hide the built-in header (title, connected status, clear button). Default: false */
  hideHeader?: boolean;
}
```

### Step 4: Destructure new props in the function signature

Change line 20 from:
```typescript
export default function LogViewer({ taskId, containerId }: LogViewerProps) {
```
to:
```typescript
export default function LogViewer({ taskId, containerId, staticLines, isActive = true, hideHeader = false }: LogViewerProps) {
```

### Step 5: Guard SSE setup with `isActive`

The `connectToEventSource` is called from `useEffect` at line 113. The effect at lines 96–126 currently calls `connectToEventSource()` whenever `effectiveTaskId` is set. Wrap the connect call:

Replace lines 110–113:
```typescript
    setLogs([]);
    setError(null);
    reconnectDelayRef.current = 1000;
    connectToEventSource();
```
with:
```typescript
    setLogs([]);
    setError(null);
    reconnectDelayRef.current = 1000;
    if (isActive !== false) {
      connectToEventSource();
    }
```

Also add `isActive` to the effect dependency array. Change line 126 from:
```typescript
  }, [effectiveTaskId, connectToEventSource]);
```
to:
```typescript
  }, [effectiveTaskId, connectToEventSource, isActive]);
```

### Step 6: Replace unconditional auto-scroll with pause/resume

Add a `autoScrollRef` to track whether auto-scroll is enabled, and a `userScrolled` state for the resume indicator. Also add `onScroll` handler.

After line 31 (`const isMountedRef = useRef(true);`), add:
```typescript
  const autoScrollRef = useRef(true);
  const [autoScrollPaused, setAutoScrollPaused] = useState(false);
```

Replace the existing auto-scroll `useEffect` (lines 128–132):
```typescript
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);
```
with:
```typescript
  useEffect(() => {
    if (autoScrollRef.current && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScroll = useCallback(() => {
    const el = logContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
    autoScrollRef.current = atBottom;
    setAutoScrollPaused(!atBottom);
  }, []);

  const resumeScroll = useCallback(() => {
    autoScrollRef.current = true;
    setAutoScrollPaused(false);
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, []);
```

### Step 7: Resolve the lines to render

Add a variable just before the `if (!effectiveTaskId)` guard (before line 134):
```typescript
  // Static lines take precedence when not active
  const displayLines = (!isActive && staticLines) ? staticLines : logs;
```

### Step 8: Update the render — hideHeader and scroll handler

Replace the full `return (...)` block (lines 142–189) with:

```typescript
  return (
    <div className="flex flex-col h-full bg-gray-950 font-mono text-xs">
      {!hideHeader && (
        <div className="px-4 py-2 border-b border-gray-700 flex justify-between items-center flex-shrink-0 bg-gray-900">
          <div>
            <span className="text-xs font-semibold text-gray-200">Task Output</span>
            {' · '}
            <span className={connected ? 'text-green-400' : 'text-gray-500'}>
              {connected ? 'Connected' : 'Reconnecting...'}
            </span>
            {' · '}
            <span className="text-gray-500">{displayLines.length} lines</span>
          </div>
          <button
            onClick={() => setLogs([])}
            className="text-xs text-gray-500 hover:text-gray-300 px-2 py-0.5 rounded"
          >
            Clear
          </button>
        </div>
      )}

      <div className="relative flex-1 overflow-hidden">
        <div
          ref={logContainerRef}
          onScroll={handleScroll}
          className="h-full overflow-y-auto p-3"
        >
          {displayLines.length === 0 ? (
            <div className="text-gray-600">
              {isActive === false ? 'No output recorded' : 'Waiting for output...'}
            </div>
          ) : (
            displayLines.map((log, index) => (
              <div key={index} className="mb-0.5 leading-relaxed">
                <span className="text-gray-600">
                  [{new Date(log.timestamp).toLocaleTimeString()}]
                </span>{' '}
                <span className={log.stream === 'stderr' ? 'text-red-400' : 'text-gray-100'}>
                  {log.line}
                </span>
              </div>
            ))
          )}
        </div>

        {autoScrollPaused && (
          <button
            onClick={resumeScroll}
            className="absolute bottom-3 right-3 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs px-3 py-1.5 rounded-full border border-gray-600 flex items-center gap-1 shadow-lg"
          >
            ↓ scroll to resume
          </button>
        )}
      </div>

      {error && (
        <div className="px-3 py-1 bg-red-900/30 border-t border-red-800 text-xs text-red-400 flex-shrink-0">
          {error}
        </div>
      )}
    </div>
  );
```

Also update the "no task selected" empty state (lines 134–140) to match the dark style:
```typescript
  if (!effectiveTaskId && !staticLines) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-950 text-gray-600 text-xs font-mono">
        Select a task to view output
      </div>
    );
  }
```

### Step 9: Verify the file compiles

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```
Expected: no errors referencing `LogViewer.tsx`

### Step 10: Commit

```bash
cd packages/dashboard
git add src/components/LogViewer.tsx
git commit -m "feat(74): extend LogViewer with staticLines, isActive, hideHeader, auto-scroll pause/resume"
```

---

## Task 2: Create `TaskTerminalPanel` component

**Files:**
- Create: `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx`

This component owns the compact header (task ID + status badge + close) and delegates terminal rendering to `LogViewer`.

### Step 1: Create the file

```typescript
'use client';

import type { Task, TaskActivityEntry } from '@/lib/types';
import type { LogEntry } from '@/components/LogViewer';
import LogViewer from '@/components/LogViewer';
import StatusBadge from '@/components/common/StatusBadge';

interface TaskTerminalPanelProps {
  task: Task;
  onClose: () => void;
}

function activityToLogEntries(entries: TaskActivityEntry[]): LogEntry[] {
  return entries.map(e => ({
    line: e.entry,
    stream: 'stdout' as const,
    timestamp: e.timestamp * 1000, // activity_log uses Unix seconds; LogViewer expects ms
  }));
}

export default function TaskTerminalPanel({ task, onClose }: TaskTerminalPanelProps) {
  const isActive = task.status === 'in_progress' || task.status === 'starting';
  const staticLines = isActive ? undefined : activityToLogEntries(task.activity_log);

  return (
    <div className="flex flex-col w-80 flex-shrink-0 border-l border-gray-800 bg-gray-950 h-full">
      {/* Compact header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800 flex-shrink-0 bg-gray-900 gap-2">
        <span className="font-mono text-xs text-gray-400 truncate flex-1" title={task.id}>
          {task.id}
        </span>
        <StatusBadge status={task.status} />
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 ml-1 flex-shrink-0 leading-none"
          aria-label="Close terminal panel"
        >
          ×
        </button>
      </div>

      {/* Terminal body */}
      <div className="flex-1 overflow-hidden">
        <LogViewer
          taskId={isActive ? task.id : undefined}
          staticLines={staticLines}
          isActive={isActive}
          hideHeader={true}
        />
      </div>
    </div>
  );
}
```

### Step 2: Verify TypeScript

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```
Expected: no errors

### Step 3: Commit

```bash
cd packages/dashboard
git add src/components/tasks/TaskTerminalPanel.tsx
git commit -m "feat(74): add TaskTerminalPanel with compact header and LogViewer integration"
```

---

## Task 3: Update TaskBoard to use TaskTerminalPanel

**Files:**
- Modify: `packages/dashboard/src/components/tasks/TaskBoard.tsx`

Replace the existing detail panel (the `{selectedTask && (...)}` block) with `TaskTerminalPanel`. The existing panel contains: PipelineView, task metadata, ActivityLog, AutonomyPanel, EscalationContextPanel, CourseCorrectionHistory — all of which can be removed per the design (terminal-only right panel).

### Step 1: Add the import

At the top of the file, after the existing `PipelineView` import, add:
```typescript
import TaskTerminalPanel from './TaskTerminalPanel';
```

Remove unused imports that the old panel used (optional, but clean):
- `ActivityLog` (if only used in the old panel)
- `PipelineView` (if only used in the old panel)

Check first:
```bash
grep -n "ActivityLog\|PipelineView\|AutonomyPanel\|EscalationContextPanel\|CourseCorrectionHistory" packages/dashboard/src/components/tasks/TaskBoard.tsx
```
If any are only used in the detail panel section, remove their imports too.

### Step 2: Replace the detail panel block

The existing detail panel block starts at:
```typescript
      {/* Detail Panel */}
      {selectedTask && (
        <div className="w-80 flex-shrink-0 border-l border-gray-200 dark:border-gray-700 pl-4">
```
...and ends at the closing `</div>` before the final `</div>` and `);`.

Replace the entire `{selectedTask && (...)}` block with:
```typescript
      {selectedTask && (
        <TaskTerminalPanel
          task={selectedTask}
          onClose={() => setSelectedTask(null)}
        />
      )}
```

### Step 3: Verify TypeScript

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```
Expected: no errors

### Step 4: Smoke test in browser

```bash
cd packages/dashboard && pnpm dev
```

Open `http://localhost:6987` → navigate to Tasks page → click any task card. Verify:
- Panel opens immediately on the right
- Task ID and status badge appear in compact header
- Terminal area is dark with mono font
- For active tasks: "Waiting for output..." shows initially, then lines stream in
- For completed tasks: activity log entries render as static lines
- Scroll up in terminal → "↓ scroll to resume" badge appears
- Click badge → scrolls to bottom, badge disappears
- Close button (×) closes the panel

### Step 5: Commit

```bash
cd packages/dashboard
git add src/components/tasks/TaskBoard.tsx
git commit -m "feat(74): replace task detail panel with terminal streaming panel (DASH-01, DASH-02, DASH-03)"
```

---

## Task 4: Verify success criteria

Check each criterion from the roadmap:

**DASH-01:** Terminal-style output panel renders live L3 output per active task
- Fire up an actual L3 task (or use `openclaw-monitor status` to find one in_progress)
- Open dashboard → Tasks → click the in_progress task
- Confirm lines stream into the panel

**DASH-02:** Click task row opens stream within 500ms
- Time the click-to-panel render (should be instant; SSE connection is async)

**DASH-03:** Auto-scroll with pause-on-scroll-up, resume-on-scroll-to-bottom
- While output is streaming, scroll up in the terminal panel
- Confirm "↓ scroll to resume" badge appears
- Confirm new lines accumulate but view stays where you scrolled to
- Click badge (or scroll back to bottom manually) → auto-scroll resumes

### Final commit (if any last fixes)

```bash
git add -A
git commit -m "feat(74): phase 74 dashboard streaming UI complete"
```

---

## Troubleshooting

**Panel doesn't open on click:** Check `selectedTask` state in TaskBoard — verify `onClick` on `TaskCard` passes through the task with correct type.

**No output for active tasks:** Check that the event bridge is running. In terminal: `openclaw-monitor status`. Verify events.sock exists at `~/.openclaw/run/events.sock`. Check browser DevTools → Network → EventSource `/api/events` is connected.

**Timestamps show 1970:** `activity_log[].timestamp` may already be in ms. If so, remove `* 1000` in `activityToLogEntries`.

**TypeScript error on `LogEntry` import:** Ensure `export interface LogEntry` in LogViewer.tsx (Task 1, Step 2). Import path is `@/components/LogViewer` (without `.tsx`).

**Panel height doesn't fill:** The `TaskBoard` outer container needs `h-full` for the flex layout to work. Check that `<div className="flex gap-4 h-full">` is present in TaskBoard's return.
