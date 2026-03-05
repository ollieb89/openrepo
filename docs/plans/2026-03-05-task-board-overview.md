# Task Board Overview Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add stats summary row, pipeline stage view, status filter, and a null-project guard to the task board.

**Architecture:** Self-contained `TaskBoard` restructure — stats row + conditional `PipelineView` live inside `TaskBoard`. `PipelineView` gains a `compact` prop for the narrow terminal panel. No new files, no new context or hooks.

**Tech Stack:** React, Next.js, Tailwind CSS, SWR, existing `StatusBadge`, `Card`, `PipelineView` components.

---

### Task 1: Add `compact` prop to `PipelineView`

**Files:**
- Modify: `packages/dashboard/src/components/tasks/PipelineView.tsx`

The current component is ~79 lines and renders a horizontal stepper with 5 steps + arrows. The `compact` variant is a plain vertical list (no arrows, smaller icons) for the 320px terminal panel.

**Step 1: Open the file and understand the shape**

Read `packages/dashboard/src/components/tasks/PipelineView.tsx`. Key things to know:
- `Step` component takes `label`, `status`, `description?`
- `PipelineView` takes `status: TaskStatus`
- Each step renders an icon + label; icons are from `lucide-react`

**Step 2: Add the `compact` prop and compact rendering**

Replace the entire file with:

```tsx
'use client';

import React from 'react';
import { CheckCircle2, Circle, Clock, AlertCircle, ArrowRight } from 'lucide-react';
import type { TaskStatus } from '@/lib/types';

interface StepProps {
  label: string;
  status: 'complete' | 'active' | 'pending' | 'failed';
  description?: string;
  compact?: boolean;
}

function Step({ label, status, description, compact = false }: StepProps) {
  const icons = {
    complete: <CheckCircle2 className={compact ? 'w-4 h-4 text-green-500' : 'w-6 h-6 text-green-500'} />,
    active: <Clock className={compact ? 'w-4 h-4 text-blue-500 animate-pulse' : 'w-6 h-6 text-blue-500 animate-pulse'} />,
    pending: <Circle className={compact ? 'w-4 h-4 text-gray-300' : 'w-6 h-6 text-gray-300'} />,
    failed: <AlertCircle className={compact ? 'w-4 h-4 text-red-500' : 'w-6 h-6 text-red-500'} />,
  };

  const textColors = {
    complete: 'text-green-700 dark:text-green-400',
    active: 'text-blue-700 dark:text-blue-400 font-semibold',
    pending: 'text-gray-500 dark:text-gray-400',
    failed: 'text-red-700 dark:text-red-400',
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2 py-1">
        {icons[status]}
        <span className={`text-xs ${textColors[status]}`}>{label}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center flex-1 min-w-[120px]">
      <div className="mb-2">{icons[status]}</div>
      <span className={`text-xs uppercase tracking-wider ${textColors[status]}`}>{label}</span>
      {description && <span className="text-[10px] text-gray-400 mt-1">{description}</span>}
    </div>
  );
}

interface PipelineProps {
  status: TaskStatus;
  compact?: boolean;
}

export default function PipelineView({ status, compact = false }: PipelineProps) {
  const getStepStatus = (step: string): 'complete' | 'active' | 'pending' | 'failed' => {
    const sequence = ['directive', 'routing', 'executing', 'review', 'merge'];
    const currentIndex = sequence.indexOf(
      status === 'pending' ? 'directive' :
      status === 'starting' ? 'routing' :
      status === 'in_progress' ? 'executing' :
      status === 'testing' ? 'review' :
      status === 'completed' ? 'merge' :
      status === 'failed' || status === 'rejected' ? 'failed' : 'directive'
    );

    const stepIndex = sequence.indexOf(step);

    if (status === 'failed' || status === 'rejected') {
      if (stepIndex < currentIndex) return 'complete';
      if (stepIndex === currentIndex) return 'failed';
      return 'pending';
    }

    if (stepIndex < currentIndex) return 'complete';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  const steps: { key: string; label: string }[] = [
    { key: 'directive', label: 'L1 Directive' },
    { key: 'routing', label: 'L2 Routing' },
    { key: 'executing', label: 'L3 Execution' },
    { key: 'review', label: 'Review' },
    { key: 'merge', label: 'Final Merge' },
  ];

  if (compact) {
    return (
      <div className="px-3 py-2 bg-gray-900 border-b border-gray-800">
        {steps.map(s => (
          <Step key={s.key} label={s.label} status={getStepStatus(s.key)} compact />
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between w-full py-4 px-2 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700">
      <Step label="L1 Directive" status={getStepStatus('directive')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="L2 Routing" status={getStepStatus('routing')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="L3 Execution" status={getStepStatus('executing')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="Review" status={getStepStatus('review')} />
      <ArrowRight className="w-4 h-4 text-gray-300 shrink-0" />
      <Step label="Final Merge" status={getStepStatus('merge')} />
    </div>
  );
}
```

**Step 3: Verify no TypeScript errors**

```bash
cd packages/dashboard && npx tsc --noEmit 2>&1 | grep PipelineView
```

Expected: no output (no errors).

**Step 4: Commit**

```bash
git add packages/dashboard/src/components/tasks/PipelineView.tsx
git commit -m "feat(tasks): add compact prop to PipelineView for narrow panel use"
```

---

### Task 2: Add compact PipelineView to TaskTerminalPanel

**Files:**
- Modify: `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx`

The terminal panel is `w-80` (320px) with a dark background (`bg-gray-950`). The compact PipelineView goes between the header bar and the completion banner.

**Step 1: Add the import**

At the top of `TaskTerminalPanel.tsx`, after the existing imports, add:

```tsx
import PipelineView from './PipelineView';
```

**Step 2: Insert compact PipelineView after the header div**

The header div ends at the closing `</div>` after the `×` close button (around line 75). After that closing `</div>`, insert:

```tsx
      {/* Pipeline stage indicator */}
      <div className="flex-shrink-0">
        <PipelineView status={task.status} compact />
      </div>
```

The file section should look like:

```tsx
      {/* Compact header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-800 flex-shrink-0 bg-gray-900 gap-2">
        <span className="font-mono text-xs text-gray-400 truncate flex-1" title={task.id}>
          {task.id}
        </span>
        <StatusBadge status={task.status} />
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-300 ml-1 flex-shrink-0 leading-none text-base"
          aria-label="Close terminal panel"
        >
          ×
        </button>
      </div>

      {/* Pipeline stage indicator */}
      <div className="flex-shrink-0">
        <PipelineView status={task.status} compact />
      </div>

      {/* Completion banner — non-blocking strip explaining source-of-truth transition */}
      {bannerState !== 'none' && (
```

**Step 3: Verify no TypeScript errors**

```bash
cd packages/dashboard && npx tsc --noEmit 2>&1 | grep TaskTerminalPanel
```

Expected: no output.

**Step 4: Commit**

```bash
git add packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx
git commit -m "feat(tasks): add compact pipeline stage view to terminal panel"
```

---

### Task 3: Restructure TaskBoard — null guard + stats row + filter + pipeline banner

**Files:**
- Modify: `packages/dashboard/src/components/tasks/TaskBoard.tsx`

This is the main change. The board gets:
1. Null projectId guard (before loading check)
2. Stats row with 5 cards, clickable to filter columns
3. Full `PipelineView` banner when a task is selected
4. Filter state that dims non-selected columns

**Step 1: Replace the entire file**

```tsx
'use client';

import { useState } from 'react';
import type { TaskStatus } from '@/lib/types';
import { useTasks } from '@/lib/hooks/useTasks';
import { useProject } from '@/context/ProjectContext';
import TaskCard from './TaskCard';
import TaskTerminalPanel from './TaskTerminalPanel';
import PipelineView from './PipelineView';
import StatusBadge from '@/components/common/StatusBadge';
import Card from '@/components/common/Card';

const STATUS_COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: 'pending', label: 'Pending' },
  { status: 'in_progress', label: 'In Progress' },
  { status: 'testing', label: 'Testing' },
  { status: 'completed', label: 'Completed' },
  { status: 'failed', label: 'Failed' },
];

function columnTasks(tasks: ReturnType<typeof useTasks>['tasks'], status: TaskStatus) {
  return tasks.filter(t =>
    status === 'in_progress'
      ? t.status === 'in_progress' || t.status === 'starting'
      : t.status === status
  );
}

export default function TaskBoard() {
  const { projectId } = useProject();
  const { tasks, isLoading } = useTasks(projectId);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<TaskStatus | null>(null);

  const selectedTask = selectedTaskId
    ? tasks.find(t => t.id === selectedTaskId) ?? null
    : null;

  function handleTaskClick(taskId: string) {
    setSelectedTaskId(taskId);
    setFilterStatus(null);
  }

  function handleStatClick(status: TaskStatus) {
    setFilterStatus(prev => (prev === status ? null : status));
  }

  // Guard: no project selected
  if (!projectId) {
    return (
      <Card className="text-center py-12">
        <div className="px-4">
          <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
          </svg>
          <h3 className="mt-3 text-sm font-semibold text-gray-900 dark:text-white">No project selected</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Select a project from the dropdown in the header to view tasks.
          </p>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 dark:text-gray-400">
        Loading tasks...
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <Card className="text-center py-12">
        <div className="px-4">
          <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
          </svg>
          <h3 className="mt-3 text-sm font-semibold text-gray-900 dark:text-white">No tasks</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            No L3 tasks found for this project. Tasks appear when L2 delegates work to L3 specialists.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Stats summary row */}
      <div className="grid grid-cols-5 gap-3 flex-shrink-0">
        {STATUS_COLUMNS.map(col => {
          const count = columnTasks(tasks, col.status).length;
          const isActive = filterStatus === col.status;
          return (
            <button
              key={col.status}
              onClick={() => handleStatClick(col.status)}
              className={`p-3 rounded-lg border text-center transition-all ${
                isActive
                  ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700 ring-1 ring-blue-400'
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="text-2xl font-bold text-gray-900 dark:text-white mb-1">{count}</div>
              <StatusBadge status={col.status} />
            </button>
          );
        })}
      </div>

      {/* Pipeline banner — shown when a task is selected */}
      {selectedTask && (
        <div className="flex-shrink-0">
          <PipelineView status={selectedTask.status} />
        </div>
      )}

      {/* Kanban + terminal panel */}
      <div className="flex gap-4 flex-1 min-h-0">
        <div className="flex-1 flex gap-4 overflow-x-auto pb-4">
          {STATUS_COLUMNS.map(col => {
            const tasks_in_col = columnTasks(tasks, col.status);
            const isDimmed = filterStatus !== null && filterStatus !== col.status;

            return (
              <div
                key={col.status}
                className={`flex-shrink-0 w-64 transition-opacity ${isDimmed ? 'opacity-40' : 'opacity-100'}`}
              >
                <div className="flex items-center gap-2 mb-3 px-1">
                  <StatusBadge status={col.status} />
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {tasks_in_col.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {tasks_in_col.map(task => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      onClick={() => handleTaskClick(task.id)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {selectedTask && (
          <TaskTerminalPanel
            task={selectedTask}
            onClose={() => setSelectedTaskId(null)}
          />
        )}
      </div>
    </div>
  );
}
```

**Step 2: Verify no TypeScript errors**

```bash
cd packages/dashboard && npx tsc --noEmit 2>&1 | grep -E "TaskBoard|error TS"
```

Expected: no output.

**Step 3: Run the dashboard and smoke test**

```bash
make dashboard
```

Open http://localhost:6987/tasks and verify:
- No project selected → "No project selected" card with folder icon
- Project selected, tasks loading → "Loading tasks..." spinner
- Project selected, no tasks → "No tasks" card (unchanged)
- Project selected, tasks loaded → stats row (5 cards) + kanban columns
- Click a stat card → non-matching columns dim; click again → all columns restore
- Click a task card → pipeline banner appears above kanban; terminal panel opens on right; stat filter cleared
- Terminal panel header → compact pipeline list (5 steps, vertical)

**Step 4: Commit**

```bash
git add packages/dashboard/src/components/tasks/TaskBoard.tsx
git commit -m "feat(tasks): add stats row, pipeline banner, column filter, and null project guard to task board"
```

---

## Summary of Changes

| File | Lines changed | Purpose |
|------|--------------|---------|
| `PipelineView.tsx` | +35 | `compact` prop for vertical list variant |
| `TaskTerminalPanel.tsx` | +5 | Compact pipeline view between header and log |
| `TaskBoard.tsx` | ~full rewrite | Stats row, filter, pipeline banner, null guard |

Total: ~150 lines changed, 0 new files.
