# Roadmap: OpenClaw (Grand Architect Protocol)

## Milestones

- ✅ **v1.0 Grand Architect Protocol Foundation** — Phases 1-10 (shipped 2026-02-23)
- ✅ **v1.1 Project Agnostic** — Phases 11-18 (shipped 2026-02-23)
- 🚧 **v1.2 Orchestration Hardening** — Phases 19-25 (in progress)

## Phases

<details>
<summary>✅ v1.0 Grand Architect Protocol Foundation (Phases 1-10) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Environment Substrate (2/2 plans) — completed 2026-02-17
- [x] Phase 2: Core Orchestration (2/2 plans) — completed 2026-02-17
- [x] Phase 3: Specialist Execution (4/4 plans) — completed 2026-02-18
- [x] Phase 4: Monitoring Uplink (4/4 plans) — completed 2026-02-18
- [x] Phase 5: Wiring Fixes & Initialization (3/3 plans) — completed 2026-02-23
- [x] Phase 6: Phase 3 Formal Verification (2/2 plans) — completed 2026-02-23
- [x] Phase 7: Phase 4 Formal Verification (2/3 plans, 1 skipped) — completed 2026-02-23
- [x] Phase 8: Final Gap Closure (1/1 plan) — completed 2026-02-23
- [x] Phase 9: Integration Wiring Cleanup (2/2 plans) — completed 2026-02-23
- [x] Phase 10: Housekeeping & Documentation (2/2 plans) — completed 2026-02-23

See: `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.1 Project Agnostic (Phases 11-18) — SHIPPED 2026-02-23</summary>

- [x] Phase 11: Config Decoupling Foundation (3/3 plans) — completed 2026-02-23
- [x] Phase 12: SOUL Templating (2/2 plans) — completed 2026-02-23
- [x] Phase 13: Multi-Project Runtime (2/2 plans) — completed 2026-02-23
- [x] Phase 14: Project CLI (2/2 plans) — completed 2026-02-23
- [x] Phase 15: Dashboard Project Switcher (2/2 plans) — completed 2026-02-23
- [x] Phase 16: Phase 11/12 Integration Fixes (2/2 plans) — completed 2026-02-23
- [x] Phase 17: Phase 11/12 Formal Verification (2/2 plans) — completed 2026-02-23
- [x] Phase 18: Integration Hardening (2/2 plans) — completed 2026-02-23

See: `.planning/milestones/v1.1-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.2 Orchestration Hardening (In Progress)

**Milestone Goal:** Make the orchestration layer production-grade — structured observability, state reliability, performance under concurrency, per-project pool configuration, and dashboard metrics.

- [x] **Phase 19: Structured Logging** - Establish structured JSON logging foundation across all orchestration components (completed 2026-02-24)
- [x] **Phase 20: Reliability Hardening** - State backup/recovery and config schema validation with fast-fail error reporting (completed 2026-02-24)
- [x] **Phase 21: State Engine Performance** - Docker client pooling, in-memory state caching, incremental updates, shared-lock reads (completed 2026-02-24)
- [x] **Phase 22: Observability Metrics** - Task lifecycle metrics, pool utilization tracking, and activity log rotation (completed 2026-02-24)
- [x] **Phase 23: Per-Project Pool Config** - Configurable concurrency limits, isolated/shared pool modes, queue overflow policies (completed 2026-02-24)
- [ ] **Phase 24: Dashboard Metrics** - Agent hierarchy filtering per project and usage metrics visualization panel
- [x] **Phase 25: Monitor Cache Fix** - Fix JarvisState cache reuse in multi-project monitor path (PERF-04 integration gap) (completed 2026-02-24)

## Phase Details

### Phase 19: Structured Logging
**Goal**: All orchestration components emit structured JSON logs with configurable levels, giving operators a consistent, machine-readable audit trail
**Depends on**: Phase 18
**Requirements**: OBS-01
**Success Criteria** (what must be TRUE):
  1. Every orchestration module (state_engine, spawn, monitor, snapshot, pool) emits log lines as JSON objects with timestamp, level, component, and message fields
  2. Log level is configurable at startup without code changes (env var or config)
  3. A log grep for a task ID returns structured entries from every component that touched that task
  4. Existing stdout prints and ad-hoc logging replaced — no mixed plain-text/JSON output from orchestration layer
**Plans**: 2 plans
Plans:
- [ ] 19-01-PLAN.md — Logging foundation module + state_engine instrumentation
- [ ] 19-02-PLAN.md — Instrument spawn, pool, and snapshot with structured logging

### Phase 20: Reliability Hardening
**Goal**: The system never loses state to JSON corruption and catches misconfigured projects at load time with clear, actionable errors
**Depends on**: Phase 19
**Requirements**: REL-01, REL-02, REL-03
**Success Criteria** (what must be TRUE):
  1. Truncating or corrupting workspace-state.json then restarting the state engine restores the last valid state from backup rather than reinitializing empty
  2. A project.json missing a required field (e.g. workspace) causes openclaw to exit immediately with a message identifying the missing field — not a KeyError traceback
  3. An openclaw.json with a broken reports_to chain causes startup to fail fast with the specific agent ID and constraint violated
  4. State writes always leave a recoverable backup; no write path skips the backup step
**Plans**: 2 plans
Plans:
- [ ] 20-01-PLAN.md — State backup-before-write and recovery-from-backup
- [ ] 20-02-PLAN.md — Project config schema validation and agent hierarchy validation

### Phase 21: State Engine Performance
**Goal**: Orchestration throughput improves under concurrent spawns — Docker connections reused, state reads served from memory, and file writes minimized to changed fields only
**Depends on**: Phase 20
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):
  1. Spawning three L3 containers in sequence reuses a single Docker client connection — confirmed by absence of repeated connection setup in logs
  2. Monitor polling and dashboard API reads acquire shared locks only and do not block concurrent spawn writes
  3. After updating a single task's status, the write-through cache ensures subsequent reads are served from memory without re-reading disk
  4. Cache hit rate for state reads is observable in structured logs; disk reads only occur on cache miss or detected external modification
**Plans**: 3 plans
Plans:
- [x] 21-01-PLAN.md — Docker client pooling (shared singleton with lazy init and reconnect)
- [x] 21-02-PLAN.md — State engine caching, write-through updates, and cached shared-lock reads
- [x] 21-03-PLAN.md — Gap closure: align PERF-03 requirement text with write-through implementation

### Phase 22: Observability Metrics
**Goal**: Operators can see how long tasks take, how saturated each project's pool is, and the activity log stays bounded in size
**Depends on**: Phase 21
**Requirements**: OBS-02, OBS-03, OBS-04
**Success Criteria** (what must be TRUE):
  1. After a task completes, its spawn-to-complete duration, lock wait time, and retry count are retrievable from structured logs or state
  2. Pool utilization for a project (active containers, queued tasks, completed count, semaphore saturation) is queryable via the monitor CLI
  3. When the activity log exceeds its configured threshold, old entries are archived and the active log is trimmed — the log file does not grow unbounded
  4. Pool saturation events (all slots occupied, task queued) appear as structured log entries with project and task context
**Plans**: 2 plans
Plans:
- [ ] 22-01-PLAN.md — Task lifecycle metrics (timestamps, lock wait, retry count) and activity log rotation
- [ ] 22-02-PLAN.md — Pool utilization tracking (CLI subcommand, saturation event logging)

### Phase 23: Per-Project Pool Config
**Goal**: Each project can declare its own concurrency limit, pool isolation mode, and overflow behavior in project.json — no code changes required to adjust
**Depends on**: Phase 22
**Requirements**: POOL-01, POOL-02, POOL-03
**Success Criteria** (what must be TRUE):
  1. Setting l3_overrides.max_concurrent = 1 in a project's project.json limits that project to one active L3 container at a time, regardless of global pool size
  2. A project configured for isolated pool mode runs containers exclusively against its own pool; shared-mode projects share the global semaphore
  3. A project configured with overflow policy "reject" returns an immediate error when the queue is full; "wait" queues the task; "priority" elevates it above standard-priority queued tasks
  4. Changing pool config in project.json takes effect on next spawn without restarting the orchestration layer
**Plans**: 2 plans
Plans:
- [ ] 23-01-PLAN.md — Pool config loader, validation, and config-driven PoolRegistry with hot-reload
- [ ] 23-02-PLAN.md — Pool isolation modes (shared/isolated), overflow policies (reject/wait/priority), monitor update

### Phase 24: Dashboard Metrics
**Goal**: The occc dashboard shows which agents belong to the selected project and surfaces task performance and pool utilization as visual metrics
**Depends on**: Phase 23
**Requirements**: DSH-09, DSH-10
**Success Criteria** (what must be TRUE):
  1. Switching projects in the dashboard updates the agent hierarchy view to show only L2/L3 agents associated with that project — global agents remain visible
  2. The usage metrics panel displays task completion times (last N tasks), pool utilization percentage, and container lifecycle counts for the selected project
  3. The metrics panel updates without a page reload when task state changes (SWR polling or SSE)
  4. An empty-state is shown (not a broken chart) when a project has no completed tasks yet
**Plans**: 2 plans
Plans:
- [ ] 24-01-PLAN.md — Metrics API route, recharts visualizations (bar chart, gauge, stat cards), /metrics page
- [ ] 24-02-PLAN.md — Agent hierarchy global/project split with status indicator dots

### Phase 25: Monitor Cache Fix
**Goal**: Multi-project monitor tail reuses JarvisState across poll cycles so the in-memory cache provides hits instead of cold-starting every iteration
**Depends on**: Phase 21
**Requirements**: PERF-04 (integration gap closure)
**Gap Closure:** Closes integration gap and broken flow from v1.2 audit
**Success Criteria** (what must be TRUE):
  1. `monitor.py` `tail_state()` multi-project path creates JarvisState once per project outside the poll loop and reuses it across iterations
  2. Cache hit rate in structured logs shows hits (not only misses) during multi-project monitor tail polling
  3. `show_status()` and `show_task()` multi-project paths also reuse JarvisState instances where practical (lower priority — one-shot calls)
**Plans**: 1 plan
Plans:
- [ ] 25-01-PLAN.md — Hoist JarvisState instances out of poll loops, add structured logger, document one-shot paths

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Environment Substrate | v1.0 | 2/2 | ✓ Complete | 2026-02-17 |
| 2. Core Orchestration | v1.0 | 2/2 | ✓ Complete | 2026-02-17 |
| 3. Specialist Execution | v1.0 | 4/4 | ✓ Complete | 2026-02-18 |
| 4. Monitoring Uplink | v1.0 | 4/4 | ✓ Complete | 2026-02-18 |
| 5. Wiring Fixes | v1.0 | 3/3 | ✓ Complete | 2026-02-23 |
| 6. Phase 3 Verification | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 7. Phase 4 Verification | v1.0 | 2/3 | ✓ Complete | 2026-02-23 |
| 8. Final Gap Closure | v1.0 | 1/1 | ✓ Complete | 2026-02-23 |
| 9. Integration Wiring | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 10. Housekeeping & Docs | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 11. Config Decoupling Foundation | v1.1 | 3/3 | ✓ Complete | 2026-02-23 |
| 12. SOUL Templating | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 13. Multi-Project Runtime | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 14. Project CLI | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 15. Dashboard Project Switcher | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 16. Phase 11/12 Integration Fixes | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 17. Phase 11/12 Formal Verification | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 18. Integration Hardening | v1.1 | 2/2 | ✓ Complete | 2026-02-23 |
| 19. Structured Logging | 2/2 | Complete    | 2026-02-24 | - |
| 20. Reliability Hardening | 2/2 | Complete    | 2026-02-24 | - |
| 21. State Engine Performance | 3/3 | Complete    | 2026-02-24 | - |
| 22. Observability Metrics | 2/2 | Complete    | 2026-02-24 | - |
| 23. Per-Project Pool Config | 2/2 | Complete    | 2026-02-24 | - |
| 24. Dashboard Metrics | 1/2 | In Progress|  | - |
| 25. Monitor Cache Fix | 1/1 | Complete    | 2026-02-24 | - |
