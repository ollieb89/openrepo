# Phase 74b: Stable Terminal Transition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the terminal panel reset glitch — when a task completes while the user is watching, the live SSE buffer is preserved, any missing tail is appended via suffix-overlap merge from `activity_log`, and a banner explains the source-of-truth transition.

**Architecture:** Split LogViewer's single monolithic effect into Effect A (log lifecycle — only clears on real task switch, never on `isActive` change), Effect B (SSE lifecycle — never touches logs), and Effect C (supplemental merge — appends `activity_log` tail once per completion). TaskTerminalPanel gains a stable `logTaskId` state and a `bannerState` for the completion indicator.

**Tech Stack:** React, TypeScript, Vitest, Tailwind CSS

**Design doc:** `docs/plans/2026-03-05-phase-74b-stable-terminal-transition-design.md`

---

## Context

### Key files

| File | Role |
|------|------|
| `packages/dashboard/src/components/LogViewer.tsx` | SSE consumer — we refactor the core effect |
| `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx` | Panel wrapper — we add stable ID + banner |
| `packages/dashboard/tests/lib/logViewer-utils.test.ts` | New — unit tests for pure merge function |

### Run tests
```bash
cd packages/dashboard && pnpm test
```

### TypeScript check
```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```

### The bug in one sentence
`setLogs([])` fires when `isActive` changes because a single `useEffect` conflates "task switched" and "SSE state changed". The fix: three separate effects, each with one responsibility.

---

## Task 1: Extract and test `suffixOverlapMerge`

**Files:**
- Create: `packages/dashboard/src/lib/logViewer-utils.ts`
- Create: `packages/dashboard/tests/lib/logViewer-utils.test.ts`

This is a pure function — test it in isolation before wiring it into the component.

### Step 1: Write the failing tests

Create `packages/dashboard/tests/lib/logViewer-utils.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { suffixOverlapMerge } from '@/lib/logViewer-utils';
import type { LogEntry } from '@/components/LogViewer';

function entry(line: string, ts = 1000): LogEntry {
  return { line, stream: 'stdout', timestamp: ts };
}

describe('suffixOverlapMerge', () => {
  it('returns live unchanged when supplemental is empty', () => {
    const live = [entry('a'), entry('b')];
    expect(suffixOverlapMerge(live, [])).toEqual(live);
  });

  it('appends non-overlapping supplemental to live', () => {
    const live = [entry('a'), entry('b')];
    const sup = [entry('c'), entry('d')];
    expect(suffixOverlapMerge(live, sup)).toEqual([
      entry('a'), entry('b'), entry('c'), entry('d'),
    ]);
  });

  it('finds suffix overlap and appends only the tail', () => {
    const live = [entry('a'), entry('b'), entry('c')];
    const sup = [entry('b'), entry('c'), entry('d'), entry('e')];
    const result = suffixOverlapMerge(live, sup);
    expect(result.map(e => e.line)).toEqual(['a', 'b', 'c', 'd', 'e']);
  });

  it('handles full overlap (no new lines)', () => {
    const live = [entry('a'), entry('b'), entry('c')];
    const sup = [entry('b'), entry('c')];
    expect(suffixOverlapMerge(live, sup)).toEqual(live);
  });

  it('handles CRLF normalization in comparison', () => {
    const live = [entry('line1'), entry('line2\r')];
    const sup = [entry('line2'), entry('line3')];
    const result = suffixOverlapMerge(live, sup);
    expect(result.map(e => e.line)).toEqual(['line1', 'line2\r', 'line3']);
  });

  it('does not drop legitimate repeated lines', () => {
    const live = [entry('Retrying…'), entry('Retrying…'), entry('Retrying…')];
    const sup = [entry('Retrying…'), entry('Done')];
    // Only the last "Retrying…" suffix should overlap with sup[0]
    const result = suffixOverlapMerge(live, sup);
    expect(result.map(e => e.line)).toEqual([
      'Retrying…', 'Retrying…', 'Retrying…', 'Done',
    ]);
  });

  it('caps append with divider when no overlap and supplemental is large (>500 lines)', () => {
    const live = [entry('live-line')];
    const sup = Array.from({ length: 600 }, (_, i) => entry(`sup-${i}`));
    const result = suffixOverlapMerge(live, sup);
    // Should have live-line + divider + last 500 of sup
    expect(result[0].line).toBe('live-line');
    expect(result[1].line).toBe('— stored log (partial) —');
    expect(result.length).toBe(1 + 1 + 500);
    expect(result[result.length - 1].line).toBe('sup-599');
  });

  it('appends all when no overlap and supplemental is small (<=500 lines)', () => {
    const live = [entry('live-line')];
    const sup = Array.from({ length: 10 }, (_, i) => entry(`sup-${i}`));
    const result = suffixOverlapMerge(live, sup);
    expect(result.length).toBe(11);
    expect(result[0].line).toBe('live-line');
    expect(result[1].line).toBe('sup-0');
  });
});
```

### Step 2: Run to confirm all tests fail

```bash
cd packages/dashboard && pnpm test tests/lib/logViewer-utils.test.ts
```

Expected: `Cannot find module '@/lib/logViewer-utils'`

### Step 3: Implement `logViewer-utils.ts`

Create `packages/dashboard/src/lib/logViewer-utils.ts`:

```typescript
import type { LogEntry } from '@/components/LogViewer';

const OVERLAP_WINDOW = 500;

function normalizeLine(line: string): string {
  // Normalize CRLF and trailing CR for comparison only (not mutation)
  return line.replace(/\r\n/g, '\n').replace(/\r$/, '');
  // TODO: strip ANSI codes here if logs contain terminal escape sequences
}

/**
 * Append entries from `supplemental` that are not already at the tail of `live`.
 *
 * Algorithm: find the largest k where the last k lines of `live` match the
 * first k lines of `supplemental` (by normalized content). Append supplemental[k:].
 *
 * Constrained to last OVERLAP_WINDOW lines to avoid O(n²) on large logs.
 * When no overlap is found and supplemental is large (>OVERLAP_WINDOW), appends
 * only the last OVERLAP_WINDOW lines with a synthetic divider to avoid doubling.
 */
export function suffixOverlapMerge(live: LogEntry[], supplemental: LogEntry[]): LogEntry[] {
  if (!supplemental.length) return live;

  const windowSize = Math.min(OVERLAP_WINDOW, live.length);
  const window = live.slice(-windowSize);

  // Find largest k where live[-k:] matches supplemental[0:k]
  let overlapK = 0;
  const maxK = Math.min(windowSize, supplemental.length);
  for (let k = maxK; k > 0; k--) {
    let match = true;
    for (let i = 0; i < k; i++) {
      const liveIdx = window.length - k + i;
      if (normalizeLine(window[liveIdx].line) !== normalizeLine(supplemental[i].line)) {
        match = false;
        break;
      }
    }
    if (match) {
      overlapK = k;
      break;
    }
  }

  const tail = supplemental.slice(overlapK);

  if (!overlapK && supplemental.length > OVERLAP_WINDOW) {
    // No overlap and large supplemental — avoid doubling the entire log
    const divider: LogEntry = {
      line: '— stored log (partial) —',
      stream: 'stdout',
      timestamp: Date.now(),
    };
    return [...live, divider, ...supplemental.slice(-OVERLAP_WINDOW)];
  }

  return [...live, ...tail];
}
```

### Step 4: Run tests — expect all to pass

```bash
cd packages/dashboard && pnpm test tests/lib/logViewer-utils.test.ts
```

Expected: all 8 tests pass.

### Step 5: Commit

```bash
cd packages/dashboard
git add src/lib/logViewer-utils.ts tests/lib/logViewer-utils.test.ts
git commit -m "feat(74b): add suffixOverlapMerge utility with full test coverage"
```

---

## Task 2: Refactor LogViewer — split the monolithic effect

**Files:**
- Modify: `packages/dashboard/src/components/LogViewer.tsx`

This is the structural fix. Split the single effect into three with clear, non-overlapping responsibilities.

### Step 1: Read the current file

Read `packages/dashboard/src/components/LogViewer.tsx` (246 lines — already read in design session).

### Step 2: Add new refs below the existing refs (after line 39 `autoScrollRef`)

After:
```typescript
  const autoScrollRef = useRef(true);
```

Add:
```typescript
  const prevTaskIdRef = useRef<string | undefined>(undefined);
  const mergedForTaskIdRef = useRef<string | undefined>(undefined);
```

### Step 3: Add the `supplementalLines` prop

Replace the existing `LogViewerProps` interface:
```typescript
interface LogViewerProps {
  taskId?: string;
  /** @deprecated Use taskId instead */
  containerId?: string;
  /** Pre-built log lines for completed/failed tasks (skips SSE when isActive=false) */
  staticLines?: LogEntry[];
  /** When false and staticLines provided, SSE is not opened. Default: true */
  isActive?: boolean;
  /** Hide the built-in header (title, connected status, clear button). Default: false */
  hideHeader?: boolean;
}
```

With:
```typescript
interface LogViewerProps {
  taskId?: string;
  /** @deprecated Use taskId instead */
  containerId?: string;
  /** @deprecated Use supplementalLines instead */
  staticLines?: LogEntry[];
  /** When false, SSE is not opened. Default: true */
  isActive?: boolean;
  /** Hide the built-in header. Default: false */
  hideHeader?: boolean;
  /** Activity log entries to merge into the live buffer on task completion (Effect C). */
  supplementalLines?: LogEntry[];
}
```

Update the function signature to destructure `supplementalLines`:
```typescript
export default function LogViewer({ taskId, containerId, staticLines, isActive = true, hideHeader = false, supplementalLines }: LogViewerProps) {
```

### Step 4: Replace the single monolithic `useEffect` (lines 106–139) with four effects

The current block to replace — starts at:
```typescript
  useEffect(() => {
    isMountedRef.current = true;

    if (!effectiveTaskId) {
```
...ends at:
```typescript
  }, [effectiveTaskId, connectToEventSource, isActive]);
```

Replace the entire block with:

```typescript
  // Mount/unmount lifecycle — isMountedRef management and final cleanup
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, []);

  // Effect A: log lifecycle — clears buffer only on real task switch
  // INVARIANT: never clears logs due to isActive changes
  useEffect(() => {
    const prevId = prevTaskIdRef.current;
    prevTaskIdRef.current = effectiveTaskId;

    if (prevId === effectiveTaskId) return; // no-op: same id (shouldn't happen, but guard)

    if (prevId === undefined && effectiveTaskId !== undefined) {
      // Initialize: first mount or resuming from undefined — start fresh
      setLogs([]);
      setError(null);
      reconnectDelayRef.current = 1000;
    } else if (prevId !== undefined && effectiveTaskId === undefined) {
      // Task removed/hidden: PRESERVE BUFFER — stop streaming but do not erase
      // (caller removed taskId without intending to clear the log)
      setConnected(false);
      setError(null);
    } else if (prevId !== effectiveTaskId && effectiveTaskId !== undefined) {
      // Real task switch: clear buffer and start fresh
      setLogs([]);
      setError(null);
      reconnectDelayRef.current = 1000;
    }
  }, [effectiveTaskId]);

  // Effect B: SSE lifecycle — connects/disconnects stream, never touches logs
  useEffect(() => {
    if (!effectiveTaskId || isActive === false) {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      setConnected(false);
      return;
    }

    connectToEventSource();
  }, [effectiveTaskId, isActive, connectToEventSource]);

  // Effect C: supplemental merge — runs at most once per task completion
  // Appends any activity_log tail entries not already in the live buffer.
  useEffect(() => {
    if (
      !isActive &&
      supplementalLines &&
      supplementalLines.length > 0 &&
      effectiveTaskId &&
      effectiveTaskId !== mergedForTaskIdRef.current
    ) {
      mergedForTaskIdRef.current = effectiveTaskId;
      setLogs(prev => suffixOverlapMerge(prev, supplementalLines));
    }
  }, [isActive, supplementalLines, effectiveTaskId]);
```

### Step 5: Add the import for `suffixOverlapMerge`

At the top of the file, after the existing React imports, add:
```typescript
import { suffixOverlapMerge } from '@/lib/logViewer-utils';
```

### Step 6: TypeScript check

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```

Expected: no errors in `LogViewer.tsx`

### Step 7: Run all tests

```bash
cd packages/dashboard && pnpm test
```

Expected: all tests pass (nothing in LogViewer tests since we test the pure function separately)

### Step 8: Commit

```bash
cd packages/dashboard
git add src/components/LogViewer.tsx src/lib/logViewer-utils.ts
git commit -m "refactor(74b): split LogViewer effect into A/B/C — fix reset-on-completion bug"
```

---

## Task 3: Update TaskTerminalPanel — stable ID + completion banner

**Files:**
- Modify: `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx`

### Step 1: Read the current file

Read `packages/dashboard/src/components/tasks/TaskTerminalPanel.tsx` (53 lines).

### Step 2: Replace the entire file contents

```typescript
'use client';

import { useState, useEffect, useRef } from 'react';
import type { Task, TaskActivityEntry } from '@/lib/types';
import type { LogEntry } from '@/components/LogViewer';
import LogViewer from '@/components/LogViewer';
import StatusBadge from '@/components/common/StatusBadge';

interface TaskTerminalPanelProps {
  task: Task;
  onClose: () => void;
}

type BannerState = 'none' | 'syncing' | 'stored' | 'empty';

const BANNER_TEXT: Record<Exclude<BannerState, 'none'>, string> = {
  syncing: 'Task completed — syncing final log…',
  stored: 'Task completed — showing stored log',
  empty: 'Task completed',
};

function activityToLogEntries(entries: TaskActivityEntry[]): LogEntry[] {
  return entries.map(e => ({
    line: e.entry,
    stream: 'stdout' as const,
    timestamp: e.timestamp * 1000, // activity_log uses Unix seconds; LogViewer expects ms
  }));
}

export default function TaskTerminalPanel({ task, onClose }: TaskTerminalPanelProps) {
  const isActive = task.status === 'in_progress' || task.status === 'starting';

  // Stable logTaskId — advances only when user selects a genuinely different task.
  // task.id is a stable primitive string even when the task object is replaced by polling.
  const [logTaskId, setLogTaskId] = useState(task.id);
  useEffect(() => { setLogTaskId(task.id); }, [task.id]);

  // Banner state: tracks completion transition
  const [bannerState, setBannerState] = useState<BannerState>('none');

  // Completion edge detection: true → false triggers 'syncing' flash
  const wasActiveRef = useRef(isActive);
  useEffect(() => {
    if (wasActiveRef.current && !isActive) {
      setBannerState('syncing');
    }
    wasActiveRef.current = isActive;
  }, [isActive]);

  // Deterministic banner — keyed on activity_log presence, not async callback
  useEffect(() => {
    if (!isActive) {
      setBannerState(task.activity_log.length > 0 ? 'stored' : 'empty');
    }
  }, [isActive, task.activity_log.length]);

  // supplementalLines: activity_log entries for LogViewer Effect C to merge
  const supplementalLines = isActive ? undefined : activityToLogEntries(task.activity_log);

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
          className="text-gray-500 hover:text-gray-300 ml-1 flex-shrink-0 leading-none text-base"
          aria-label="Close terminal panel"
        >
          ×
        </button>
      </div>

      {/* Completion banner — non-blocking strip explaining source-of-truth transition */}
      {bannerState !== 'none' && (
        <div className="px-3 py-1 bg-gray-800 border-b border-gray-700 text-xs text-gray-500 flex-shrink-0 select-none">
          {BANNER_TEXT[bannerState]}
        </div>
      )}

      {/* Terminal body */}
      <div className="flex-1 overflow-hidden">
        <LogViewer
          taskId={logTaskId}
          isActive={isActive}
          supplementalLines={supplementalLines}
          hideHeader={true}
        />
      </div>
    </div>
  );
}
```

Note what changed from the original:
- Added `useState`, `useEffect`, `useRef` imports
- Added `BannerState` type + `BANNER_TEXT` map
- Added `logTaskId` state (stable, derived from `task.id`)
- Added completion edge detection (`wasActiveRef`)
- Added deterministic `bannerState` effect
- Replaced `staticLines={activityToLogEntries(task.activity_log)}` with `supplementalLines={supplementalLines}`
- Removed `staticLines` prop (no longer passed — LogViewer handles merge via Effect C)
- Added banner strip between header and terminal body

### Step 3: TypeScript check

```bash
cd packages/dashboard && pnpm tsc --noEmit 2>&1 | head -30
```

Expected: no errors

### Step 4: Run all tests

```bash
cd packages/dashboard && pnpm test
```

Expected: all pass

### Step 5: Commit

```bash
cd packages/dashboard
git add src/components/tasks/TaskTerminalPanel.tsx
git commit -m "feat(74b): stable logTaskId + completion banner in TaskTerminalPanel"
```

---

## Task 4: Smoke test — verify behavior in browser

Start the dashboard:
```bash
make dashboard
```

Open `http://localhost:6987` → Tasks page.

**Scenario A: Open already-completed task**
1. Click any task with status `completed` or `failed`
2. Expect: terminal panel opens with activity_log entries displayed (no "Waiting for output…" flash)
3. Expect: banner shows `"Task completed — showing stored log"` (or `"Task completed"` if no activity_log)
4. Expect: close and reopen same task — same content, no flicker

**Scenario B: Watch an active task complete** (requires a running L3 task)
1. Click an `in_progress` task — stream should be live
2. Wait for it to complete
3. Expect: terminal panel does NOT clear — live output stays visible
4. Expect: banner transitions from nothing → `"Task completed — syncing final log…"` → `"Task completed — showing stored log"` within one render cycle
5. Expect: any tail lines from activity_log are appended smoothly (no reset, no doubling)

**Scenario C: Switch tasks**
1. Open task A (stream or static)
2. Click task B
3. Expect: panel content clears and shows task B output — this IS the intentional clear

**Scenario D: Edge case — close panel mid-stream**
1. Open an active task
2. Close the panel (`×`)
3. Reopen the same active task
4. Expect: buffer starts fresh (new SSE connection), not showing stale previous output

### Final commit if any small fixes needed

```bash
git add -A
git commit -m "fix(74b): smoke test fixes"
```

---

## Troubleshooting

**TypeScript error: `suffixOverlapMerge` not found**
Ensure `src/lib/logViewer-utils.ts` exports the function and the import path is `@/lib/logViewer-utils`.

**Banner stays 'syncing' forever**
The deterministic banner effect should overwrite 'syncing' on the next render. If it doesn't, check that `task.activity_log` is a stable array reference being updated by `useTasks` polling.

**Buffer still clears on completion**
Verify Effect A has `[effectiveTaskId]` in its dep array (not `[effectiveTaskId, isActive]`). The split is the fix — `isActive` must not be in Effect A's deps.

**Duplicate lines in terminal**
The overlap search in `suffixOverlapMerge` may be missing because the SSE stream's lines have trailing whitespace or ANSI codes that the activity_log does not. Check `normalizeLine` — extend it if needed.

**"— stored log (partial) —" divider appears unexpectedly**
This only appears when supplemental is >500 lines AND there is zero overlap. If activity_log is the full log (not just tail), this is expected. To suppress it, remove the `supplemental.length > OVERLAP_WINDOW` cap — but be aware you may double the entire output in the no-overlap case.
