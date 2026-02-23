# Roadmap: OpenClaw (Grand Architect Protocol)

## Phases

- [x] **Phase 1: Environment Substrate** - Establish the Ubuntu 24.04 host, Docker networking, and OpenClaw Gateway. ✓ COMPLETE
- [x] **Phase 2: Core Orchestration** - Implement the L1 (ClawdiaPrime) and L2 (PumplAI_PM) hierarchy and delegation. ✓ COMPLETE
- [x] **Phase 3: Specialist Execution** - Deploy isolated L3 specialists and implement Jarvis Protocol state synchronization.
- [ ] **Phase 4: Monitoring Uplink** - Deploy the "occc" dashboard for real-time human oversight and monitoring.
- [ ] **Phase 5: Wiring Fixes & Initialization** - Fix L1 config.json and initialize snapshots directory to close integration gaps.
- [ ] **Phase 6: Phase 3 Formal Verification** - Verify HIE-03, HIE-04, COM-03, COM-04 and create Phase 3 VERIFICATION.md.
- [ ] **Phase 7: Phase 4 Formal Verification** - Verify DSH-01, DSH-02, DSH-03, DSH-04, SEC-02 and create Phase 4 VERIFICATION.md.

---

## Phase Details

### Phase 1: Environment Substrate
**Goal**: Establish the physical and networking foundation for the swarm.
**Depends on**: Nothing
**Requirements**: SET-01, SET-02, SET-03, SEC-01
**Success Criteria**:
  1. Ubuntu 24.04 host is configured with Docker and Nvidia drivers.
  2. OpenClaw Gateway is active and responds to ping on port 18789.
  3. Root `openclaw.json` is validated and correctly maps the PumplAI workspace volume.
**Plans**: 2 plans
- [x] 01-environment-substrate-01-PLAN.md — Substrate Initialization (SET-01, SET-02) ✓
- [x] 01-environment-substrate-02-PLAN.md — Gateway & Isolation Enforcement (SET-03, SEC-01) ✓

### Phase 2: Core Orchestration
**Goal**: Implement the L1 and L2 hierarchy and delegation skills.
**Depends on**: Phase 1
**Requirements**: HIE-01, HIE-02, COM-01, COM-02
**Success Criteria**:
  1. ClawdiaPrime (L1) successfully initializes and registers PumplAI_PM (L2) node.
  2. A task issued to L1 is correctly routed to L2 via the OpenClaw Gateway.
  3. L2 identity and SOUL are correctly enforced, restricting access to `/app/project`.
**Plans**: 2 plans
- [x] 02-01-PLAN.md — Hierarchy Initialization (HIE-01, HIE-02) ✓
- [x] 02-02-PLAN.md — Communication & Delegation (COM-01, COM-02) ✓

### Phase 3: Specialist Execution
**Goal**: Deploy isolated L3 specialists and implement state synchronization.
**Depends on**: Phase 2
**Requirements**: HIE-03, HIE-04, COM-03, COM-04
**Success Criteria**:
  1. L3 Specialist containers are dynamically spawned with physical isolation.
  2. `state.json` (Jarvis Protocol) updates in real-time as L3 workers execute tasks.
  3. Semantic snapshots correctly capture and persist workspace state changes.
**Plans**: 4 plans
- [x] 03-01-PLAN.md -- L3 Foundation + Jarvis Protocol State Engine (HIE-03, COM-03)
- [x] 03-02-PLAN.md -- Container Lifecycle + Physical Isolation (HIE-03, HIE-04)
- [x] 03-03-PLAN.md -- Workspace Persistence + CLI Monitoring (COM-04)
- [x] 03-04-PLAN.md -- Registration + Integration Verification (HIE-03, HIE-04, COM-03, COM-04)

### Phase 4: Monitoring Uplink
**Goal**: Provide real-time visibility into the running swarm via the occc dashboard.
**Depends on**: Phase 3
**Requirements**: DSH-01, DSH-02, DSH-03, DSH-04, SEC-02
**Success Criteria**:
  1. The `occc` dashboard (Next.js 16) renders live agent status and global metrics.
  2. Live logs from isolated containers are streamed and visible in the dashboard.
  3. Sensitive information is successfully redacted from all debug outputs and logs.
**Plans**: 4 plans
- [ ] 04-01-PLAN.md -- Data Layer + State API (DSH-01, DSH-02)
- [ ] 04-02-PLAN.md -- Log Streaming + Redaction Pipeline (DSH-03, SEC-02)
- [ ] 04-03-PLAN.md -- Mission Control Dashboard UI (DSH-01, DSH-04)
- [ ] 04-04-PLAN.md -- Deployment + End-to-End Verification (DSH-01, DSH-02, DSH-03, DSH-04, SEC-02)

### Phase 5: Wiring Fixes & Initialization
**Goal**: Close integration and flow gaps identified by milestone audit — fix broken L1→L2 delegation wiring and initialize missing snapshots directory.
**Depends on**: Phase 2, Phase 3
**Requirements**: COM-01 (integration fix), COM-04 (initialization fix)
**Gap Closure**: Closes gaps from v1.0 audit
**Success Criteria**:
  1. ClawdiaPrime (L1) has a config.json with skill_registry that references router_skill.
  2. L1 → L2 delegation flow completes end-to-end.
  3. workspace/.openclaw/snapshots/ directory exists and snapshot capture flow works.
**Plans**: 2 plans
- [ ] 05-01-PLAN.md -- L1 Config + Delegation Wiring (COM-01)
- [ ] 05-02-PLAN.md -- Snapshots Initialization + Verification (COM-04)

### Phase 6: Phase 3 Formal Verification
**Goal**: Formally verify all Phase 3 deliverables and create the missing VERIFICATION.md.
**Depends on**: Phase 5
**Requirements**: HIE-03, HIE-04, COM-03, COM-04
**Gap Closure**: Closes gaps from v1.0 audit
**Success Criteria**:
  1. L3 specialist containers spawn with physical isolation (no-new-privileges, cap_drop ALL).
  2. Jarvis Protocol state.json updates in real-time during L3 task execution.
  3. Semantic snapshots capture and persist workspace state changes.
  4. Phase 3 VERIFICATION.md created with all criteria assessed.
**Plans**: 2 plans
- [ ] 06-01-PLAN.md -- Build verification script + live testing + fix failures (HIE-03, HIE-04, COM-03, COM-04)
- [ ] 06-02-PLAN.md -- Produce 06-VERIFICATION.md with evidence (HIE-03, HIE-04, COM-03, COM-04)

### Phase 7: Phase 4 Formal Verification
**Goal**: Formally verify all Phase 4 deliverables and create the missing VERIFICATION.md.
**Depends on**: Phase 6
**Requirements**: DSH-01, DSH-02, DSH-03, DSH-04, SEC-02
**Gap Closure**: Closes gaps from v1.0 audit
**Success Criteria**:
  1. occc dashboard renders live agent status and global metrics.
  2. Live logs from isolated containers stream to the dashboard with redaction.
  3. Sensitive information is successfully redacted from all debug outputs.
  4. Phase 4 VERIFICATION.md created with all criteria assessed.
**Plans**: 3 plans
- [x] 07-01-PLAN.md — Build verification scripts + live testing (DSH-01, DSH-02, DSH-03, DSH-04, SEC-02)
- [x] 07-02-PLAN.md — Produce 07-VERIFICATION.md with evidence (DSH-01, DSH-02, DSH-03, DSH-04, SEC-02)
- [ ] 07-03-PLAN.md — Fix SSE stream to emit actual data events (DSH-02, gap closure from UAT)

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Environment Substrate | 2/2 | ✓ Complete | 2026-02-17 |
| 2. Core Orchestration | 2/2 | ✓ Complete | 2026-02-17 |
| 3. Specialist Execution | 4/4 | ✓ Complete | 2026-02-18 |
| 4. Monitoring Uplink | 0/4 | Planning Complete | - |
| 5. Wiring Fixes & Initialization | 0/2 | Planned | - |
| 6. Phase 3 Formal Verification | 0/2 | Planned | - |
| 7. Phase 4 Formal Verification | 2/3 | UAT Gap Closure | - |
