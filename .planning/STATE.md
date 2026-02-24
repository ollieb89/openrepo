# Project State: OpenClaw

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.
**Current focus:** v1.2 Orchestration Hardening — Phase 23: Pool Config

## Current Position

Phase: 23 of 25 (Pool Config)
Plan: 2 of 2 in current phase (23-01 complete, 23-02 pending)
Status: Phase 23 in progress — 23-01-PLAN.md complete (POOL-01: config-driven PoolRegistry)
Last activity: 2026-02-24 — 23-01-PLAN.md complete (POOL-01: get_pool_config + hot-reload PoolRegistry)

Progress: [██░░░░░░░░░░░░░░░░░░] 10% (v1.2)

## Performance Metrics

**Velocity:**
- v1.0: 10 phases, 25 plans across 7 days
- v1.1: 8 phases, 17 plans in ~5 hours

**By Phase (v1.2):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19-structured-logging P01 | 1 | 2 tasks | 4 files |
| 19-structured-logging P02 | 1 | 2 tasks | 3 files |
| 20-reliability-hardening P01 | 1 | 2 tasks | 3 files |
| 20-reliability-hardening P02 | 1 | 2 tasks | 3 files |
| 21-state-engine-performance P01 | 1 | 2 tasks | 2 files |
| 21-state-engine-performance P02 | 1 | 2 tasks | 2 files |
| 21-state-engine-performance P03 | 1 | 1 task | 2 files |
| 22-observability-metrics P01 | 1 | 2 tasks | 4 files |
| 22-observability-metrics P02 | 1 | 2 tasks | 2 files |
| 23-pool-config P01 | 1 | 2 tasks | 4 files |
| 25-monitor-cache-fix P01 | 1 | 2 tasks | 1 file |

*Updated after each plan completion*

## Accumulated Context

### Decisions

All v1.0 and v1.1 decisions logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Shell injection hotfix committed before v1.2 (execSync → execFileSync in router_skill)
- L3 pool isolation is shared by default; per-project isolated pools targeted in Phase 23
- [Phase 19-structured-logging]: Use Python stdlib logging only — no external deps, emit to stderr, component field strips openclaw. prefix
- [Phase 19-02]: L3 container stdout relay logged at DEBUG with output field; log streaming errors downgraded to debug (expected on task end)
- [Phase 20-01]: Post-write backup (not pre-write) is correct semantics for last-known-good state — _create_backup called after json.dump/f.flush in _write_state_locked
- [Phase 20-02]: Collect-all strategy for both validators; validate_project_config wired into load_project_config; load_and_validate_openclaw_config added as explicit validated loader
- [Phase 21-01]: No threading locks on Docker client singleton — docker.DockerClient is thread-safe; ping-on-reuse pattern for transparent daemon restart recovery
- [Phase 21-02]: mtime is primary cache invalidation signal; TTL (5s) is safety net only. Deep copy on both cache store and retrieval. Cache check before any lock acquisition — zero contention on cache hits.
- [Phase 21-03]: PERF-03 requirement updated to describe write-through cache semantics — JSON requires atomic full rewrites; the real performance gain is cache elimination of redundant re-reads after writes (no code changes needed, requirement text was the gap)
- [Phase 22-observability-metrics]: rotate_activity_log acquires its own lock separate from update_task — fast-path cache check avoids lock when within threshold, break replaces return in update_task retry loop to enable post-write rotation
- [Phase 22-observability-metrics]: lock_wait_ms tracked by pool.py as wall-clock time around state engine calls (not internal fcntl spin) — practical proxy without changing _acquire_lock return type
- [Phase 22-observability-metrics]: Saturation detection via semaphore._value==0 before async with — no side effects, no additional synchronization
- [Phase 22-observability-metrics]: Monitor pool subcommand computes aggregates on-the-fly from state file — works when pool process is not running, consistent with CONTEXT.md
- [Phase 25-monitor-cache-fix]: js_instances is function-local to tail_state() (not module-level) — implicit teardown on exit; evict on any read exception for resilient mid-session recovery
- [Phase 23-pool-config]: Pool config reads project.json fresh on every get_pool() call — supports hot-reload without restart
- [Phase 23-pool-config]: Invalid pool config values log a warning and fall back to defaults — never raise, never block spawns
- [Phase 23-pool-config]: max_per_project removed from PoolRegistry; config-driven via get_pool_config() with _POOL_DEFAULTS fallback; _pool_config attached to pool instances for Plan 02 overflow policy

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 23-01-PLAN.md (config-driven PoolRegistry with hot-reload; POOL-01 complete; Phase 23 Plan 1 of 2 done)
Resume file: None
