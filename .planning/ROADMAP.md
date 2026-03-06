# Roadmap: OpenClaw Agent Orchestration

## Milestones

- ✅ **v1.0 Grand Architect Protocol Foundation** — Phases 1-10 (shipped 2026-02-23)
- ✅ **v1.1 Project Agnostic** — Phases 11-18 (shipped 2026-02-23)
- ✅ **v1.2 Orchestration Hardening** — Phases 19-25 (shipped 2026-02-24)
- ✅ **v1.3 Agent Memory** — Phases 26-38 (shipped 2026-02-24)
- ✅ **v1.4 Operational Maturity** — Phases 39-44 (shipped 2026-02-25)
- ✅ **v1.5 Config Consolidation** — Phases 45-53 (shipped 2026-02-25)
- ✅ **v1.6 Agent Autonomy** — Phases 54-60 (shipped 2026-02-26)
- ✅ **v2.0 Structural Intelligence** — Phases 61-67 (shipped 2026-03-04)
- 🚧 **v2.1 Programmatic Integration & Real-Time Streaming** — Phases 68-77 (in progress)

---

<details>
<summary>✅ v1.0–v1.6 (Phases 1-60) — SHIPPED</summary>

60 phases shipped across 6 milestones. See MILESTONES.md for full retrospective.

</details>

<details>
<summary>✅ v2.0 Structural Intelligence (Phases 61-67) — SHIPPED 2026-03-04</summary>

- [x] Phase 61: Topology Foundation (2/2 plans) — completed 2026-03-04
- [x] Phase 62: Structure Proposal Engine (5/5 plans) — completed 2026-03-03
- [x] Phase 63: Correction System and Approval Gate (3/3 plans) — completed 2026-03-03
- [x] Phase 64: Structural Memory (2/2 plans) — completed 2026-03-04
- [x] Phase 65: Topology Observability (3/3 plans) — completed 2026-03-04
- [x] Phase 66: Wire Rubric Scores to Confidence Chart (1/1 plan) — completed 2026-03-04
- [x] Phase 67: Integration Cleanup (1/1 plan) — completed 2026-03-04

</details>

---

### 🚧 v2.1 Programmatic Integration & Real-Time Streaming (In Progress)

**Milestone Goal:** Replace CLI-level coupling with programmatic APIs, activate existing event infrastructure, and deliver live L3 output streaming to the dashboard.

## Phases

- [x] **Phase 68: Tech Debt Resolution** - Resolve test failures, consolidate TopologyProposal, remove hardcoded paths (completed 2026-03-04)
- [x] **Phase 69: Docker Base Image** - Create shared openclaw-base image and rebase L3 Dockerfile (completed 2026-03-04)
- [x] **Phase 70: Event Bridge Activation** - Start Unix socket server, wire event bus to transport (completed 2026-03-04)
- [x] **Phase 71: L3 Output Streaming** - Stream Docker container output through event bridge to dashboard SSE (completed 2026-03-04)
- [x] **Phase 72: Gateway-Only Dispatch** - Remove execFileSync fallback, add bootstrap mode, gateway health check at startup (completed 2026-03-04)
- [x] **Phase 73: Unified Agent Registry** - Merge agent configs, auto-discovery, config drift detection (completed 2026-03-04)
- [x] **Phase 74: Dashboard Streaming UI** - Terminal-style live output panel with task board integration (completed 2026-03-05)
- [x] **Phase 75: Unified Observability** - Consolidated metrics endpoint and pipeline timeline view (completed 2026-03-05)
- [x] **Phase 76: SOUL Injection Verification** - Verify dynamic variables and topology context populated at spawn time (completed 2026-03-06)
- [ ] **Phase 77: Integration E2E Verification** - End-to-end verification of full pipeline

## Phase Details

### Phase 68: Tech Debt Resolution
**Goal**: The codebase is clean enough to build on — all tests pass, models are consolidated, no developer-specific paths
**Depends on**: Phase 67 (v2.0 complete)
**Requirements**: DEBT-01, DEBT-02, DEBT-03
**Success Criteria** (what must be TRUE):
  1. `uv run pytest packages/orchestration/tests/` completes with zero failures including test_proposer.py and test_state_engine_memory.py
  2. A single TopologyProposal class exists in proposal_models.py with graph field, rubric_score, and to_dict/from_dict — proposer.py imports and uses it directly
  3. Running `grep -r "~/\|~/" .` on tracked files returns no results
  4. All runtime configs and SOUL templates reference OPENCLAW_ROOT or environment variables rather than absolute user paths
**Plans:** 2/2 plans complete
Plans:
- [x] 68-01-PLAN.md — Consolidate TopologyProposal and fix test failures (DEBT-01, DEBT-02) [COMPLETE: 694 tests pass]
- [ ] 68-02-PLAN.md — Remove hardcoded user paths from all tracked files (DEBT-03)

### Phase 69: Docker Base Image
**Goal**: A shared openclaw-base image exists and L3 containers use it, reducing Dockerfile duplication and standardizing the base layer
**Depends on**: Phase 68
**Requirements**: DOCK-01
**Success Criteria** (what must be TRUE):
  1. `docker build -t openclaw-base:bookworm-slim docker/base/` succeeds
  2. L3 Dockerfile uses `FROM openclaw-base:bookworm-slim` instead of a raw debian/ubuntu base
  3. `make docker-l3` builds successfully using the shared base image
**Plans**: 1 plan
Plans:
- [ ] 69-01-PLAN.md — Create openclaw-base image and rebase L3 Dockerfile (DOCK-01)

### Phase 70: Event Bridge Activation
**Goal**: The event bridge Unix socket server starts automatically and all published events flow through it to connected clients
**Depends on**: Phase 68
**Requirements**: EVNT-01, EVNT-02
**Success Criteria** (what must be TRUE):
  1. Starting the orchestration layer starts the Unix socket server — no manual step required
  2. A test client connecting to the Unix socket receives events published via the event bus within 100ms
  3. All 17 event types published to the event bus are forwarded to connected socket clients without filtering or loss
  4. Socket server handles client disconnect gracefully without crashing the orchestration process
**Plans**: 1 plan
Plans:
- [x] 70-01-PLAN.md — Wire event_bus to socket transport, migrate publishers, auto-start server (EVNT-01, EVNT-02)

### Phase 71: L3 Output Streaming
**Goal**: L3 container stdout/stderr flows in real-time from pool.py through the event bridge and appears in the dashboard SSE stream
**Depends on**: Phase 70
**Requirements**: EVNT-03, EVNT-04
**Success Criteria** (what must be TRUE):
  1. While an L3 container is running, its stdout appears in the dashboard SSE stream within 2 seconds of being written
  2. Each output line is tagged with the task ID so the dashboard can route to the correct terminal panel
  3. The SSE endpoint sends heartbeat pings every 30 seconds — browser devtools shows the keepalive traffic
  4. After a network interruption, the dashboard SSE client reconnects automatically and receives the last 100 buffered events for the task without manual refresh
**Plans:** 2/2 plans complete
Plans:
- [ ] 71-01-PLAN.md — Add TASK_OUTPUT event type, wire pool.py emission, socket heartbeat (EVNT-03)
- [ ] 71-02-PLAN.md — SSE heartbeat, TypeScript types, LogViewer event bridge consumer (EVNT-04)

### Phase 72: Gateway-Only Dispatch
**Goal**: All directive routing goes through the gateway HTTP API — no CLI subprocess fallback exists — and the system can start without a gateway for setup tasks
**Depends on**: Phase 68
**Requirements**: GATE-01, GATE-02, GATE-03
**Success Criteria** (what must be TRUE):
  1. Removing the gateway while the router is running causes dispatch to fail with a clear error — not silently fall back to execFileSync
  2. `grep -r "execFileSync" skills/router/` returns no results
  3. Running `openclaw monitor status` with `OPENCLAW_BOOTSTRAP=1` succeeds even when the gateway process is not running
  4. Starting the orchestration layer without bootstrap mode and without a gateway running produces a fatal startup error with a human-readable message
**Plans:** 1/1 plans complete
Plans:
- [ ] 72-01-PLAN.md — Remove execFileSync fallback, add bootstrap mode and gateway health check (GATE-01, GATE-02, GATE-03)

### Phase 73: Unified Agent Registry
**Goal**: Agent configuration has one source of truth — per-agent config.json files — with auto-discovery at startup and drift warnings when central config diverges
**Depends on**: Phase 68
**Requirements**: AREG-01, AREG-02, AREG-03
**Success Criteria** (what must be TRUE):
  1. Adding a new agent directory under agents/ with a config.json causes it to appear in the registry at next startup without editing openclaw.json
  2. `openclaw agent list` shows agents discovered from the filesystem, not only those in openclaw.json
  3. A mismatch between openclaw.json agents.list and agents/*/agent/config.json produces a startup warning that names the conflicting fields
  4. Removing an agent directory removes it from the registry on next startup
**Plans**: 2 plans
Plans:
- [ ] 73-01-PLAN.md — Add drift detection, defaults inheritance, startup wiring to AgentRegistry (AREG-01, AREG-02, AREG-03)
- [ ] 73-02-PLAN.md — Create `openclaw agent list` CLI command with table and JSON output (AREG-02, AREG-03)

### Phase 74: Dashboard Streaming UI
**Goal**: Users can open any active task on the task board and watch its L3 output stream live in a terminal-style panel
**Depends on**: Phase 71
**Requirements**: DASH-01, DASH-02, DASH-03
**Success Criteria** (what must be TRUE):
  1. The task board shows a live output pane alongside or beneath the task list — not a separate navigation step
  2. Clicking a task row opens its output stream in the terminal panel within 500ms
  3. Output auto-scrolls to the bottom as new lines arrive; scrolling up pauses auto-scroll with a visual indicator
  4. Scrolling back to the bottom resumes auto-scroll automatically without clicking a button
**Plans**: 1 plan
Plans:
- [ ] 74-01-PLAN.md — Terminal-style live output panel with task board integration (DASH-01, DASH-02, DASH-03)

### Phase 75: Unified Observability
**Goal**: A single metrics endpoint consolidates all system metrics and the dashboard shows a pipeline timeline from L1 dispatch through L3 completion
**Depends on**: Phase 71
**Requirements**: OBSV-01, OBSV-02
**Success Criteria** (what must be TRUE):
  1. `GET /api/metrics` returns a JSON response containing both orchestration metrics (from Python) and dashboard-computed metrics in a single payload
  2. The dashboard metrics page shows a timeline row per task with labeled segments: L1 dispatch, L2 decomposition, L3 execution — each with a timestamp and duration
  3. Timestamps and durations in the timeline are accurate to within 1 second of actual event times
**Plans:** 2/2 plans complete
Plans:
- [ ] 75-01-PLAN.md — Python snapshot writer + /api/metrics unified response (OBSV-01)
- [ ] 75-02-PLAN.md — Pipeline timeline UI: PipelineStrip, TaskPulse expand, Metrics page section (OBSV-02)

### Phase 76: SOUL Injection Verification
**Goal**: Every L3 container spawned has its SOUL variables fully populated including active task count, pool utilization, and current topology context
**Depends on**: Phase 73
**Requirements**: OBSV-03
**Success Criteria** (what must be TRUE):
  1. Spawning an L3 container and inspecting its SOUL file shows non-empty values for active_task_count, pool_utilization, and topology_context
  2. Spawning two concurrent L3 tasks shows different active_task_count values in their respective SOUL files
  3. After proposing a topology, spawned L3 containers have the current topology archetype name and agent count in their SOUL context
**Plans**: 1 plan
Plans:
- [x] 76-01-PLAN.md — Verify SOUL dynamic variables populated at spawn time (OBSV-03) [COMPLETE: 773 tests pass]

### Phase 77: Integration E2E Verification
**Goal**: The full pipeline works end-to-end — L1 dispatches through the gateway, L2 decomposes, L3 spawns with populated SOUL, output streams to the dashboard, events flow, and metrics update
**Depends on**: Phase 74, Phase 75, Phase 76
**Requirements**: INTG-01
**Success Criteria** (what must be TRUE):
  1. Issuing a directive at L1 results in a visible L3 task appearing in the dashboard task board within 5 seconds
  2. The L3 task's live output stream appears in the terminal panel while the container is running
  3. After L3 completes, the metrics endpoint reflects the completed task count and the pipeline timeline shows the full L1→L2→L3 duration
  4. The event stream shows no gaps — all expected event types (dispatch, spawn, output, complete) appear in correct order
**Plans**: 1 plan
Plans:
- [ ] 77-01-PLAN.md — End-to-end integration verification (INTG-01)

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-10 | v1.0 | 25/25 | Complete | 2026-02-23 |
| 11-18 | v1.1 | 17/17 | Complete | 2026-02-23 |
| 19-25 | v1.2 | 14/14 | Complete | 2026-02-24 |
| 26-38 | v1.3 | 19/19 | Complete | 2026-02-24 |
| 39-44 | v1.4 | 16/16 | Complete | 2026-02-25 |
| 45-53 | v1.5 | 22/22 | Complete | 2026-02-25 |
| 54-60 | v1.6 | 14/14 | Complete | 2026-02-26 |
| 61-67 | v2.0 | 17/17 | Complete | 2026-03-04 |
| 68. Tech Debt Resolution | 2/2 | Complete    | 2026-03-04 | - |
| 69. Docker Base Image | 1/1 | Complete    | 2026-03-04 | - |
| 70. Event Bridge Activation | v2.1 | Complete    | 2026-03-04 | 2026-03-04 |
| 71. L3 Output Streaming | 2/2 | Complete    | 2026-03-04 | - |
| 72. Gateway-Only Dispatch | 1/1 | Complete    | 2026-03-04 | - |
| 73. Unified Agent Registry | 2/2 | Complete    | 2026-03-04 | - |
| 74. Dashboard Streaming UI | 1/1 | Complete   | 2026-03-05 | - |
| 75. Unified Observability | 2/2 | Complete   | 2026-03-05 | - |
| 76. SOUL Injection Verification | v2.1 | 1/1 | Complete | 2026-03-06 |
| 77. Integration E2E Verification | v2.1 | 0/1 | Planned | - |

---
*Roadmap created: 2026-02-17*
*Last updated: 2026-03-06 — Phases 76-77 planned (76-01-PLAN.md, 77-01-PLAN.md)*
