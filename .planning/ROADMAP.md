# Roadmap: OpenClaw (Grand Architect Protocol)

## Milestones

- ✅ **v1.0 Grand Architect Protocol Foundation** — Phases 1-10 (shipped 2026-02-23)
- ✅ **v1.1 Project Agnostic** — Phases 11-18 (shipped 2026-02-23)
- ✅ **v1.2 Orchestration Hardening** — Phases 19-25 (shipped 2026-02-24)
- ✅ **v1.3 Agent Memory** — Phases 26-38 (shipped 2026-02-24)
- 🚧 **v1.4 Operational Maturity** — Phases 39-42 (in progress)

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

<details>
<summary>✅ v1.2 Orchestration Hardening (Phases 19-25) — SHIPPED 2026-02-24</summary>

- [x] Phase 19: Structured Logging (2/2 plans) — completed 2026-02-24
- [x] Phase 20: Reliability Hardening (2/2 plans) — completed 2026-02-24
- [x] Phase 21: State Engine Performance (3/3 plans) — completed 2026-02-24
- [x] Phase 22: Observability Metrics (2/2 plans) — completed 2026-02-24
- [x] Phase 23: Per-Project Pool Config (2/2 plans) — completed 2026-02-24
- [x] Phase 24: Dashboard Metrics (2/2 plans) — completed 2026-02-24
- [x] Phase 25: Monitor Cache Fix (1/1 plan) — completed 2026-02-24

See: `.planning/milestones/v1.2-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.3 Agent Memory (Phases 26-38) — SHIPPED 2026-02-24</summary>

- [x] Phase 26: memU Infrastructure (2/2 plans) — completed 2026-02-24
- [x] Phase 27: Memory Client + Scoping (1/1 plan) — completed 2026-02-24
- [x] Phase 28: L3 Auto-Memorization (2/2 plans) — completed 2026-02-24
- [x] Phase 29: Pre-Spawn Retrieval + SOUL Injection (2/2 plans) — completed 2026-02-24
- [x] Phase 30: L2 Review Decision Memorization (2/2 plans) — completed 2026-02-24
- [x] Phase 33: Integration Gap Closure (2/2 plans) — completed 2026-02-24
- [x] Phase 34: Review Decision Category Fix (1/1 plan) — completed 2026-02-24
- [x] Phase 35: L3 In-Execution Memory Queries (1/1 plan) — completed 2026-02-24
- [x] Phase 36: Dashboard Memory Panel (3/3 plans) — completed 2026-02-24
- [x] Phase 37: Category Field E2E Fix (2/2 plans) — completed 2026-02-24
- [x] Phase 38: Phase 28 Verification + Cleanup (1/1 plan) — completed 2026-02-24

Phases 31 and 32 were superseded by Phases 35 and 36 respectively.

See: `.planning/milestones/v1.3-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.4 Operational Maturity (In Progress)

**Milestone Goal:** Harden the swarm for production-grade autonomy — graceful shutdown with task recovery, memory health monitoring, L1 proactive SOUL suggestions, and delta-based snapshot optimization.

- [x] **Phase 39: Graceful Sentinel** - SIGTERM handling, task dehydration, interrupted task recovery loop, and fire-and-forget drain on shutdown (completed 2026-02-24)
- [x] **Phase 40: Memory Health Monitor** - Batch staleness and conflict detection with dashboard review UI and memory edit endpoint (completed 2026-02-24)
- [x] **Phase 41: L1 Strategic Suggestions** - Pattern extraction engine producing reviewable SOUL amendments with mandatory human approval gate (completed 2026-02-24)
- [ ] **Phase 42: Delta Snapshots** - Cursor-based memory retrieval and configurable snapshot pruning to reduce I/O at scale

## Phase Details

### Phase 39: Graceful Sentinel
**Goal**: L3 containers and pool shut down cleanly on SIGTERM — interrupted tasks are recorded in Jarvis state and automatically recovered on restart
**Depends on**: Phase 38 (v1.3 complete)
**Requirements**: REL-04, REL-05, REL-06, REL-07, REL-08
**Success Criteria** (what must be TRUE):
  1. Running `docker stop` on an L3 container produces exit code 143 (not 137), and the task state in workspace-state.json transitions to `interrupted` before the container exits
  2. Pool startup scans workspace-state.json for tasks stuck in `in_progress`, `interrupted`, or `starting` beyond the skill timeout and applies the configured recovery policy without manual intervention
  3. Recovery policy (`mark_failed` / `auto_retry` / `manual`) is settable per project in `l3_overrides.recovery_policy` in project.json and takes effect on the next pool startup
  4. Fire-and-forget memorize tasks in flight at shutdown are drained via `asyncio.gather` before the event loop stops — no pending task silently discarded
**Plans:** 4/4 plans complete

Plans:
- [x] 39-01-PLAN.md — Entrypoint SIGTERM trap + spawn stop_timeout (REL-04, REL-05)
- [x] 39-02-PLAN.md — Pool shutdown drain for fire-and-forget memorize tasks (REL-08)
- [x] 39-03-PLAN.md — Recovery scan at startup + recovery_policy config (REL-06, REL-07)
- [ ] 39-04-PLAN.md — Gap closure: wire run_recovery_scan() into spawn_task() startup path (REL-06)

### Phase 40: Memory Health Monitor
**Goal**: Operators can detect and resolve stale and conflicting memories through a health scan and dashboard review UI
**Depends on**: Phase 39
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-06
**Success Criteria** (what must be TRUE):
  1. Triggering a health scan returns a scored list of flagged memories annotated with flag type (`stale` or `conflict`), similarity score where applicable, and a recommended action
  2. The `/memory` dashboard page shows health badges on flagged memories — stale and conflict indicators are visible at a glance without navigating away
  3. Clicking a conflict badge opens a side panel showing both conflicting memories, their similarity score, and three actions: edit, delete, or dismiss flag
  4. A `PUT /memories/:id` endpoint in the memory service accepts updated content and persists the change without creating a duplicate record
**Plans:** 4/4 plans complete

Plans:
- [ ] 40-01-PLAN.md — Health scan engine + PUT endpoint in memory service (QUAL-01, QUAL-02, QUAL-03, QUAL-04)
- [ ] 40-02-PLAN.md — Next.js proxy routes + health badges + Health tab + scan trigger (QUAL-04, QUAL-05)
- [ ] 40-03-PLAN.md — Conflict resolution side panel + settings panel + auto-advance (QUAL-06)

### Phase 41: L1 Strategic Suggestions
**Goal**: L1 can identify recurring failure patterns in task history and produce reviewable SOUL amendments that an operator must explicitly approve before any SOUL file is modified
**Depends on**: Phase 40
**Requirements**: ADV-01, ADV-02, ADV-03, ADV-04, ADV-05, ADV-06
**Success Criteria** (what must be TRUE):
  1. Running pattern extraction produces no SOUL mutations — suggestions are written only to `soul-suggestions.json` in the project state directory and the soul-override.md file is unchanged until an operator explicitly accepts
  2. A suggestion contains a pattern description, evidence count, and exact diff-style text proposed for soul-override.md — sufficient for an operator to evaluate without reading raw task logs
  3. The dashboard surfaces pending suggestions with accept and reject actions; accepting appends the suggestion to soul-override.md and re-renders the SOUL; rejecting memorizes the rejection reason
  4. Suggestions are only generated when ≥3 similar rejections are found within the lookback window — the engine produces no output on insufficient data rather than generating noise
  5. The suggestion apply API route validates the diff before writing (rejects payloads containing safety constraint removal, shell commands, or exceeding 100 lines) — structural injection is prevented at the API layer
**Plans:** 3/3 plans complete

Plans:
- [ ] 41-01-PLAN.md — Pattern extraction engine + soul-suggestions.json schema + unit tests (ADV-01, ADV-02, ADV-03)
- [ ] 41-02-PLAN.md — Next.js API routes: GET/POST suggestions + accept/reject action with approval gate validation (ADV-04, ADV-06)
- [ ] 41-03-PLAN.md — Suggestions dashboard page + SuggestionCard + DismissedTab + Sidebar badge (ADV-05)

### Phase 42: Delta Snapshots
**Goal**: Pre-spawn memory retrieval fetches only new memories since the last retrieval, and snapshot history is bounded by a configurable limit per project
**Depends on**: Phase 39
**Requirements**: PERF-05, PERF-06, PERF-07, PERF-08
**Success Criteria** (what must be TRUE):
  1. After a task completes, `memory_cursors` in workspace-state.json is updated with the ISO timestamp of the retrieval — visible in the raw state file
  2. A project that has run multiple tasks shows measurably fewer memories fetched on subsequent pre-spawn retrievals compared to the first (cursor filters out already-seen memories)
  3. The memU `/retrieve` endpoint accepts a `created_after` ISO timestamp parameter and returns only memories created after that timestamp
  4. Projects with `max_snapshots` configured in project.json automatically prune the oldest snapshots when the limit is exceeded — snapshot directory never grows beyond the configured count
**Plans:** 1/3 plans executed

Plans:
- [ ] 42-01-PLAN.md — Test scaffold: 13 tests covering PERF-05 through PERF-08 (RED state)
- [ ] 42-02-PLAN.md — Cursor feature: JarvisState helpers + cursor-aware spawn retrieval + memU created_after filter (PERF-05, PERF-06, PERF-07)
- [ ] 42-03-PLAN.md — Snapshot pruning: wire cleanup_old_snapshots into capture_semantic_snapshot (PERF-08)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-10 | v1.0 | 25/25 | ✓ Complete | 2026-02-23 |
| 11-18 | v1.1 | 17/17 | ✓ Complete | 2026-02-23 |
| 19-25 | v1.2 | 14/14 | ✓ Complete | 2026-02-24 |
| 26-38 | v1.3 | 19/19 | ✓ Complete | 2026-02-24 |
| 39. Graceful Sentinel | 4/4 | Complete    | 2026-02-24 | - |
| 40. Memory Health Monitor | 4/4 | Complete    | 2026-02-24 | - |
| 41. L1 Strategic Suggestions | 3/3 | Complete    | 2026-02-24 | - |
| 42. Delta Snapshots | 1/3 | In Progress|  | - |
