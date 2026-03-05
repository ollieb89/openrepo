# Phase 74b: Stable Terminal Transition on Task Completion — Design

**Date:** 2026-03-05
**Depends on:** Phase 74 (Dashboard Streaming UI)
**Files changed:** `LogViewer.tsx`, `TaskTerminalPanel.tsx`

---

## Problem

When a task transitions from `in_progress` to `completed` while the terminal panel is open, two user-hostile things happen:

1. The terminal visually "rewinds" — the live SSE buffer is cleared at the exact moment the user expects final output lines to arrive.
2. The tail can be lost — any output not yet persisted to `activity_log` (flush delay, last chunk) disappears silently. Users see a shorter or different log than what actually ran.

This causes distrust ("did it really finish? did it crash?") even when the backend is healthy.

### Root cause

`LogViewer` has a single `useEffect([effectiveTaskId, connectToEventSource, isActive])` that conflates two responsibilities:

- **Task switched** → clear buffer, start fresh *(intentional)*
- **Active state changed** → connect/disconnect SSE *(should never touch buffer)*

When `isActive` flips, the effect re-runs and hits `setLogs([])` unconditionally. Combined with `TaskTerminalPanel` passing `taskId={undefined}` on completion (hitting the separate `!effectiveTaskId` clear path), the buffer is nuked twice.

---

## Goals

1. Eliminate the visual reset on task completion.
2. Append any activity_log tail not captured by the live stream (suffix-overlap merge).
3. Make the source-of-truth transition explicit to the user (banner).
4. Install a guardrail so future callers cannot accidentally reintroduce the reset.

---

## Non-Goals / Invariants

- **No server-side changes.** No sequence numbers, no new API endpoints.
- **No structural LogViewer API changes.** One optional prop added (`supplementalLines`); all existing props unchanged.
- **`TaskBoard.tsx` unchanged.**

**Core invariant:** `LogViewer` never clears logs due to `isActive` changes; only a real task switch clears the buffer.

---

## Architecture

Two files change. Everything else is untouched.

| File | Change |
|------|--------|
| `LogViewer.tsx` | Split single effect → Effect A + B + C; add `supplementalLines?` prop |
| `TaskTerminalPanel.tsx` | `logTaskId` state; completion edge detection; banner |

---

## LogViewer Changes

### 1. Split the single effect into three

#### Effect A — Log lifecycle (buffer clear only)

Deps: `[effectiveTaskId]` only.

Governed by this truth table. Uses `prevTaskIdRef` to distinguish transitions:

| prevId | nextId | Action |
|--------|--------|--------|
| `undefined` | non-null | Initialize: `setLogs([])`, reset error/backoff. Note: with stable `logTaskId` from TaskTerminalPanel, this path does NOT trigger at completion — only on first mount or real task switch. |
| non-null | `undefined` | Stop streaming — **preserve buffer. No `setLogs([])`**. This is the guardrail. |
| non-null A | non-null B (different) | Real task switch: `setLogs([])`, reset error/backoff. |
| same | same | No-op. |

Zero SSE code in this effect.

#### Effect B — SSE lifecycle

Deps: `[effectiveTaskId, isActive, connectToEventSource]`.

Responsible only for connect/disconnect. **Never touches `logs` state. No `setLogs` anywhere.**

When `!effectiveTaskId || isActive === false`: close EventSource, clear reconnect timer, set `connected = false`. Return.
When `effectiveTaskId && isActive`: call `connectToEventSource()`.

#### Effect C — Supplemental merge

Deps: `[isActive, supplementalLines]`.

Runs at most once per task completion. Guarded by `mergedForTaskIdRef`:

```
if (!isActive && supplementalLines?.length && effectiveTaskId !== mergedForTaskIdRef.current) {
  mergedForTaskIdRef.current = effectiveTaskId;
  setLogs(prev => suffixOverlapMerge(prev, supplementalLines));
}
```

The `mergedForTaskIdRef` prevents double-merge if `supplementalLines` changes while `isActive` remains false (e.g., activity_log backfills after initial completion).

### 2. Add `supplementalLines?: LogEntry[]` prop

Optional. No behavior change for callers that don't pass it. When provided and `isActive` flips to false, Effect C merges the tail into the live buffer directly. `displayLines` stays `logs` — no source-switching.

### 3. Suffix-overlap merge algorithm

**Purpose:** Append activity_log entries that arrived after the SSE stream ended, without duplicating content already in the live buffer.

**Window:** Constrain search to last `N = min(500, liveBuffer.length)` lines to bound runtime.

**Normalization (for comparison only, not mutation):**
- `\r\n` → `\n`
- strip trailing `\r`
- ANSI stripping: TODO comment — skip for now

**Algorithm:**
1. Search window = last N lines of `liveBuffer`
2. Find the largest `k` such that `liveBuffer[-k:]` matches `supplementalLines[0:k]` by normalized `line` content
3. If overlap found: append `supplementalLines[k:]` to buffer
4. If no overlap found:
   - If `supplementalLines.length > N`: append only `supplementalLines[-N:]` with a synthetic separator line `"— stored log (partial) —"` to signal truncation. Avoids worst-case doubling when activity_log contains the full log.
   - If `supplementalLines.length <= N`: append all of `supplementalLines`

**Why suffix-overlap and not dedupe-by-content:** Global dedup drops legitimate repeated lines (progress bars, "Retrying…", etc.). Suffix-overlap only deduplicates at the live↔stored boundary.

---

## TaskTerminalPanel Changes

### 1. Stable `logTaskId`

```typescript
const [logTaskId, setLogTaskId] = useState(task.id);

// task.id is a stable primitive string — same across polling-replaced task objects.
// Advances only when user selects a genuinely different task.
useEffect(() => { setLogTaskId(task.id); }, [task.id]);
```

`logTaskId` is always a valid task ID, never `undefined`. Passed to `LogViewer` as `taskId={logTaskId}`.

> If `TaskBoard` exposes `selectedTaskId` as a prop in future, prefer keying off that primitive directly for even stronger clarity.

### 2. Completion edge detection

```typescript
const wasActiveRef = useRef(isActive);

useEffect(() => {
  if (wasActiveRef.current && !isActive) {
    // true → false edge: task just completed
    setBannerState('syncing');
  }
  wasActiveRef.current = isActive;
}, [isActive]);
```

### 3. `supplementalLines` wiring

```typescript
const supplementalLines = isActive ? undefined : activityToLogEntries(task.activity_log);
```

Passed to LogViewer. Effect C picks it up when `isActive` is false.

### 4. Banner state

```typescript
type BannerState = 'none' | 'syncing' | 'stored' | 'empty';
```

Deterministic transition — keyed on `activity_log` presence, no async callback needed:

| Condition | State |
|-----------|-------|
| `isActive === true` | `'none'` |
| `!isActive && activity_log.length > 0` | `'stored'` (transition from `'syncing'` after edge) |
| `!isActive && activity_log.length === 0` | `'empty'` |

Effect:
```typescript
useEffect(() => {
  if (!isActive) {
    setBannerState(task.activity_log.length > 0 ? 'stored' : 'empty');
  }
}, [isActive, task.activity_log.length]);
```

The `'syncing'` state is set on the completion edge (section 2 above) and immediately overwritten by this effect on the next render. This gives one render of "syncing" as a flash cue before the merge result is visible.

Banner renders as a small non-blocking strip above the terminal body:

| State | Text |
|-------|------|
| `syncing` | `"Task completed — syncing final log…"` |
| `stored` | `"Task completed — showing stored log"` |
| `empty` | `"Task completed"` |
| `none` | *(not rendered)* |

---

## Data Flow After This Change

```
User watching active task:
  LogViewer → SSE stream → logs[] → rendered

Task status transitions to 'completed':
  TaskTerminalPanel: isActive = false
    → Effect B: closes SSE, no logs touch
    → Effect A: effectiveTaskId unchanged → no-op
    → banner transitions 'none' → 'syncing' → 'stored'
    → supplementalLines = activityToLogEntries(activity_log)
    → Effect C: suffixOverlapMerge(logs, supplementalLines)
    → logs[] updated in place (appended, not replaced)
    → rendered: same buffer + any tail entries

User closes and reopens panel for completed task:
  logTaskId updates to task.id (same value — no-op if same task)
  isActive = false
  supplementalLines = activityToLogEntries(activity_log)
  LogViewer: no SSE opened (isActive=false), renders supplementalLines via displayLines
```

---

## What This Eliminates

| Before | After |
|--------|-------|
| Buffer cleared when `isActive` flips | Effect B never touches logs |
| Buffer cleared when `taskId → undefined` | Effect A guard: `undefined` = preserve buffer |
| Live output replaced by activity_log snapshot | Suffix-overlap merge appends tail in place |
| Silent source switch | Banner makes transition explicit |
| No protection against future regressions | `prevTaskIdRef` + Effect A/B split = structural guardrail |
