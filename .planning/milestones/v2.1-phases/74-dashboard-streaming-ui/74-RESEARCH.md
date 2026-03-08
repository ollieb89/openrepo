# Phase 74: Dashboard Streaming UI - Research

**Researched:** 2026-03-05
**Domain:** React/Next.js dashboard UI — SSE streaming, terminal panel, task board interactions
**Confidence:** HIGH (codebase verification, all claims backed by direct file inspection)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- This is a verification and polish phase — infrastructure (SSE, LogViewer, TaskTerminalPanel, TaskBoard wiring) was built in Phase 71; Phase 74 fills UX gaps and satisfies DASH-01/DASH-02/DASH-03 success criteria
- `LogViewer.tsx` is production-ready — use as-is, no rebuild needed
- `TaskTerminalPanel.tsx` is the side panel wrapper — use as-is, may need minor width/header tweaks
- `TaskBoard.tsx` already wires click-to-select and renders `TaskTerminalPanel` — confirm correct behavior
- `TaskCard.tsx` needs `isSelected` prop + selected visual state added
- Fixed `w-80` (320px) right-side panel — maintain as-is (matches existing design pattern)
- Clicking any task (in-progress or completed/failed) opens the panel — existing behavior correct
- No missed-event replay on reconnect (in-memory only, fire-and-forget) — Phase 71 decision
- Existing LogViewer error banner on disconnect is acceptable
- DASH-03: The "↓ scroll to resume" is an indicator, NOT a button — satisfies DASH-03 as-is
- Resizable panel — OUT OF SCOPE (Phase 77 or backlog)
- Fullscreen terminal mode — OUT OF SCOPE (backlog)
- Search/filter within terminal output — OUT OF SCOPE (backlog)

### Claude's Discretion
- Exact visual style for task card selected state (blue ring, background tint, or combined)
- Whether to make SSE reconnect indicator more subtle
- Minor layout/spacing adjustments if needed for terminal readability

### Deferred Ideas (OUT OF SCOPE)
- Resizable panel (Phase 77 or backlog)
- Fullscreen terminal mode (backlog)
- Search/filter within terminal output (backlog)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-01 | Terminal-style output panel renders live L3 output per active task | `LogViewer.tsx` and `TaskTerminalPanel.tsx` are implemented; this phase verifies and wire-confirms the full end-to-end render path |
| DASH-02 | Click task on task board opens live output stream | `TaskBoard.tsx` has `handleTaskClick` and `selectedTaskId` state; `TaskCard.tsx` needs `isSelected` prop for visual confirmation; wiring is present |
| DASH-03 | Auto-scroll with pause-on-scroll-up, resume-on-scroll-to-bottom (no button required) | `LogViewer.tsx` implements `autoScrollRef` + scroll handler with 20px `atBottom` threshold; indicator is non-interactive label, not button — satisfies requirement |
</phase_requirements>

## Summary

Phase 74 is a targeted polish phase, not a feature-build phase. The core streaming infrastructure — SSE bridge, LogViewer, TaskTerminalPanel, TaskBoard wiring — was delivered in Phase 71. The codebase verification confirms all components exist and are largely correct. The one confirmed gap is `TaskCard.tsx` missing an `isSelected` prop and the corresponding visual selected state; clicking a card gives no visual feedback that it is selected. All other DASH-01/DASH-02/DASH-03 criteria are implemented.

The plan must verify that the full end-to-end flow works (click → panel opens → SSE connects → output streams → auto-scroll works), add the `isSelected` selected state to `TaskCard`, and run the vitest suite plus a smoke-test checklist for the streaming behavior. No new infrastructure is needed.

**Primary recommendation:** Add `isSelected: boolean` to `TaskCard` props with a Tailwind blue ring highlight, then verify the end-to-end streaming flow passes all success criteria from the CONTEXT.md.

## Standard Stack

### Core (confirmed from package.json and codebase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.5.12 | React framework, SSE route via `app/api/events/route.ts` | Already in use; App Router with `force-dynamic` export |
| React | 19 | Component library | Project standard |
| Tailwind CSS | ^3.4.0 | Utility-first styling | Project-wide, dark: variants throughout |
| TypeScript | ^5 | Type safety | Project standard |
| SWR | ^2.4.0 | Data fetching for tasks API | Used in `TaskBoard.tsx` via `useTasks` and `useSWRConfig` |
| Vitest | ^3.2.4 | Unit testing | Project-configured test framework |
| lucide-react | ^0.575.0 | Icon components used in PipelineView | Already in use |

### Existing Components (no new installation needed)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| `LogViewer` | `src/components/LogViewer.tsx` | Production-ready | SSE, auto-scroll, reconnect, 1000-line buffer |
| `TaskTerminalPanel` | `src/components/tasks/TaskTerminalPanel.tsx` | Production-ready | Wraps LogViewer, completion banner, PipelineView compact |
| `TaskBoard` | `src/components/tasks/TaskBoard.tsx` | Production-ready | `selectedTaskId` state, `handleTaskClick`, renders panel |
| `TaskCard` | `src/components/tasks/TaskCard.tsx` | Needs `isSelected` prop | No selected visual state exists yet |
| `PipelineView` | `src/components/tasks/PipelineView.tsx` | Production-ready | compact mode used in panel header |
| `StatusBadge` | `src/components/common/StatusBadge.tsx` | Production-ready | Used in TaskCard and panel header |
| `useEvents` | `src/hooks/useEvents.ts` | Production-ready | Used by TaskBoard for lifecycle event revalidation |

**Installation:** No new packages required. All dependencies are installed.

## Architecture Patterns

### Data Flow (verified from source)

```
TaskBoard.tsx
  └── selectedTaskId state (useState<string | null>)
  └── handleTaskClick(taskId) → setSelectedTaskId(taskId)
  └── TaskCard (per task)
        └── onClick → handleTaskClick(task.id)
        └── isSelected prop (MISSING — gap to fill)
  └── TaskTerminalPanel (when selectedTask exists)
        └── task prop (full Task object)
        └── LogViewer
              └── taskId prop
              └── EventSource('/api/events') → filters by task_id
              └── autoScrollRef + scroll handler

SSE Path:
  L3 pool.py stdout → event_bus → Unix socket → /api/events/route.ts → SSE stream
  EventSource client-side → LogViewer.onmessage → filters type=task.output + task_id match
```

### Recommended Implementation Pattern: isSelected on TaskCard

**What:** Add `isSelected?: boolean` to `TaskCardProps`. Apply Tailwind ring classes conditionally.

**When to use:** Any time a TaskCard represents the currently selected task (selectedTaskId matches task.id).

**Tailwind pattern (consistent with existing board):**

```typescript
// Source: verified from TaskBoard.tsx filterStatus active button pattern (line 131-133)
// Pattern: ring-1 ring-blue-400 + blue tinted background
const selectedClasses = isSelected
  ? 'ring-2 ring-blue-500 dark:ring-blue-400 bg-blue-50 dark:bg-blue-900/20'
  : '';

// Full className:
className={`p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm cursor-pointer hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600 transition-all ${selectedClasses}`}
```

**TaskBoard wiring:**

```typescript
// In TaskBoard.tsx, pass isSelected to TaskCard
<TaskCard
  key={task.id}
  task={task}
  onClick={() => handleTaskClick(task.id)}
  isSelected={selectedTaskId === task.id}
/>
```

### Auto-Scroll Pattern (verified from LogViewer.tsx lines 204-223)

The auto-scroll is already implemented correctly. The `atBottom` check uses a 20px threshold — this is the correct pattern for terminal UIs (prevents false non-bottom detection due to sub-pixel scrolling).

```typescript
// Source: LogViewer.tsx lines 204-215 (verified)
const handleScroll = useCallback(() => {
  const el = logContainerRef.current;
  if (!el) return;
  const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
  if (atBottom) {
    autoScrollRef.current = true;
    setAutoScrollPaused(false);
  } else {
    autoScrollRef.current = false;
    setAutoScrollPaused(true);
  }
}, []);
```

The "↓ scroll to resume" button at line 289 calls `resumeScroll` which scrolls programmatically — this is an indicator + shortcut, not a required action to resume auto-scroll. Scrolling down naturally to the bottom also resumes it via `handleScroll`. This satisfies DASH-03.

### SSE Connection Pattern (verified from LogViewer.tsx)

LogViewer opens a single `EventSource('/api/events')` per component instance. Events are filtered client-side by `parsed.task_id === effectiveTaskId`. The API route (`/api/events/route.ts`) delivers all events to all SSE clients — filtering is entirely client-side.

**Key behaviors verified:**
- `Effect A` (lines 127-150): Clears log buffer only on real task switch (taskId changes), not on isActive changes
- `Effect B` (lines 152-179): SSE lifecycle — connects/disconnects without touching logs
- `Effect C` (lines 181-194): Supplemental merge — appends activity_log entries on task completion, deduplicating via `suffixOverlapMerge`
- Exponential backoff: 1s → 2s → 4s → ... → 30s max (lines 100-107)
- 1000-line rolling buffer (MAX_LOG_ENTRIES constant)

### TaskTerminalPanel Lifecycle (verified from TaskTerminalPanel.tsx)

The panel determines `isActive = task.status === 'in_progress' || task.status === 'starting'`. For completed/failed tasks, `supplementalLines` is populated from `task.activity_log` (converted via `activityToLogEntries`). LogViewer Effect C merges these on task completion.

**Completion banner states:**
- `'syncing'`: transition flash when task goes from active → inactive
- `'stored'`: task.activity_log.length > 0 (has stored entries)
- `'empty'`: task.activity_log.length === 0 (nothing stored)

### Anti-Patterns to Avoid

- **Clearing logs on isActive toggle:** LogViewer explicitly guards against this (Effect A). Never add setLogs([]) to isActive-dependent effects.
- **Replacing the "↓ scroll to resume" button with a purely passive indicator and removing the click handler:** The button's click handler calls `resumeScroll()` as a convenience shortcut. The scroll handler still resumes on natural scroll — both paths should coexist.
- **Passing task object reference as LogViewer taskId:** Always pass `task.id` (string primitive) to avoid spurious reconnections when the Task object reference refreshes from SWR polling.
- **Double EventSource connections:** `TaskBoard.tsx` uses `useEvents` for lifecycle events; `LogViewer` uses its own `EventSource`. These are separate connections for separate purposes — do not merge them.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Overlap deduplication on log merge | Custom diff algorithm | `suffixOverlapMerge` in `src/lib/logViewer-utils.ts` | Already built, tested with 8 vitest cases |
| SSE reconnection with backoff | Custom retry logic | `LogViewer.tsx` reconnect in `onerror` handler | Already implemented with exponential backoff |
| Task filtering by status | Custom filter | `getColumnTasks()` in TaskBoard.tsx | Already handles edge-case status aliasing (starting→in_progress, rejected→failed) |
| Ring buffer for SSE replay | Custom buffer | `/api/events/route.ts` ringBuffer (100 events) | Already implemented with Last-Event-ID header support |

## Common Pitfalls

### Pitfall 1: TaskCard onClick signature mismatch

**What goes wrong:** `TaskCard.onClick` is typed `(task: Task) => void` but `TaskBoard` passes `() => handleTaskClick(task.id)`. Adding `isSelected` must not change this pattern.

**Why it happens:** The onClick in TaskCard passes the full Task object but the board ignores it and uses the closure. A future refactor may break if onClick signature changes.

**How to avoid:** Keep `isSelected` as a separate prop (not derived from onClick). Do not change the onClick signature.

### Pitfall 2: selectedTaskId pointing to a stale/removed task

**What goes wrong:** If a task disappears from the list (filtered out or project switch), `selectedTask` becomes null and the panel closes. This is correct existing behavior but worth verifying after adding `isSelected`.

**Why it happens:** `selectedTask = tasks.find(t => t.id === selectedTaskId) ?? null`. When null, `TaskTerminalPanel` is not rendered.

**How to avoid:** No special handling needed. Confirm `isSelected={selectedTaskId === task.id}` only passes true for tasks currently in the rendered list — which is guaranteed by the map over `colTasks`.

### Pitfall 3: isSelected prop causing TypeScript errors at build

**What goes wrong:** `TaskCardProps` currently has no `isSelected` field. Forgetting to update the interface causes a TypeScript compile error.

**How to avoid:** Add `isSelected?: boolean` (optional with default false) to the `TaskCardProps` interface. Default to false via destructuring: `{ task, onClick, isSelected = false }`.

### Pitfall 4: Auto-scroll resume breaking when panel switches tasks

**What goes wrong:** `autoScrollRef` is internal to LogViewer. When `taskId` changes, Effect A clears logs and resets `reconnectDelayRef` but does NOT explicitly reset `autoScrollRef` or `autoScrollPaused` state. If the user had scrolled up on the previous task and then clicks a new task, the paused indicator might linger briefly.

**Why it happens:** `autoScrollRef` starts as `true` and `autoScrollPaused` starts as `false` (initial useState). On task switch, Effect A does not reset these. However, since logs are cleared, the scroll position resets to top = bottom (empty list), which would naturally trigger `atBottom = true` on the next scroll event.

**How to avoid:** Verify behavior manually: click task A, scroll up (paused indicator appears), click task B — confirm indicator disappears and auto-scroll resumes. If it does not, add `autoScrollRef.current = true; setAutoScrollPaused(false)` inside the task-switch branch of Effect A. This is a verification task, not necessarily a code change.

### Pitfall 5: vitest config excludes src/ test files

**What goes wrong:** `vitest.config.ts` includes only `tests/**/*.test.ts` and `tests/**/*.test.tsx`. Tests in `src/` (like `src/lib/ollama.test.ts`) are NOT picked up by the configured test runner.

**Why it happens:** Vitest config at line 7: `include: ['tests/**/*.test.ts', 'tests/**/*.test.tsx']`. New test files for Phase 74 must go in `tests/` not `src/`.

**How to avoid:** Place all Phase 74 test files under `packages/dashboard/tests/`.

## Code Examples

### Pattern 1: TaskCard with isSelected prop

```typescript
// File: packages/dashboard/src/components/tasks/TaskCard.tsx
// Source: derived from existing TaskBoard.tsx filter button pattern (verified line 131-133)

interface TaskCardProps {
  task: Task;
  onClick: (task: Task) => void;
  isSelected?: boolean;  // ADD THIS
}

export default function TaskCard({ task, onClick, isSelected = false }: TaskCardProps) {
  const lastActivity = task.activity_log[task.activity_log.length - 1];

  return (
    <div
      onClick={() => onClick(task)}
      className={`p-3 bg-white dark:bg-gray-800 border rounded-lg shadow-sm cursor-pointer transition-all
        ${isSelected
          ? 'border-blue-400 dark:border-blue-500 ring-2 ring-blue-400 dark:ring-blue-500 bg-blue-50 dark:bg-blue-900/20 hover:border-blue-400 dark:hover:border-blue-500'
          : 'border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-600'
        }`}
    >
      {/* ... existing interior unchanged ... */}
    </div>
  );
}
```

### Pattern 2: TaskBoard passing isSelected to TaskCard

```typescript
// File: packages/dashboard/src/components/tasks/TaskBoard.tsx
// Source: verified from existing TaskBoard.tsx (line 169-175) — minimal delta

<TaskCard
  key={task.id}
  task={task}
  onClick={() => handleTaskClick(task.id)}
  isSelected={selectedTaskId === task.id}   // ADD THIS LINE
/>
```

### Pattern 3: Vitest test for TaskCard isSelected visual state

```typescript
// File: packages/dashboard/tests/components/tasks/TaskCard.test.tsx
// Pattern from: tests/lib/logViewer-utils.test.ts (verified structure)
// NOTE: vitest.config.ts environment is 'node'; DOM component testing requires jsdom setup
// Consider: test the prop interface compiles, or use a smoke/manual test for visual verification

import { describe, it, expect } from 'vitest';
// Full DOM rendering requires @testing-library/react + jsdom config — see Wave 0 gaps
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `containerId` prop on LogViewer | `taskId` prop (containerId is `@deprecated`) | Phase 71 | New code must use `taskId` |
| Static log display | `supplementalLines` Effect C merge | Phase 71 | Completed tasks show stored activity_log without page navigation |
| Full re-render on task switch | Effect A: only clear logs on real taskId change | Phase 71 | Prevents flicker on SWR revalidation |

## Open Questions

1. **Auto-scroll state after task switch (Pitfall 4)**
   - What we know: autoScrollRef and autoScrollPaused are not explicitly reset in Effect A on task switch
   - What's unclear: Whether the natural scroll-position-reset (empty list = at bottom) correctly fires handleScroll and clears the paused state
   - Recommendation: Verify manually during implementation. If not working, add explicit reset in Effect A task-switch branch.

2. **DASH-02 "within 500ms" success criterion**
   - What we know: `handleTaskClick` is a synchronous state update → React re-renders TaskTerminalPanel immediately → SSE connect happens in LogViewer Effect B after render
   - What's unclear: Whether SSE socket connection latency adds visible delay on the panel opening (the panel appears instantly but logs may lag)
   - Recommendation: The 500ms criterion refers to panel appearing, not first log line. Panel appearance is instant (synchronous React state). No optimization needed.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 3.2.4 |
| Config file | `packages/dashboard/vitest.config.ts` |
| Quick run command | `cd /home/ob/Development/Tools/openrepo/packages/dashboard && pnpm test` |
| Full suite command | `cd /home/ob/Development/Tools/openrepo/packages/dashboard && pnpm test` |

**Note:** `vitest.config.ts` uses `environment: 'node'`. DOM component rendering tests require `jsdom` or `happy-dom` environment. The existing tests (logViewer-utils, sync, topology) are pure logic tests, not component render tests. Phase 74 verification is primarily manual/smoke-test for the visual and streaming behaviors.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | LogViewer renders terminal output panel | smoke (manual) | `pnpm test` — no DOM test yet | ❌ Wave 0 |
| DASH-02 | TaskCard isSelected prop applies visual state | unit (logic) + smoke | `pnpm test -- tests/components/tasks/TaskCard.test.ts` | ❌ Wave 0 |
| DASH-03 | Auto-scroll pauses on scroll-up, resumes at bottom | smoke (manual) | `pnpm test -- tests/lib/logViewer-utils.test.ts` (utils only) | ✅ (utils) |

**DASH-01 and DASH-03 streaming/scroll behaviors require browser-environment testing or manual verification** — the current vitest config uses `node` environment which cannot render React components or simulate scroll events without additional setup.

### Sampling Rate

- **Per task commit:** `pnpm test` (runs all vitest tests; < 5 seconds for current suite)
- **Per wave merge:** `pnpm test` (full suite) + manual smoke-test checklist
- **Phase gate:** Full suite green + manual streaming verification before `/gsd:verify-work`

### Manual Smoke-Test Checklist (required for DASH-01, DASH-02, DASH-03)

```
Dashboard running at http://localhost:6987 with active orchestration:

[ ] DASH-02: Click a task card in any column — panel appears within 500ms (visually)
[ ] DASH-02: Clicked task card shows selected visual state (blue ring / tinted background)
[ ] DASH-01: Terminal panel shows task ID, StatusBadge, PipelineView compact, LogViewer
[ ] DASH-01 (in_progress task): LogViewer shows "Connected" status and streams live lines
[ ] DASH-01 (completed task): LogViewer shows stored activity_log via supplementalLines
[ ] DASH-03: Scroll up in active stream — "↓ scroll to resume" indicator appears
[ ] DASH-03: Scroll back down (within 20px of bottom) — indicator disappears automatically (no button click)
[ ] DASH-03: "↓ scroll to resume" button click also resumes (shortcut path)
[ ] Click a different task — panel switches, selected state moves, buffer clears
[ ] Close button (×) dismisses panel, no task shows selected state
```

### Wave 0 Gaps

- [ ] `tests/components/tasks/TaskCard.test.ts` — covers DASH-02 isSelected prop compilation and className logic (pure logic test, no DOM render needed if testing className string generation)
- [ ] Consider: add `jsdom` to vitest environment for component render tests if required by future phases

*(The `tests/lib/logViewer-utils.test.ts` already exists and covers DASH-03's underlying merge logic.)*

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `packages/dashboard/src/components/LogViewer.tsx` — full SSE, auto-scroll, Effect A/B/C verified
- Direct file inspection: `packages/dashboard/src/components/tasks/TaskBoard.tsx` — selectedTaskId, handleTaskClick, TaskTerminalPanel wiring verified
- Direct file inspection: `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx` — isActive logic, supplementalLines, completion banner verified
- Direct file inspection: `packages/dashboard/src/components/tasks/TaskCard.tsx` — confirmed missing isSelected prop
- Direct file inspection: `packages/dashboard/src/app/api/events/route.ts` — SSE bridge, ring buffer, heartbeat verified
- Direct file inspection: `packages/dashboard/vitest.config.ts` — node environment, tests/ include pattern verified
- Direct file inspection: `packages/dashboard/package.json` — vitest 3.2.4, pnpm test script verified

### Secondary (MEDIUM confidence)
- `.planning/phases/74-dashboard-streaming-ui/74-CONTEXT.md` — CONTEXT decisions verified against codebase; all claims cross-checked

### Tertiary (LOW confidence)
- None — all findings backed by direct file inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from package.json and node_modules
- Architecture: HIGH — verified from direct component source inspection
- Pitfalls: HIGH — derived from verified source code behavior; Pitfall 4 flagged as requires runtime verification
- Test gaps: HIGH — vitest.config.ts and tests/ directory structure confirmed

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable stack, no fast-moving dependencies)
