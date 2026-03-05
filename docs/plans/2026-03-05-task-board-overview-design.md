# Task Board Overview Design

**Date:** 2026-03-05
**Status:** Approved

## Problem

The task board (`/tasks`) is a kanban board with no summary context. Issues:

1. No overview — no stats, no pipeline visibility
2. No null-project guard — when no project is selected, the board shows a confusing "No tasks" card with an L3 message
3. Layout feels incomplete — `PipelineView` component exists but is unused
4. Selected task detail (terminal panel) has no pipeline context

## Approach

Self-contained `TaskBoard` redesign — all layout sections live inside `TaskBoard`. The page wrapper stays thin.

## Layout

```
┌─────────────────────────────────────────────────┐
│ Guard: No project selected                       │  (replaces everything)
├─────────────────────────────────────────────────┤
│ Stats row: [Pending] [In Progress] [Testing]    │  always visible
│            [Completed] [Failed]                 │
├─────────────────────────────────────────────────┤
│ PipelineView (full, horizontal)                 │  visible only when task selected
│ L1 Directive → L2 Routing → L3 Exec → Review → Merge
├──────────────────────────────┬──────────────────┤
│ Kanban columns (scrollable)  │ Terminal panel   │
│ Pending | In Prog | Testing  │ - compact        │
│ Completed | Failed           │   PipelineView   │
│                              │ - log viewer     │
└──────────────────────────────┴──────────────────┘
```

## Components

### TaskBoard.tsx (restructured)

**New state:**
- `filterStatus: TaskStatus | null` — active stat card filter

**Sections:**
1. Guard — if `!projectId`, render "Select a project to view tasks" Card
2. Loading — existing spinner (unchanged)
3. Empty — existing "No tasks" card (unchanged)
4. Main layout (flex-col):
   - Stats row (always)
   - PipelineView (only when `selectedTask !== null`)
   - Kanban + terminal panel row

**Filter behavior:**
- Clicking a stat card sets `filterStatus` to that status (or clears if already selected)
- Non-filtered columns render at `opacity-40`
- Selecting a task card clears `filterStatus`

### PipelineView.tsx (add compact prop)

Add `compact?: boolean` prop:
- `compact={false}` (default) — existing horizontal layout with arrows, `min-w-[120px]` per step
- `compact={true}` — vertical list layout, no arrows, smaller icons

Compact layout:
```
✓ L1 Directive
✓ L2 Routing
⟳ L3 Execution   ← active (blue, pulsing)
○ Review
○ Final Merge
```

### TaskTerminalPanel.tsx (add compact pipeline)

Add `<PipelineView status={task.status} compact />` between the header bar and the completion banner.

## Error & Edge Cases

- `projectId === null`: Show "Select a project to view tasks" card (not loading, not empty)
- All tasks in one status: stats still show all 5 cards (zero counts shown, not hidden)
- Filter + selected task: selecting a task clears the filter
- `compact` PipelineView with `failed`/`rejected` status: shows failed state at correct step (existing logic)

## Files Changed

| File | Change |
|------|--------|
| `packages/dashboard/src/components/tasks/TaskBoard.tsx` | Full restructure |
| `packages/dashboard/src/components/tasks/PipelineView.tsx` | Add `compact` prop |
| `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx` | Add compact PipelineView |
| `packages/dashboard/src/app/tasks/page.tsx` | No changes |
