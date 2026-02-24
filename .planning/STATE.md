# Project State: OpenClaw

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.
**Current focus:** v1.4 Operational Maturity — Phase 40: Memory Health Monitor

## Current Position

Phase: 40 of 42 (Memory Health Monitor) — IN PROGRESS
Plan: 1 of N in current phase
Status: Plan 01 complete — health scan backend API (QUAL-01..QUAL-04)
Last activity: 2026-02-24 — Phase 40 Plan 01 complete: health scan engine, three endpoints, 19 tests

Progress: [████░░░░░░] 40% (v1.4)

## Performance Metrics

**Velocity (prior milestones):**
- v1.0: 10 phases, 25 plans across 7 days
- v1.1: 8 phases, 17 plans in ~5 hours
- v1.2: 7 phases, 14 plans in ~1 day
- v1.3: 11 phases, 19 plans in 7 days

**v1.4:** 4 phases, TBD plans — 5 plans complete (Phase 39 Plans 01-04, Phase 40 Plan 01)

## Accumulated Context

### Decisions

All prior decisions logged in PROJECT.md Key Decisions table (v1.0–v1.3).

v1.4 research flags to carry into planning:
- Phase 39: asyncio SIGTERM + fcntl deadlock interaction — dehydration must use flag + `loop.add_signal_handler`, never direct `update_task()` from signal handler. Recovery loop needs `recovery_safe` flag check before re-spawning to avoid re-running tasks with existing git commits.
- Phase 41: Build the approval gate before the suggestion pipeline. SOUL diff validation rules (no safety constraint removal, no shell commands, max 100 lines) must be specified before coding the apply path.

**Phase 39 Plan 01 decisions:**
- CLI runtime backgrounded with pipe-to-tee + wait so PID 1 (bash) remains free to receive SIGTERM
- _child_pid captures tee PID (last pipeline stage); killing tee sends SIGPIPE to CLI runtime — acceptable shutdown path
- stop_timeout=30 in spawn.py matches drain window from CONTEXT.md; exceeds JarvisState LOCK_TIMEOUT (5s) plus overhead

**Phase 39 Plan 02 decisions:**
- Use loop.add_signal_handler() not signal.signal() — prevents fcntl deadlock if state engine holds lock at signal time
- Idempotency guard via mutable closure dict {"flag": False} — double SIGTERM silently ignored
- drain_pending_memorize_tasks() returns summary dict not raises — caller decides action
- 30s drain timeout matches stop_timeout=30 set in plan 01

**Phase 39 Plan 03 decisions:**
- auto_retry checks git branch for partial commits before re-queuing — falls back to mark_failed if commits exist (conservative, no data loss)
- Retry limit of 1 enforced via metadata.retry_count >= 1 — prevents infinite retry loops
- Missing spawn_requested_at treated as expired with warning log — silently skipping could mask orphaned tasks
- run_recovery_scan() always logs startup summary even when nothing recovered

**Phase 39 Plan 04 decisions:**
- pool_cfg set in both try and except paths so pool._pool_config is always a valid dict before run_recovery_scan() call
- run_recovery_scan() called unconditionally in spawn_task() — no conditional guard needed (scan handles empty state gracefully)

**Phase 40 Plan 01 decisions:**
- scan_engine.py extracted as stdlib-only module so algorithm is testable without pydantic/memu in root env
- Lazy imports of cosine_topk and pendulum inside function bodies — _check_staleness works without memu at import time
- user_id required (non-optional) in HealthScanRequest to prevent cross-project scope leak
- content required (non-optional) in MemoryUpdateRequest to prevent empty-body ValueError from memu CRUD
- last_reinforced_at absence treated as 'fresh' if created_at within retrieval_window — avoids false-positive stale flags
- Conflict pair deduplication via tuple(sorted([id_a, id_b])) seen-set

### Pending Todos

None.

### Blockers/Concerns

- Phase 39 Plan 01 RESOLVED: stop_timeout=30 added to spawn.py container_config.
- Phase 40: `PUT /memories/:id` endpoint schema needs confirmation against existing `memory_item` model before implementation to avoid schema migration.
- Phase 41: Rejection corpus may be too small for ≥3-cluster threshold at current project scale — track cluster hit rate early and add keyword-frequency fallback if needed.

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 40-01-PLAN.md — health scan engine + REST endpoints (QUAL-01..QUAL-04)
Resume: Phase 40 Plan 02 — dashboard health UI (QUAL-05, QUAL-06)
