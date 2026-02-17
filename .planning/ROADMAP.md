# Roadmap: OpenClaw (Grand Architect Protocol)

## Phases

- [ ] **Phase 1: Environment Substrate** - Establish the Ubuntu 24.04 host, Docker networking, and OpenClaw Gateway.
- [ ] **Phase 2: Core Orchestration** - Implement the L1 (ClawdiaPrime) and L2 (PumplAI_PM) hierarchy and delegation.
- [ ] **Phase 3: Specialist Execution** - Deploy isolated L3 specialists and implement Jarvis Protocol state synchronization.
- [ ] **Phase 4: Monitoring Uplink** - Deploy the "occc" dashboard for real-time human oversight and monitoring.

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
- [ ] 01-environment-substrate-01-PLAN.md — Substrate Initialization (SET-01, SET-02)
- [ ] 01-environment-substrate-02-PLAN.md — Gateway & Isolation Enforcement (SET-03, SEC-01)

### Phase 2: Core Orchestration
**Goal**: Implement the L1 and L2 hierarchy and delegation skills.
**Depends on**: Phase 1
**Requirements**: HIE-01, HIE-02, COM-01, COM-02
**Success Criteria**:
  1. ClawdiaPrime (L1) successfully initializes and registers PumplAI_PM (L2) node.
  2. A task issued to L1 is correctly routed to L2 via the OpenClaw Gateway.
  3. L2 identity and SOUL are correctly enforced, restricting access to `/app/project`.
**Plans**: TBD

### Phase 3: Specialist Execution
**Goal**: Deploy isolated L3 specialists and implement state synchronization.
**Depends on**: Phase 2
**Requirements**: HIE-03, HIE-04, COM-03, COM-04
**Success Criteria**:
  1. L3 Specialist containers (Frontend/Backend) are dynamically spawned with physical isolation.
  2. `state.json` (Jarvis Protocol) updates in real-time as L3 workers execute tasks.
  3. Semantic snapshots correctly capture and persist workspace state changes.
**Plans**: TBD

### Phase 4: Monitoring Uplink
**Goal**: Provide real-time visibility into the running swarm via the occc dashboard.
**Depends on**: Phase 3
**Requirements**: DSH-01, DSH-02, DSH-03, DSH-04, SEC-02
**Success Criteria**:
  1. The `occc` dashboard (Next.js 16) renders live agent status and global metrics.
  2. Live logs from isolated containers are streamed and visible in the dashboard.
  3. Sensitive information is successfully redacted from all debug outputs and logs.
**Plans**: TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Environment Substrate | 0/2 | Not started | - |
| 2. Core Orchestration | 0/1 | Not started | - |
| 3. Specialist Execution | 0/1 | Not started | - |
| 4. Monitoring Uplink | 0/1 | Not started | - |
