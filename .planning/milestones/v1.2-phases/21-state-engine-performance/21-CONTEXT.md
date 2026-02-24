# Phase 21: State Engine Performance - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve orchestration throughput under concurrent spawns. Docker connections reused, state reads served from memory, file writes minimized to changed fields only. Covers PERF-01 (Docker client pooling), PERF-02 (in-memory caching), PERF-03 (incremental updates), PERF-04 (shared-lock reads).

</domain>

<decisions>
## Implementation Decisions

### Caching strategy
- Per-project caching — each project's state cached independently, matching existing per-project state file pattern
- No cross-project cache invalidation needed; project switch just uses that project's cache

### Incremental writes
- Task-level granularity — when a task's status changes, read full state, update only the changed task object, write back
- Lock + read-modify-write for concurrent writes — acquire exclusive lock, read latest, apply task change, write. Same pattern as current but scoped to changed task
- Write-through cache — after writing to disk, immediately update the in-memory cache (no extra disk read on next access)
- Full backups always — Phase 20's backup-before-write remains full-state snapshots; only the primary write path is incremental

### Claude's Discretion
- External modification detection method (mtime check vs file hash vs other approach)
- Cache hit/miss log level (structured logging from Phase 19)
- Corruption/missing file handling during cache refresh (integrate with Phase 20 recovery)
- Docker client pooling lifecycle — when to create/destroy, reconnection on daemon restart, per-project vs global
- Shared lock behavior for reads — timeout, fallback under contention

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Success criteria from roadmap are well-defined: reused Docker connections (log-verified), shared-lock reads, task-level disk writes, observable cache hit rate.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 21-state-engine-performance*
*Context gathered: 2026-02-24*
