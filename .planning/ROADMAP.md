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
- 🔄 **v2.1 Programmatic Integration & Real-Time Streaming** — Phases 68-82 (gap closure in progress)

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

### 🔄 v2.1 Programmatic Integration & Real-Time Streaming (Tech Debt Closure In Progress)

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
- [x] **Phase 77: Integration E2E Verification** - End-to-end verification of full pipeline (completed 2026-03-06)
- [x] **Phase 78: Verification Documentation Closure** - Write missing VERIFICATION.md files for phases 74, 76, 77 (automated portion) (completed 2026-03-06)
- [x] **Phase 79: INTG-01 Live E2E Execution** - Execute 4 deferred live INTG-01 success criteria with full system running (completed 2026-03-07)
- [x] **Phase 80: Nyquist Compliance + Tech Debt Cleanup** - Write missing VALIDATION.md for phases 69-73, 76-77; remove dead code; fix cosmetic issues (completed 2026-03-08)
- [x] **Phase 81: Alert & Metrics Accuracy** - Fix autonomy alert project_id scoping (GAP-03) and metrics.py hardcoded max_concurrent (GAP-04) (completed 2026-03-08)
- [x] **Phase 82: Nyquist v2.1 Completion** - Run /gsd:validate-phase for phases 74, 75, 78, 79, 80 to flip nyquist_compliant: true (completed 2026-03-08)

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
- [x] 77-01-PLAN.md — End-to-end integration verification (INTG-01) [COMPLETE: 779 tests pass]

### Phase 78: Verification Documentation Closure
**Goal**: All phases with missing VERIFICATION.md files have them written and requirements_completed frontmatter is correct — closing the 3-source documentation gate for OBSV-03 and the automated portion of INTG-01
**Depends on**: Phase 77
**Requirements**: OBSV-03, INTG-01 (automated criteria), DASH-01, DASH-02, DASH-03
**Gap Closure**: Closes documentation gaps identified in v2.1 audit
**Success Criteria** (what must be TRUE):
  1. Phase 74 VERIFICATION.md exists and documents DASH-01, DASH-02, DASH-03 as verified
  2. Phase 76 VERIFICATION.md exists and all 3 OBSV-03 success criteria are marked passed
  3. Phase 76 SUMMARY.md requirements_completed frontmatter includes OBSV-03
  4. Phase 77 VERIFICATION.md exists and documents the 6 passing automated integration tests
  5. Phase 77 SUMMARY.md requirements_completed frontmatter includes INTG-01
**Plans**: 2 plans
Plans:
- [x] 78-01-PLAN.md — Write VERIFICATION.md for phases 74, 76, 77; fix requirements_completed frontmatter (OBSV-03, INTG-01, DASH-01/02/03)
- [ ] 78-02-PLAN.md — Fix wrong artifact paths in 74-VERIFICATION.md (mission-control → tasks) (DASH-01, DASH-02, DASH-03)

### Phase 79: INTG-01 Live E2E Execution
**Goal**: The 4 INTG-01 live system success criteria (deferred to 77-E2E-CHECKLIST.md) are executed with a running system and documented in a formal VERIFICATION.md update
**Depends on**: Phase 78
**Requirements**: INTG-01
**Gap Closure**: Closes live criteria gap identified in v2.1 audit
**Success Criteria** (what must be TRUE):
  1. Docker + gateway + dashboard are all running simultaneously
  2. All 4 items in 77-E2E-CHECKLIST.md are executed and pass: task appears in task board, live output streams, metrics update after completion, event order is correct
  3. Phase 77 VERIFICATION.md updated with live results and INTG-01 marked fully satisfied
**Plans**: 5 plans (3 original + 2 gap closure)
Plans:
- [x] 79-01-PLAN.md — Service health gates: Docker, memU, gateway, dashboard, Docker images, project config (INTG-01) [COMPLETE: all 6 gates passed]
- [x] 79-02-PLAN.md — Live criterion execution: 4 INTG-01 criteria + DASH-01/DASH-03 via Playwright MCP (INTG-01) [COMPLETE: blocked — event bridge offline; see 79-04/79-05 gap closure]
- [x] 79-03-PLAN.md — VERIFICATION.md updates: 77-VERIFICATION.md (10/10) and 74-VERIFICATION.md (3/3) (INTG-01) [COMPLETE: documented blocked state]
- [x] 79-04-PLAN.md — Gap closure: commit useEvents.ts fix, correct ROADMAP, start event bridge (INTG-01) [COMPLETE: useEvents.ts fixed, event bridge healthy]
- [x] 79-05-PLAN.md — Gap closure: live criterion execution retry + VERIFICATION.md updates (INTG-01) [COMPLETE: all 4 INTG-01 criteria + DASH-01/DASH-03 verified 2026-03-07]
- [x] 79-06-PLAN.md — Gap closure: C1 SSE real-time latency, C3 metrics data, DASH-03 scroll indicator (INTG-01) [COMPLETE: all 3 gaps closed, score 9/9, LogViewer.tsx /api/events fix applied 2026-03-08]

### Phase 80: Nyquist Compliance + Tech Debt Cleanup
**Goal**: All v2.1 phases have VALIDATION.md files, dead code is removed, and low-severity cosmetic issues are fixed
**Depends on**: Phase 79
**Requirements**: (no new requirements — closes tech debt)
**Gap Closure**: Closes nyquist and tech debt gaps identified in v2.1 audit
**Success Criteria** (what must be TRUE):
  1. VALIDATION.md exists for phases 69, 70, 71, 72, 73, 76, 77 with nyquist_compliant: true
  2. collect_metrics() in metrics.py is removed (dead code with no callers in production path)
  3. environment/page.tsx socket path display label matches the actual socket path used in route.ts
**Plans**: 1 plan
Plans:
- [ ] 80-01-PLAN.md — Write VALIDATION.md for phases 69-73, 76-77; remove dead code; verify socket label (tech debt)

### Phase 81: Alert & Metrics Accuracy
**Goal**: Autonomy escalation alerts are visible in the per-project alert feed and the metrics endpoint reports the correct per-project `max_concurrent` value
**Depends on**: Phase 80
**Requirements**: (no new requirements — closes integration gaps GAP-03, GAP-04)
**Gap Closure**: Closes GAP-03 and GAP-04 from v2.1 audit integration checker
**Success Criteria** (what must be TRUE):
  1. `AutonomyEventBus` includes a real `project_id` in emitted events — `autonomy.escalation` and `autonomy.state_changed` events are no longer silently dropped by `useAlerts.ts`
  2. Triggering an autonomy state change causes an alert to appear in the dashboard per-project alert feed
  3. `GET /api/metrics` returns `max_concurrent` matching the project's `l3_overrides.max_concurrent` config (or global default when not overridden) — not always `3`
**Plans**: 1 plan
Plans:
- [ ] 81-01-PLAN.md — Fix AutonomyEventBus project_id scoping and metrics.py max_concurrent config read (GAP-03, GAP-04)

### Phase 82: Nyquist v2.1 Completion
**Goal**: All v2.1 phases have nyquist_compliant: true in their VALIDATION.md — the milestone is fully Nyquist-attested
**Depends on**: Phase 81
**Requirements**: (no new requirements — closes Nyquist gaps from v2.1 audit)
**Gap Closure**: Closes partial/missing VALIDATION.md for phases 74, 75, 78, 79, 80
**Success Criteria** (what must be TRUE):
  1. Phase 74 VALIDATION.md exists with `nyquist_compliant: true`
  2. Phase 75 VALIDATION.md exists with `nyquist_compliant: true`
  3. Phase 78 VALIDATION.md exists with `nyquist_compliant: true`
  4. Phase 79 VALIDATION.md exists with `nyquist_compliant: true`
  5. Phase 80 VALIDATION.md exists with `nyquist_compliant: true`
**Plans**: 1 plan
Plans:
- [ ] 82-01-PLAN.md — Write retroactive attestation VALIDATION.md for phases 74, 75, 78, 79, 80 + update milestone audit

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
| 77. Integration E2E Verification | v2.1 | 1/1 | Complete | 2026-03-06 |
| 78. Verification Documentation Closure | 2/2 | Complete    | 2026-03-06 | - |
| 79. INTG-01 Live E2E Execution | 6/6 | Complete    | 2026-03-07 | - |
| 80. Nyquist Compliance + Tech Debt Cleanup | 1/1 | Complete    | 2026-03-08 | - |
| 81. Alert & Metrics Accuracy | 1/1 | Complete    | 2026-03-08 | - |
| 82. Nyquist v2.1 Completion | 1/1 | Complete    | 2026-03-08 | - |

---
*Roadmap created: 2026-02-17*
*Last updated: 2026-03-08 — Phases 81-82 added via /gsd:plan-milestone-gaps; closes GAP-03, GAP-04 (alert/metrics accuracy) and Nyquist validation gaps for phases 74, 75, 78, 79, 80*
