# Phase 75: Unified Observability - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Consolidate metrics into a single unified endpoint that merges Python orchestration data with the existing dashboard-computed payload, and build a pipeline timeline UI showing L1→L2→L3 execution per task.

Covers OBSV-01 and OBSV-02 only. SOUL injection verification (OBSV-03) is Phase 76. No new event pipeline work — this phase consumes existing /api/pipeline and event stream.

</domain>

<decisions>
## Implementation Decisions

### Python metrics integration (OBSV-01)

- **Option A: Python writes a snapshot file** — `collect_metrics()` (or its call site in JarvisState) writes a `python-metrics.json` snapshot file to the project workspace directory alongside `workspace-state.json`. Next.js `/api/metrics` reads and merges it. No gateway hop, no new network dependency.
- **Snapshot write trigger**: Piggybacked on every `JarvisState._write_state_locked()` call — same hook as state writes. Throttle to max once per 500ms–1s to avoid disk thrash.
- **Atomic write**: Write to a temp file, then `os.replace()` (atomic rename). Dashboard always reads a complete snapshot.
- **File path convention**: Per-project, alongside workspace-state.json. Exact path resolved during planning (e.g. `{OPENCLAW_ROOT}/workspace/.openclaw/{project_id}/python-metrics.json`).
- **Include in snapshot**: `meta.generated_at` (unix timestamp), `meta.source_state_rev` (or last mtime of state file) for staleness tracking.

### Unified /api/metrics response shape

- Multi-source response with top-level namespacing:
  - `dashboard.*` — existing TS-computed metrics (tasks/lifecycle/pool/memory/usage/autonomy/durations) — unchanged
  - `python.*` — data from snapshot file (task counts, pool, memory health, autonomy from Python side)
  - `meta.*` — timestamps, snapshot age (seconds since `python.generated_at`), file mtime, versions
- Graceful degradation: if python-metrics.json is missing or stale, `python` key is null and `meta.snapshot_missing: true`. Dashboard still renders — show snapshot age in UI so operators know data freshness.

### Pipeline timeline — Mission Control (OBSV-02)

- **Inline expand in TaskPulse** — click a task row to expand/collapse in-place. No modal/drawer for the primary interaction.
- **Inline expansion content (tight, ≤3 lines)**:
  - Top: single-row pipeline strip with labeled segments (L1 → L2 → L3 and sub-stages if present)
  - Current stage emphasis + elapsed time (e.g. "L2 • 38s")
  - State badges: blocked / waiting / retrying / failed
  - One-line failure hint ("failed: tool timeout") — not full stack traces
  - Metadata row: started_at, total elapsed, current_stage_elapsed, attempt #, agent
  - Actions row: "View logs", "Retry", "Open details" (drawer — deferred to later)
- **Do NOT show inline**: full event logs, verbose diffs, multi-row history
- **Auto-expand triggers**: tasks in attention queue, failed/retrying tasks, tasks stuck past a threshold (e.g. L2 > N seconds)
- **Data fetch**: on expand, fetch `/api/pipeline?taskId=...` (short TTL cache per task). Optimistically update strip from live event stream; reconcile with pipeline API occasionally.
- **"Details" affordance**: optional — opens a right-side drawer for deep detail. Deferred — not in this phase.

### Pipeline timeline — Metrics page (OBSV-02)

- **New section appended at bottom of existing `/app/metrics/page.tsx`** — no new tab, no new route.
- Aggregate view: list of recent tasks (most recent ~20) with mini-pipeline timelines + filters for status, stage, and duration buckets.

### Missing timestamp handling

- **Show known stages only — no invented durations.**
- Stages with real timestamps → solid segments with duration label.
- Stages implied by task status but missing timestamps → faint/dashed placeholder (reserved space, no duration text).
- In-progress stage with known start → growing solid "in-progress" segment.
- In-progress stage with unknown start → highlighted placeholder + "in progress (start unknown)" label.
- Duration text only printed when both endpoints are known (or in-progress with known start).
- If key timestamps are absent: show "⚠ incomplete timing" tooltip in the expanded row.
- Keep consistent strip layout by reserving space for missing stages (placeholder) — don't compute estimated lengths.

### API / data model

- Consume existing `/api/pipeline/route.ts` as-is (already returns 6-stage pipeline per task: L1 Dispatch, L2 Routing, L3 Spawn, L3 Execution, L2 Review, Merge).
- Build `PipelineTimeline` component around the existing response shape; no re-derivation of timing in browser.
- If the API response shape needs extending (e.g. per-task fetch by taskId), add `?taskId=` query param support to the existing route rather than creating a new endpoint.

### Claude's Discretion

- Exact throttle interval for snapshot writes (500ms–1s range)
- Strip segment color coding (e.g. blue = active, green = done, red = failed, gray = placeholder)
- Exact height/padding of expanded TaskPulse rows
- Whether to extract `PipelineStrip` as a shared component used by both Mission Control and Metrics page (likely yes, but planner decides)

</decisions>

<specifics>
## Specific Ideas

- "Mission Control is an operations console — you're scanning, triaging, bouncing between tasks fast. Inline expansion keeps you in the flow."
- "Inline = strip + key facts. Drawer = deep detail on demand." — two levels of disclosure, drawer deferred.
- Shift-click (or a "pin" icon) to keep multiple tasks expanded simultaneously — planner can add this if simple.
- Timeline philosophy: "Mission Control is for truthy operational signals. If you start filling gaps, people will trust the pretty bar and miss the real uncertainty."
- Snapshot meta: show "Python snapshot age: 12s" in metrics UI so operators can gauge data freshness at a glance.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- `/app/api/metrics/route.ts`: Already a comprehensive unified endpoint — reads workspace-state.json directly, aggregates lifecycle/pool/memory/usage/autonomy. Phase 75 adds `python.*` and `meta.*` sections by reading the new snapshot file.
- `/app/api/pipeline/route.ts`: Fully implemented — returns 6-stage pipeline for all recent tasks. Needs `?taskId=` filtering added.
- `packages/orchestration/src/openclaw/metrics.py`: `collect_metrics(project_id)` already returns task counts, pool, memory, autonomy. This is the source for the Python snapshot.
- `packages/orchestration/src/openclaw/state_engine.py`: `JarvisState._write_state_locked()` is the natural hook point for snapshot writes.
- `packages/dashboard/src/components/metrics/` directory: MetricCard, StatusDistributionChart, TrendLineChart, AgentLeaderboard, TaskDataTable, TimeRangeSelector — established component patterns to follow.
- `packages/dashboard/src/components/mission-control/TaskPulse.tsx`: The task list component that gets inline expand added.

### Established Patterns

- **File reading pattern**: Dashboard reads workspace files directly via `fs/promises` — no gateway proxy for data. `OPENCLAW_ROOT` env var as root. `withAuth()` middleware wrapper on all API routes.
- **Atomic writes in Python**: Use `tempfile` + `os.replace()` (established pattern for state engine backups).
- **Component style**: Tailwind CSS, dark mode variants (`dark:bg-gray-800`), rounded-xl cards, status badges.
- **Data fetching in dashboard**: SWR hooks in `src/lib/hooks/` — pipeline data should follow this pattern (`usePipeline` hook).

### Integration Points

- `JarvisState._write_state_locked()` → call `write_python_metrics_snapshot()` after successful state write (throttled)
- `/api/metrics/route.ts` → add snapshot file read alongside existing `getTaskState()` / `getProject()` calls
- `/api/pipeline/route.ts` → add `taskId` query param filter
- `TaskPulse.tsx` → add click handler + expandable row with `PipelineStrip` component
- `packages/dashboard/src/app/metrics/page.tsx` → append `PipelineSection` at bottom

</code_context>

<deferred>
## Deferred Ideas

- Right-side drawer for deep task detail (full pipeline + logs) — user confirmed it's the second disclosure level but explicitly deferred from this phase
- Prometheus /metrics endpoint — out of scope for v2.1 per REQUIREMENTS.md
- Event persistence / replay — deferred to v2.2

</deferred>

---

*Phase: 75-unified-observability*
*Context gathered: 2026-03-05*
