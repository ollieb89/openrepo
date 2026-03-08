# Phase 75: Unified Observability - Research

**Researched:** 2026-03-05
**Domain:** Python snapshot file integration, Next.js API route extension, React pipeline timeline UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Python metrics integration (OBSV-01)**
- Option A only: Python writes `python-metrics.json` snapshot file per-project alongside `workspace-state.json`. No gateway hop, no new network dependency.
- Snapshot write is piggybacked on every `JarvisState._write_state_locked()` call, throttled to max once per 500ms–1s.
- Atomic write: temp file + `os.replace()` (atomic rename).
- File path: `{OPENCLAW_ROOT}/workspace/.openclaw/{project_id}/python-metrics.json` (exact path resolved during planning).
- Snapshot includes `meta.generated_at` (unix timestamp) and `meta.source_state_rev` (last mtime of state file).

**Unified /api/metrics response shape**
- Top-level namespacing: `dashboard.*` (existing TS-computed), `python.*` (from snapshot), `meta.*` (timestamps, snapshot age, versions).
- Graceful degradation: if python-metrics.json missing or stale, `python` key is null and `meta.snapshot_missing: true`. Dashboard still renders.
- Show snapshot age in UI so operators know data freshness.

**Pipeline timeline — Mission Control (OBSV-02)**
- Inline expand in TaskPulse — click a task row to expand/collapse in-place. No modal/drawer in this phase.
- Inline expansion content (tight, <=3 lines): single-row pipeline strip, current stage emphasis + elapsed, state badges, one-line failure hint, metadata row, actions row ("View logs", "Retry").
- Do NOT show inline: full event logs, verbose diffs, multi-row history.
- Auto-expand triggers: tasks in attention queue, failed/retrying tasks, tasks stuck past threshold.
- Data fetch on expand: `/api/pipeline?taskId=...` (short TTL cache per task). Optimistic update from live event stream.
- "Details" drawer deferred — not in this phase.

**Pipeline timeline — Metrics page (OBSV-02)**
- New section appended at bottom of existing `/app/metrics/page.tsx` — no new tab, no new route.
- Aggregate view: ~20 recent tasks with mini-pipeline timelines + filters for status, stage, duration buckets.

**Missing timestamp handling**
- Show known stages only — no invented durations.
- Real timestamps → solid segments with duration label.
- Implied stages (no timestamp) → faint/dashed placeholder (reserved space, no duration text).
- In-progress with known start → growing solid in-progress segment.
- In-progress with unknown start → highlighted placeholder + "in progress (start unknown)" label.
- Duration text only when both endpoints known (or in-progress with known start).
- If key timestamps absent: "⚠ incomplete timing" tooltip in expanded row.
- Consistent strip layout — reserve space for missing stages, do NOT compute estimated lengths.

**API / data model**
- Consume existing `/api/pipeline/route.ts` as-is (6-stage pipeline: L1 Dispatch, L2 Routing, L3 Spawn, L3 Execution, L2 Review, Merge).
- Add `?taskId=` query param filter to existing route rather than new endpoint.
- No re-derivation of timing in browser — use API response shape directly.

### Claude's Discretion
- Exact throttle interval for snapshot writes (500ms–1s range)
- Strip segment color coding (blue = active, green = done, red = failed, gray = placeholder)
- Exact height/padding of expanded TaskPulse rows
- Whether to extract `PipelineStrip` as shared component used by both Mission Control and Metrics page (likely yes)

### Deferred Ideas (OUT OF SCOPE)
- Right-side drawer for deep task detail — second disclosure level, explicitly deferred
- Prometheus /metrics endpoint — out of scope for v2.1
- Event persistence / replay — deferred to v2.2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| OBSV-01 | Unified /api/metrics endpoint consolidates Python orchestration metrics and dashboard-computed metrics | Python snapshot write pattern in state_engine.py, existing /api/metrics/route.ts structure, graceful degradation strategy |
| OBSV-02 | Pipeline timeline view shows L1 dispatch → L2 decomposition → L3 execution with timestamps and durations | Existing /api/pipeline/route.ts with 6-stage shape, TaskPulse.tsx inline expansion pattern, Metrics page append strategy |
</phase_requirements>

---

## Summary

Phase 75 implements two features on top of a largely complete foundation: a unified metrics endpoint that merges Python orchestration data (via a file snapshot) into the existing Next.js `/api/metrics` response, and a pipeline timeline UI at two sites (Mission Control TaskPulse inline expansion, Metrics page bottom section).

The dominant technical risk is the throttled snapshot write in `JarvisState._write_state_locked()` — this is a hot code path that must remain atomic and never block state writes if the snapshot write fails. The pattern is already established in the codebase (the `.bak` backup uses `shutil.copy2` inside the same write path), so the pattern is safe to follow. The snapshot write must be wrapped in a broad try/except and must run after the successful state write completes.

On the dashboard side, both the pipeline strip and the TaskPulse expansion are net-new React components with no close analogs in the current component library. The closest pattern is `MetricCard` (pure display, Tailwind, dark mode). The pipeline strip is a horizontal proportional timeline — this is pure CSS/Tailwind with no third-party charting library needed.

**Primary recommendation:** Build the Python snapshot writer as a standalone helper function `write_python_metrics_snapshot(project_id, state)` called from `_write_state_locked` after the successful write. Extract `PipelineStrip` as a shared component consumed by both `TaskPulse` expansion and `PipelineSection` on the Metrics page. Add `?taskId=` filter to `/api/pipeline/route.ts` and a `usePipeline` SWR hook.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `tempfile` + `os.replace()` | stdlib | Atomic snapshot file writes | Already used for state engine backup pattern; POSIX-guaranteed atomicity on same filesystem |
| `time.time()` | stdlib | Unix timestamps for `generated_at` | Already used throughout state_engine.py |
| Next.js `fs/promises` `readFile` | built-in | Dashboard reads snapshot file | Already established pattern in `/api/metrics/route.ts` (`readFile` for `usage.ndjson`) |
| SWR | ^2.x | Data fetching + per-task cache | Already used for all dashboard hooks (`useTasks`, `useConnectorStatus`, etc.) |
| Tailwind CSS | ^3.x | Strip segment styling | Project-wide styling system |
| React `useState` / `useCallback` | built-in | Inline expansion state management | Already used in `metrics/page.tsx` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `threading.Timer` or `time.time()` comparison | stdlib | Throttle snapshot writes to <=1 write/500ms | For the snapshot write throttle — no external dep needed |
| `json` | stdlib | Serialize snapshot to disk | Standard serialization |
| Next.js `path` + `os` | built-in | Resolve `OPENCLAW_ROOT` + snapshot file path | Follows existing pattern in `/api/metrics/route.ts` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| File snapshot (Option A) | Gateway HTTP endpoint (Option B) | Gateway hop adds latency + network dep; file is simpler and consistent with existing state pattern |
| CSS Tailwind strip | Recharts / D3 timeline | Third-party libs add bundle weight; the strip is a proportional div layout, pure Tailwind is sufficient |
| SWR per-task fetch | Polling setInterval | SWR provides deduplication, per-key TTL, and optimistic update; it's the project standard |

**Installation:** No new packages required for either Python or TypeScript work.

---

## Architecture Patterns

### Recommended Project Structure

New files this phase creates:

```
packages/orchestration/src/openclaw/
├── metrics.py                    # EXISTING — add write_python_metrics_snapshot()
└── state_engine.py               # EXISTING — call snapshot writer from _write_state_locked()

packages/dashboard/src/
├── app/api/metrics/route.ts      # EXISTING — merge python snapshot into response
├── app/api/pipeline/route.ts     # EXISTING — add ?taskId= filter
├── app/metrics/page.tsx          # EXISTING — append PipelineSection at bottom
├── components/
│   ├── mission-control/
│   │   └── TaskPulse.tsx         # EXISTING — add inline expand
│   └── metrics/
│       ├── PipelineStrip.tsx     # NEW — shared strip component
│       └── PipelineSection.tsx   # NEW — Metrics page pipeline list
└── lib/hooks/
    └── usePipeline.ts            # NEW — SWR hook for /api/pipeline
```

### Pattern 1: Atomic Snapshot Write in Python

**What:** After a successful state write in `_write_state_locked()`, call a throttled helper that serializes `collect_metrics()` output plus metadata to a temp file and atomically renames it into place.

**When to use:** Every state write, throttled to prevent disk thrash at <=1 write per 500ms per project.

**Example:**
```python
# In metrics.py — new function
import os
import json
import tempfile
import time
from pathlib import Path

_last_snapshot_times: dict[str, float] = {}
_SNAPSHOT_THROTTLE_S = 0.75  # 750ms — within the 500ms–1s discretion range

def write_python_metrics_snapshot(project_id: str, state_file: Path) -> None:
    """Write python-metrics.json alongside workspace-state.json.

    Throttled to avoid disk thrash. Atomic write via temp file + os.replace().
    Never raises — failure is logged and swallowed; state writes must not fail.
    """
    try:
        now = time.time()
        last = _last_snapshot_times.get(project_id, 0.0)
        if now - last < _SNAPSHOT_THROTTLE_S:
            return  # Throttled — skip this write
        _last_snapshot_times[project_id] = now

        snapshot_path = state_file.parent / "python-metrics.json"
        metrics = collect_metrics(project_id)
        payload = {
            "python": metrics,
            "meta": {
                "generated_at": now,
                "source_state_mtime": state_file.stat().st_mtime if state_file.exists() else None,
            },
        }
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            dir=snapshot_path.parent,
            prefix=".python-metrics-",
            suffix=".tmp",
            delete=False,
        )
        try:
            json.dump(payload, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp.name, snapshot_path)
        except Exception:
            tmp.close()
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise
    except Exception as exc:
        # Never propagate — snapshot failure must not abort state writes
        from .logging import get_logger
        get_logger("metrics").warning(
            "python-metrics snapshot write failed (non-fatal)",
            extra={"project_id": project_id, "error": str(exc)},
        )
```

### Pattern 2: Reading Snapshot in /api/metrics Route

**What:** After reading task state and project, also read `python-metrics.json` from the same project directory. Merge into response with top-level `python.*` and `meta.*` namespacing.

**When to use:** Every GET to `/api/metrics`. Missing file → null + staleness flag.

**Example:**
```typescript
// In /api/metrics/route.ts — additions
const snapshotPath = path.join(
  OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'python-metrics.json'
);

async function readPythonSnapshot(
  snapshotPath: string
): Promise<{ python: unknown; meta: { snapshot_missing: boolean; snapshot_age_s: number | null } }> {
  try {
    const raw = await readFile(snapshotPath, 'utf-8');
    const parsed = JSON.parse(raw);
    const generatedAt: number = parsed.meta?.generated_at ?? 0;
    const ageS = generatedAt > 0 ? Math.round(Date.now() / 1000 - generatedAt) : null;
    return {
      python: parsed.python ?? null,
      meta: { snapshot_missing: false, snapshot_age_s: ageS },
    };
  } catch {
    return { python: null, meta: { snapshot_missing: true, snapshot_age_s: null } };
  }
}
```

### Pattern 3: PipelineStrip Component

**What:** A horizontal strip of labeled segments for a single task's pipeline. Each segment gets a fixed proportional width allocation (1/6 each of 6 stages). Solid fill for known states, dashed/faint for placeholders, animated pulse for in-progress.

**When to use:** Both in TaskPulse inline expansion and Metrics page PipelineSection.

**Example:**
```typescript
// Segment color map — Claude's discretion per CONTEXT.md
const STAGE_COLORS = {
  completed: 'bg-green-500 dark:bg-green-600',
  active:    'bg-blue-500 dark:bg-blue-600 animate-pulse',
  failed:    'bg-red-500 dark:bg-red-600',
  pending:   'bg-gray-200 dark:bg-gray-700 border border-dashed border-gray-400',
} as const;

interface PipelineStripProps {
  stages: PipelineStage[];   // From /api/pipeline response shape
  compact?: boolean;         // true for Metrics page mini-strip
}
```

### Pattern 4: usePipeline SWR Hook

**What:** SWR hook fetching `/api/pipeline?project=X&taskId=Y`. Per-task key ensures independent TTLs and no cross-task cache pollution.

**When to use:** TaskPulse expansion (triggered on click, short TTL 5s). Metrics page PipelineSection (longer TTL 10s, all tasks).

**Example:**
```typescript
// src/lib/hooks/usePipeline.ts
import useSWR from 'swr';
import { apiJson } from '@/lib/api-client';

export function usePipeline(projectId: string | null, taskId?: string) {
  const key = projectId
    ? `/api/pipeline?project=${projectId}${taskId ? `&taskId=${taskId}` : ''}`
    : null;

  const { data, error, isLoading } = useSWR(key, (url) => apiJson(url), {
    refreshInterval: taskId ? 5000 : 10000,
    revalidateOnFocus: false,
  });

  return {
    pipelines: (data as any)?.pipelines ?? [],
    isLoading,
    error,
  };
}
```

### Pattern 5: TaskPulse Inline Expansion

**What:** Replace `<Link>` wrapper on task rows with a `<div>` that tracks `expandedTaskId` state. On click, render the `PipelineStrip` + metadata row below the task row. Shift-click (or pin icon) to keep multiple expanded simultaneously is listed as a simple-if-possible in CONTEXT.md.

**When to use:** Mission Control dashboard.

**Example (state management):**
```typescript
// Replaces current Link-per-row pattern
const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

const handleRowClick = (taskId: string, e: React.MouseEvent) => {
  setExpandedIds(prev => {
    const next = new Set(prev);
    if (e.shiftKey) {
      // Shift-click: toggle without clearing others
      next.has(taskId) ? next.delete(taskId) : next.add(taskId);
    } else {
      // Normal click: toggle, clear others
      if (next.has(taskId)) { next.clear(); }
      else { next.clear(); next.add(taskId); }
    }
    return next;
  });
};
```

### Anti-Patterns to Avoid

- **Blocking state writes on snapshot failures:** The snapshot write MUST be in a try/except that swallows all exceptions. A disk full or permission error must never surface to callers of `_write_state_locked`.
- **Module-level throttle dict race in concurrent Python contexts:** `_last_snapshot_times` is a module-level dict. In normal usage this is safe (GIL + single process). Do not use a threading.Lock on it — the cost is not worth it for a best-effort throttle.
- **Re-deriving timing from events in the browser:** The CONTEXT.md is explicit — use the API response shape directly. No client-side timestamp math.
- **Using `<Link>` wrapping the task row in TaskPulse:** The current code wraps each row in a `<Link>`. Expansion requires replacing `<Link>` with a clickable `<div>` and providing a separate "View details" affordance for navigation.
- **Inventing segment widths for missing-timestamp stages:** Reserved-space placeholders with equal widths for all 6 stages, no width calculation from timestamps (consistent layout per CONTEXT.md).
- **Importing `metrics.py` functions that call `JarvisState` inside `_write_state_locked`:** This would create a re-entrant lock acquisition. `write_python_metrics_snapshot` must use the already-computed `state` dict passed to it, or read from the metrics data already computed — it must NOT call `JarvisState.read_state()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | Custom write + rename logic | `tempfile.NamedTemporaryFile` + `os.replace()` | `os.replace()` is POSIX-atomic on same filesystem; already the backup pattern |
| Per-task SWR cache with TTL | Custom fetch cache | SWR `refreshInterval` + per-task key | SWR deduplicates, provides loading state, revalidates on demand |
| Pipeline data fetch | New API endpoint | `?taskId=` param on existing `/api/pipeline/route.ts` | Route already returns 6-stage data; adding a query param is minimal change |
| Timeline segment layout | SVG / D3 / canvas | CSS Tailwind `flex` divs with proportional equal widths | 6 fixed segments = simple flex layout; no runtime width calculation |

**Key insight:** The codebase already has all the data (workspace-state.json has task timestamps, pipeline route already derives stages). This phase is primarily plumbing (file-based IPC from Python to Next.js) and display (turning existing data into a visual strip).

---

## Common Pitfalls

### Pitfall 1: Re-entrant Lock in `_write_state_locked`

**What goes wrong:** `write_python_metrics_snapshot` calls `collect_metrics(project_id)` which instantiates a new `JarvisState(get_state_path(project_id))` and calls `read_state()`. This acquires `LOCK_SH` on the same file currently held under `LOCK_EX` by `_write_state_locked`. On Linux, `fcntl.flock` on the same fd from the same process re-grants the lock, but on a different fd it will block, causing a self-deadlock.

**Why it happens:** `collect_metrics` is a standalone function that independently reads state — not wrong in isolation, but dangerous when called from inside a write lock.

**How to avoid:** Pass the already-read `state` dict to `write_python_metrics_snapshot` as a parameter. The function uses the dict directly rather than reading state again. Alternatively, `collect_metrics` can be refactored to accept an optional pre-loaded state dict. Do NOT call `JarvisState.read_state()` from inside `_write_state_locked`.

**Warning signs:** Tests hang, or `LOCK_TIMEOUT` exceptions appear in state_engine tests.

### Pitfall 2: Module-Level `_last_snapshot_times` dict Leaking Between Tests

**What goes wrong:** The throttle dict is module-level. If one test writes to it and another test runs within 750ms, the second test's snapshot write is throttled and never happens — test assertions fail.

**Why it happens:** Module state persists across test functions in the same pytest session.

**How to avoid:** In tests, either: (a) monkeypatch `_SNAPSHOT_THROTTLE_S` to 0.0, or (b) clear `_last_snapshot_times` in a fixture. The test for `write_python_metrics_snapshot` should call `metrics._last_snapshot_times.clear()` before the test or set the throttle interval to 0.

### Pitfall 3: Stale `python-metrics.json` on First Dashboard Load

**What goes wrong:** Dashboard loads before any state write has happened (e.g., no tasks in project). `python-metrics.json` does not exist. `/api/metrics` handler attempts `readFile` and throws `ENOENT`.

**Why it happens:** The snapshot file is only written on state writes — it does not exist until the first `_write_state_locked` call.

**How to avoid:** The `readPythonSnapshot` helper must catch all errors (including `ENOENT`) and return `{ python: null, meta: { snapshot_missing: true } }`. The existing pattern in `/api/metrics/route.ts` for `usage.ndjson` (`code !== 'ENOENT'` check) shows the established approach — but for snapshots, swallow ALL errors and return the null response.

### Pitfall 4: TaskPulse `<Link>` → `<div>` Breaks Keyboard Navigation

**What goes wrong:** Replacing `<Link>` with a clickable `<div>` removes keyboard accessibility (Tab + Enter navigation to task detail).

**Why it happens:** `<div onClick>` is not focusable or keyboard-activatable by default.

**How to avoid:** Add `tabIndex={0}`, `role="button"`, and `onKeyDown` handler (Enter/Space triggers expand). Keep a separate `<a>` or `<Link>` for the "View all tasks" affordance and "View logs" action button.

### Pitfall 5: Proportional Strip Segment Widths vs. Equal Widths

**What goes wrong:** Temptation to compute segment widths proportionally from actual durations (e.g., L3 Execution took 80% of total time, so it gets 80% of the strip width). This fails when timestamps are missing — segments with no duration data would collapse to zero width, breaking layout consistency.

**Why it happens:** Proportional timeline is visually intuitive but the CONTEXT.md philosophy is explicitly "no invented durations, consistent layout."

**How to avoid:** Use equal fixed widths for all 6 stages (`w-1/6` each in Tailwind, or `flex: 1` per segment). The solid/dashed fill communicates status; the duration label text communicates timing. Layout never depends on actual timestamp values.

---

## Code Examples

Verified patterns from existing codebase:

### Atomic Write Pattern (from state_engine.py backup)
```python
# Source: packages/orchestration/src/openclaw/state_engine.py _create_backup()
# Pattern: same filesystem guarantees atomicity of os.replace()
if self.state_file.exists() and self.state_file.stat().st_size > 0:
    backup_path = self.state_file.with_suffix('.json.bak')
    shutil.copy2(self.state_file, backup_path)
```

For the snapshot, prefer `tempfile` + `os.replace()` over `shutil.copy2` because we are writing new content, not copying:
```python
# os.replace() is atomic on POSIX if src and dst on same filesystem
os.replace(tmp.name, snapshot_path)
```

### Reading Optional File in Next.js (from /api/metrics/route.ts)
```typescript
// Source: packages/dashboard/src/app/api/metrics/route.ts lines 47-58
const usagePath = path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'usage.ndjson');
try {
  const raw = await readFile(usagePath, 'utf-8');
  const agg = aggregateTodayUsage(raw.split('\n'));
  return { present: true, tokens: agg.tokens, costUsd: agg.costUsd };
} catch (err: unknown) {
  if ((err as NodeJS.ErrnoException).code !== 'ENOENT') {
    console.error('[metrics] Failed to read usage.ndjson:', err);
  }
  return { present: false, tokens: 0, costUsd: 0 };
}
```

For the snapshot, swallow all errors (not just ENOENT) because the file is best-effort:
```typescript
try {
  const raw = await readFile(snapshotPath, 'utf-8');
  // ... parse and return
} catch {
  return { python: null, meta: { snapshot_missing: true, snapshot_age_s: null } };
}
```

### SWR Hook Pattern (from useTasks.ts)
```typescript
// Source: packages/dashboard/src/lib/hooks/useTasks.ts
import useSWR from 'swr';
const { data, error, isLoading } = useSWR<{ tasks: Task[] }>(
  projectId ? `/api/tasks?project=${projectId}` : null,
  fetcher,
  { refreshInterval: 3000, revalidateOnFocus: false }
);
```

### Pipeline API Response Shape (from /api/pipeline/route.ts)
```typescript
// Source: packages/dashboard/src/app/api/pipeline/route.ts
interface PipelineStage {
  name: string;                              // 'L1 Dispatch' | 'L2 Routing' | 'L3 Spawn' | 'L3 Execution' | 'L2 Review' | 'Merge'
  status: 'pending' | 'active' | 'completed' | 'failed';
  timestamp?: number;                        // Unix seconds (from task metadata)
  duration?: number;                         // seconds
  agent?: string;
}
interface PipelineItem {
  taskId: string;
  projectId: string;
  stages: PipelineStage[];                   // Always 6 entries
  totalDuration?: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}
// Response: { projectId, pipelines: PipelineItem[], timestamp: string }
```

### Adding taskId Filter to Pipeline Route
```typescript
// In /api/pipeline/route.ts handler — add after existing projectId resolution
const taskId = searchParams.get('taskId');

// After building pipelines array:
const filtered = taskId
  ? pipelines.filter(p => p.taskId === taskId)
  : pipelines.slice(0, 20);

return NextResponse.json({
  projectId,
  pipelines: filtered,
  timestamp: new Date().toISOString(),
});
```

### Tailwind Pipeline Strip (CSS layout)
```tsx
// Equal-width segments — proportional to nothing, consistent layout
<div className="flex gap-0.5 w-full h-4 rounded overflow-hidden">
  {stages.map((stage, i) => (
    <div
      key={i}
      title={`${stage.name}: ${stage.status}${stage.duration ? ` (${stage.duration.toFixed(0)}s)` : ''}`}
      className={`flex-1 ${STAGE_COLORS[stage.status]} rounded-sm`}
    />
  ))}
</div>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Gateway HTTP polling for Python metrics | File snapshot (same filesystem) | Phase 75 decision | Eliminates network dep; atomic reads |
| `<Link>` per task row in TaskPulse | Clickable `<div>` with expandable detail | Phase 75 | Enables in-place expansion without navigation |
| Metrics page ends at TaskDataTable | PipelineSection appended at bottom | Phase 75 | No new route needed |

**Deprecated/outdated:**
- None — this phase extends existing files rather than replacing patterns.

---

## Open Questions

1. **`collect_metrics` calling `JarvisState.read_state()` inside write lock**
   - What we know: The current `collect_metrics(project_id)` creates a new `JarvisState` instance and calls `read_state()`. If called from `_write_state_locked`, this opens a new fd and attempts `LOCK_SH` — which on Linux will block until `LOCK_EX` is released (deadlock from same process on different fd).
   - What's unclear: Whether the planner will pass the already-read `state` dict as a parameter to `write_python_metrics_snapshot`, or refactor `collect_metrics` to optionally accept a pre-loaded state. Either approach resolves the issue.
   - Recommendation: `write_python_metrics_snapshot(project_id, state_file, state_dict)` accepts the dict already in memory. `collect_metrics` is not called from inside the lock.

2. **`meta.source_state_rev` field name**
   - What we know: CONTEXT.md says "source_state_rev (or last mtime of state file)."
   - What's unclear: Whether this should be an opaque revision counter or the raw mtime float. The state engine has no revision counter — mtime is the only available value.
   - Recommendation: Use `source_state_mtime` (a float, unix seconds) rather than inventing a counter. Simpler and consistent with how the state engine tracks cache validity.

3. **Auto-expand threshold for "stuck" L2 tasks**
   - What we know: CONTEXT.md says "tasks stuck past a threshold (e.g. L2 > N seconds)" should auto-expand.
   - What's unclear: The value of N and where it's stored (hardcoded vs configurable).
   - Recommendation: Hardcode N = 60 seconds for this phase (consistent with existing timeout conventions). Configurable version is a v2.2 enhancement.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest (uv run pytest) |
| TypeScript framework | vitest |
| Python config file | `packages/orchestration/pyproject.toml` |
| TypeScript config file | `packages/dashboard/vitest.config.ts` |
| Python quick run | `uv run pytest packages/orchestration/tests/test_metrics.py -x` |
| Python full suite | `uv run pytest packages/orchestration/tests/ -v` |
| TypeScript quick run | `cd packages/dashboard && pnpm vitest run tests/api/metrics/` |
| TypeScript full suite | `cd packages/dashboard && pnpm vitest run` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBSV-01 | `write_python_metrics_snapshot` writes valid JSON at expected path atomically | unit (pytest) | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -x` | ❌ Wave 0 |
| OBSV-01 | Throttle: second write within 750ms is skipped | unit (pytest) | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py::test_throttle -x` | ❌ Wave 0 |
| OBSV-01 | Snapshot failure does not raise from `_write_state_locked` | unit (pytest) | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py::test_failure_swallowed -x` | ❌ Wave 0 |
| OBSV-01 | `/api/metrics` response includes `python.*` and `meta.*` keys when snapshot present | unit (vitest) | `cd packages/dashboard && pnpm vitest run tests/api/metrics/unified-metrics.test.ts` | ❌ Wave 0 |
| OBSV-01 | `/api/metrics` returns `python: null, meta.snapshot_missing: true` when snapshot absent | unit (vitest) | `cd packages/dashboard && pnpm vitest run tests/api/metrics/unified-metrics.test.ts` | ❌ Wave 0 |
| OBSV-02 | `/api/pipeline?taskId=X` returns only the matching task pipeline | unit (vitest) | `cd packages/dashboard && pnpm vitest run tests/api/pipeline/pipeline-filter.test.ts` | ❌ Wave 0 |
| OBSV-02 | `PipelineStrip` renders 6 equal-width segments | unit (vitest) | `cd packages/dashboard && pnpm vitest run tests/components/metrics/PipelineStrip.test.ts` | ❌ Wave 0 |
| OBSV-02 | `PipelineStrip` uses placeholder style for pending stages (no timestamp) | unit (vitest) | `cd packages/dashboard && pnpm vitest run tests/components/metrics/PipelineStrip.test.ts` | ❌ Wave 0 |
| OBSV-02 | TaskPulse expands inline on click, collapses on second click | unit (vitest node env) | `cd packages/dashboard && pnpm vitest run tests/components/mission-control/TaskPulse.test.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -x` and `cd packages/dashboard && pnpm vitest run tests/api/metrics/`
- **Per wave merge:** Full suite — `uv run pytest packages/orchestration/tests/ -v` and `cd packages/dashboard && pnpm vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `packages/orchestration/tests/test_python_metrics_snapshot.py` — covers OBSV-01 (atomic write, throttle, failure isolation, no re-entrant lock)
- [ ] `packages/dashboard/tests/api/metrics/unified-metrics.test.ts` — covers OBSV-01 (response shape, graceful degradation)
- [ ] `packages/dashboard/tests/api/pipeline/pipeline-filter.test.ts` — covers OBSV-02 (taskId filter)
- [ ] `packages/dashboard/tests/components/metrics/PipelineStrip.test.ts` — covers OBSV-02 (strip rendering, segment styles)
- [ ] `packages/dashboard/tests/components/mission-control/TaskPulse.test.ts` — covers OBSV-02 (inline expand/collapse)

Note: vitest config (`vitest.config.ts`) uses `environment: 'node'` and `include: ['tests/**/*.test.ts']`. PipelineStrip and TaskPulse tests should test pure logic/className functions exported as named exports (same pattern as `getTaskCardClassName` in `TaskCard.tsx`). If React rendering tests are needed, the vitest environment may need `jsdom` — but the existing pattern avoids full rendering in favor of testing exported pure functions.

---

## Sources

### Primary (HIGH confidence)

Direct codebase inspection — all findings below are from actual file reads:

- `packages/orchestration/src/openclaw/state_engine.py` — `_write_state_locked()` implementation, backup pattern, lock mechanics
- `packages/orchestration/src/openclaw/metrics.py` — `collect_metrics()` implementation and re-entrancy risk
- `packages/orchestration/src/openclaw/config.py` — `get_state_path()` path derivation convention
- `packages/dashboard/src/app/api/metrics/route.ts` — existing metrics response shape, `readFile` pattern for optional files, `OPENCLAW_ROOT` usage
- `packages/dashboard/src/app/api/pipeline/route.ts` — 6-stage `PipelineItem` shape, current response structure
- `packages/dashboard/src/components/mission-control/TaskPulse.tsx` — current `<Link>` per task row pattern
- `packages/dashboard/src/app/metrics/page.tsx` — existing component layout, append point
- `packages/dashboard/src/lib/hooks/useTasks.ts` — SWR hook pattern
- `packages/dashboard/src/lib/types.ts` — `MetricsResponse`, `Task`, `PipelineStage` types
- `packages/dashboard/vitest.config.ts` — test environment, include glob
- `packages/dashboard/tests/components/tasks/TaskCard.test.ts` — pure-function test export pattern
- `packages/dashboard/tests/api/metrics/usage-aggregator.test.ts` — vitest test style
- `.planning/config.json` — `nyquist_validation` key absent (treated as enabled)

### Secondary (MEDIUM confidence)

- Project CONTEXT.md decisions — locked by user, treated as authoritative constraints
- Project REQUIREMENTS.md — OBSV-01/02 definitions
- Project STATE.md — phase history and accumulated architectural decisions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in use in the codebase; no new dependencies
- Architecture: HIGH — patterns directly derived from existing code (state_engine backup, metrics route, SWR hooks)
- Pitfalls: HIGH — re-entrancy pitfall verified by reading actual `collect_metrics` and `_write_state_locked` implementations; not speculative

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable codebase; patterns will not change)
