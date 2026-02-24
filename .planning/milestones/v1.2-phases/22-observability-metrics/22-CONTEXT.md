# Phase 22: Observability Metrics - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Instrument the orchestration layer so operators can see how long tasks take, how saturated each project's pool is, and the activity log stays bounded in size. Covers task timing metrics, pool utilization querying, activity log rotation, and saturation event logging. Dashboard integration and alerting are separate concerns.

</domain>

<decisions>
## Implementation Decisions

### Metric storage & retrieval
- Store task metrics (duration, lock wait, retry count) in workspace-state.json alongside existing task entries — no new files
- Track both `spawn_requested_at` and `container_started_at` timestamps per task, so operators can see queue wait vs execution time independently
- Task completion records `completed_at` — duration derived from timestamps

### Monitor CLI presentation
- Pool utilization display shows: active containers (N/max), queued tasks, completed count, semaphore saturation percentage
- Default (no argument) shows all projects in a table; passing a project ID filters to that project only
- Colored table output matching existing monitor.py patterns — color-code saturation levels (green/yellow/red)

### Saturation event definition
- Saturation event triggers when all semaphore slots are occupied AND a new task must queue (not just any queue activity)
- Log entry includes: project_id, queued task_id, current queue depth, list of active task_ids
- Log both saturation onset AND resolution (when a slot frees up after saturation) — lets operators see saturation duration
- Saturation events are structured log entries with project and task context

### Claude's Discretion
- Lock wait tracking approach (cumulative per task vs per-operation breakdown) — pick what fits state engine best
- Pool-level aggregate metrics (computed on-the-fly vs maintained running totals) — pick based on state engine patterns
- Pool CLI access pattern (new subcommand vs extending existing status) — pick based on existing monitor.py structure
- Whether saturation events also persist in state or remain log-only — pick based on state engine and logging architecture

</decisions>

<specifics>
## Specific Ideas

- Timestamps should enable operators to decompose total task time into: queue wait, startup, execution
- Saturation onset/resolution pairing is specifically for capacity planning — operators want to know "how long was the pool maxed out"
- Pool display should feel natural alongside existing `monitor.py tail`, `status`, and `task` subcommands

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-observability-metrics*
*Context gathered: 2026-02-24*
