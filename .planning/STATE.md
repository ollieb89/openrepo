# Project State: OpenClaw

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.
**Current focus:** v1.4 Tech Debt Cleanup — Phase 44: Plan 01 complete

## Current Position

Phase: 44 of 44 (v1.4 Tech Debt Cleanup) — COMPLETE
Plan: 1 of 1 complete in current phase
Status: Plan 01 complete — OPENCLAW_ROOT Makefile guard, README fix, SummaryStream.tsx parse error, stale-patch audit closure; 148/148 tests green
Last activity: 2026-02-25 — Phase 44 Plan 01 complete: v1.4 tech debt cleanup (TECH-DEBT-44-A, B, C)

Progress: [██████████] 100% (Phase 44 Plan 01 complete)

## Performance Metrics

**Velocity (prior milestones):**
- v1.0: 10 phases, 25 plans across 7 days
- v1.1: 8 phases, 17 plans in ~5 hours
- v1.2: 7 phases, 14 plans in ~1 day
- v1.3: 11 phases, 19 plans in 7 days

**v1.4:** 4 phases, TBD plans — 10 plans complete (Phase 39 Plans 01-04, Phase 40 Plans 01-04, Phase 41 Plans 01-02)
**Phase 43 (Gap Closure):** 1 plan complete

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

**Phase 40 Plan 02 decisions:**
- HealthFlag interface exported from HealthTab.tsx as single source of truth — Panel, Row, Table import from one location
- healthFlags Map<string, HealthFlag> keyed by memory_id for O(1) row-level badge lookup
- runHealthScan wrapped in useCallback with healthSettings dep — prevents stale closure in scheduled interval
- handleOpenConflict and handleOpenSettings use toast.info placeholders — modals deferred (out of QUAL-04/05 scope)
- Scheduled interval guards on activeTab === health AND projectId non-null

**Phase 40 Plan 03 decisions:**
- LCS word-diff splits on \s+ preserving spacing tokens for faithful original formatting
- SettingsPanel is ephemeral session-only state — no backend persistence per CONTEXT.md scope
- HealthSettings type defined in SettingsPanel.tsx, imported by MemoryPanel — single source of truth
- onArchiveMemory is optional prop on HealthTab for backward compatibility
- handleAdvanceNext sequences conflict flags only — stale flags use dismiss/archive independently

**Phase 40 Plan 04 decisions:**
- Archive uses content prefix [ARCHIVED <timestamp>] as soft-delete marker — recoverable, no backend changes needed
- items array from useMemory hook used directly (hook exposes items already unwrapped, not data?.items)
- Regression test uses stdlib dict validator not pydantic (pydantic not installed in root test env)

**Phase 41 Plan 02 decisions:**
- validateDiffText exported from action route (not shared lib) — keeps approval gate co-located with write path, preventing accidental bypass
- rerenderSoul failure logged but does not fail accept request — override content already durably written
- rejection_reason memorization deferred to L2 CLI — action route does not call memU directly (separation of concerns)
- project param always required in query string — no active_project fallback (cross-project scope safety)

**Phase 41 Plan 01 decisions:**
- Activity log (workspace-state.json) used as primary corpus; memU as supplementary — engine works even when memU is empty or down
- keyword frequency clustering (stdlib) chosen over embedding-based — no live memU dependency, works on plain text
- sys.path guard added before asyncio import to prevent orchestration/logging.py shadowing stdlib logging in Python 3.14
- suggest.py has zero imports of soul_renderer write functions — structural approval gate enforced at module boundary (ADV-06)
- Suppression fingerprint derived from md5 of keyword so rejected suggestions are matched even after evidence count changes
- [Phase 41]: SuggestionCard accepted state renders as green confirmation card (stays visible after accept for clear operator feedback)
- [Phase 41]: Sidebar reads projectId from localStorage directly (not ProjectContext) to avoid React context dependency in layout component

**Phase 42 Plan 01 decisions:**
- Tests import _filter_after from 'routers.retrieve' with docker/memory/memory_service on sys.path — not a deep package path
- PERF-08 tests patch four symbols in orchestration.snapshot (load_project_config, cleanup_old_snapshots, subprocess.run, get_snapshot_dir) — all four needed because capture_semantic_snapshot calls all of them
- PERF-06 tests assert isinstance(result, tuple) before unpacking to (items, ok) — gives clear failure message when function returns bare list

**Phase 42 Plan 02 decisions:**
- retrieve.py uses try/except ImportError guards for fastapi and relative imports — _filter_after importable in test env where only docker/memory/memory_service is on sys.path
- Naive datetime normalization: cutoff and item_dt both stripped to naive UTC before comparison — avoids TypeError on Python 3.11+ comparing TZ-aware vs TZ-naive datetimes
- empty_url returns ([], True) not ([], False) — not a network error, cursor can advance
- test_spawn_memory.py updated to unpack (list, bool) tuples — preserves test semantics after return type change

**Phase 42 Plan 03 decisions:**
- Prune block placed AFTER snapshot_path.write_text() — new snapshot counted before pruning enforces the limit (Pitfall 4 from RESEARCH.md)
- Pruning wrapped in bare except Exception — config load failures, OS errors, any unexpected errors caught and logged, never raised
- load_project_config called fresh inside try block — follows get_pool_config() pattern of reading at call time rather than caching
- PERF-08 test scaffold fixes: mock_branch_detect added as 1st subprocess mock; patch targets updated from orchestration.snapshot.* to openclaw.snapshot.*; sys.path restored for PERF-07 router imports

**Phase 43 Plan 01 decisions:**
- ORCHESTRATION_ROOT constant derived from OPENCLAW_ROOT at module scope in both route files — single source of truth for post-refactor monorepo path
- existsSync startup warn in both routes surfaces misconfiguration at server start not at request time
- asyncio.get_running_loop() used in spawn_task() (not get_event_loop()) — safe inside async context, fast-fails on miscall
- Module-level _shutdown_handler_registered flag (not closure) — accessible by patch.object in tests, reset per test
- rerenderSoul() try/catch semantics preserved — consistent with Phase 41 Plan 02 decision

**Phase 44 Plan 01 decisions:**
- Used hard exit 1 guard (not soft-warn) in Makefile dashboard target — soft-warn allows silent failure, which is the exact ADV-03 issue being fixed
- Used $$ (double dollar) in Makefile recipe for OPENCLAW_ROOT — single $ expanded by Make to empty string, defeating the guard

### Pending Todos

None.

### Blockers/Concerns

- Phase 39 Plan 01 RESOLVED: stop_timeout=30 added to spawn.py container_config.
- Phase 40: RESOLVED — PUT /api/memory/[id] proxy implemented in plan 02, used successfully in plan 03.
- Phase 41: Rejection corpus may be too small for ≥3-cluster threshold at current project scale — track cluster hit rate early and add keyword-frequency fallback if needed.

## Session Continuity

Last session: 2026-02-25
Stopped at: Completed 44-01-PLAN.md — OPENCLAW_ROOT Makefile guard + README fix + SummaryStream.tsx parse error + stale-patch audit closure (TECH-DEBT-44-A, B, C), 148/148 tests pass
Resume: Phase 44 Plan 01 complete — phase 44 done (1 plan). v1.4 milestone fully cleaned up.
