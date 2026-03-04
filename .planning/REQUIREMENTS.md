# Requirements: OpenClaw Agent Orchestration

**Defined:** 2026-03-04
**Core Value:** The system designs and refactors its own orchestration — proposing multi-agent structures, learning from human corrections, and improving structural reasoning over time.

## v2.1 Requirements

Requirements for v2.1 Programmatic Integration & Real-Time Streaming. Each maps to roadmap phases.

### Tech Debt

- [ ] **DEBT-01**: All async test failures resolved (test_proposer.py, test_state_engine_memory.py pass without event loop errors)
- [ ] **DEBT-02**: Single TopologyProposal class with graph field, rubric_score, to_dict/from_dict — proposer.py uses it directly
- [ ] **DEBT-03**: Zero hardcoded user-specific paths (/home/ollie, /home/ob) in any tracked file — all resolved via OPENCLAW_ROOT or env vars

### Event Infrastructure

- [ ] **EVNT-01**: Event bridge Unix socket server starts automatically during orchestration startup
- [ ] **EVNT-02**: Event bus handlers forward all published events through Unix socket transport to connected clients
- [ ] **EVNT-03**: L3 container output (stdout/stderr) streamed from pool.py through event bridge to dashboard SSE in real-time
- [ ] **EVNT-04**: Dashboard SSE endpoint has heartbeat keepalive and automatic reconnect with buffered history (last 100 events per task)

### Gateway Integration

- [ ] **GATE-01**: Router dispatches all directives (including propose) exclusively through gateway HTTP API — no execFileSync fallback
- [ ] **GATE-02**: Gateway health check runs at startup with fail-fast error if gateway unavailable (outside bootstrap mode)
- [ ] **GATE-03**: Bootstrap mode flag (OPENCLAW_BOOTSTRAP=1 or --bootstrap) allows CLI commands (project init, monitor status) without running gateway

### Agent Registry

- [ ] **AREG-01**: Single AgentRegistry class merges openclaw.json agents.list with agents/*/agent/config.json — per-agent config is source of truth
- [ ] **AREG-02**: Auto-discovery scans agents/*/ at startup, registers all found agents
- [ ] **AREG-03**: Config drift detection flags mismatches between central and per-agent configs at startup with warnings

### Dashboard Streaming

- [ ] **DASH-01**: Terminal-style output panel renders live L3 output per active task
- [ ] **DASH-02**: Click task on task board opens live output stream
- [ ] **DASH-03**: Auto-scroll with pause-on-scroll-up, resume-on-scroll-to-bottom behavior

### Observability

- [ ] **OBSV-01**: Unified /api/metrics endpoint consolidates Python orchestration metrics and dashboard-computed metrics
- [ ] **OBSV-02**: Pipeline timeline view shows L1 dispatch → L2 decomposition → L3 execution with timestamps and durations
- [ ] **OBSV-03**: SOUL dynamic variables (active_task_count, pool_utilization, topology context) verified populated at spawn time

### Docker

- [ ] **DOCK-01**: Shared openclaw-base:bookworm-slim base image created and used by L3 Dockerfile

### Integration Verification

- [ ] **INTG-01**: End-to-end test: L1 dispatches via gateway → L2 decomposes → L3 spawns with populated SOUL → output streams to dashboard → events flow → metrics update

## v2.2 Requirements (Deferred)

### Multi-Agent Coordination

- **CORD-01**: Structured handoff protocol with context summary, partial results, blocking reason
- **CORD-02**: Shared task queue with multiple L3s claiming subtasks from coordinator
- **CORD-03**: Collaborative memory namespace scoped per task (prefix convention in memU)
- **CORD-04**: Pre-merge conflict detection with L2 arbitration and L1 escalation
- **CORD-05**: Coordination dashboard view showing multi-agent task flow

### Event Persistence

- **EPER-01**: Event persistence to disk/DB for replay and compliance
- **EPER-02**: Event replay API for debugging and audit

## Out of Scope

| Feature | Reason |
|---------|--------|
| Git submodule wiring | Deprioritized per user feedback — formalize later |
| Mid-flight topology adaptation | Requires stable integration layer first; v2.2+ |
| Auto-scaling | Dependent on structural scoring being proven; v2.2+ |
| Self-refactoring execution graphs | Research-grade complexity; v2.2+ |
| Dynamic role spawning | Needs runtime topology mutation; v2.2+ |
| Consumer-facing UI | Audience is AI-native teams, not end users |
| Protocol standardization (ACP) | Deferred until proven internally |
| Prometheus /metrics endpoint | JSON-only for v2.1; Prometheus optional in v2.2 |
| Windows/cross-platform support | Linux-only tooling; Unix sockets are appropriate |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEBT-01 | Phase 68 | Pending |
| DEBT-02 | Phase 68 | Pending |
| DEBT-03 | Phase 68 | Pending |
| DOCK-01 | Phase 69 | Pending |
| EVNT-01 | Phase 70 | Pending |
| EVNT-02 | Phase 70 | Pending |
| EVNT-03 | Phase 71 | Pending |
| EVNT-04 | Phase 71 | Pending |
| GATE-01 | Phase 72 | Pending |
| GATE-02 | Phase 72 | Pending |
| GATE-03 | Phase 72 | Pending |
| AREG-01 | Phase 73 | Pending |
| AREG-02 | Phase 73 | Pending |
| AREG-03 | Phase 73 | Pending |
| DASH-01 | Phase 74 | Pending |
| DASH-02 | Phase 74 | Pending |
| DASH-03 | Phase 74 | Pending |
| OBSV-01 | Phase 75 | Pending |
| OBSV-02 | Phase 75 | Pending |
| OBSV-03 | Phase 76 | Pending |
| INTG-01 | Phase 77 | Pending |

**Coverage:**
- v2.1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0

---
*Requirements defined: 2026-03-04*
*Last updated: 2026-03-04 — traceability complete, all 21 requirements mapped to phases 68-77*
