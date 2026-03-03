# Requirements: OpenClaw v2.0 Structural Intelligence

**Defined:** 2026-03-03
**Core Value:** The system designs and refactors its own orchestration — proposing multi-agent structures, learning from human corrections, and improving structural reasoning over time.

## v2.0 Requirements

Requirements for structural intelligence milestone. Each maps to roadmap phases.

### Topology Data Model

- [x] **TOPO-01**: System represents swarm topology as an explicit graph object with nodes (roles) and edges (delegation/coordination relationships)
- [x] **TOPO-02**: User can serialize a topology to JSON and deserialize it back without data loss
- [x] **TOPO-03**: System tracks topology versions with timestamps and associates each version with a project
- [x] **TOPO-04**: System can compute a structural diff between two topology versions showing added/removed/modified nodes and edges
- [x] **TOPO-05**: System classifies each topology into an archetype (Lean/Balanced/Robust) based on role count, hierarchy depth, and coordination patterns
- [x] **TOPO-06**: Topology data is stored in a separate file from workspace-state.json to avoid lock contention with L3 execution

### Structure Proposal

- [ ] **PROP-01**: User can submit an outcome description and receive 2-3 topology proposals (Lean/Balanced/Robust archetypes)
- [ ] **PROP-02**: Each proposal includes: roles, hierarchy, delegation boundaries, coordination model, risk assessment, estimated complexity, and confidence level
- [ ] **PROP-03**: Each proposal is scored across a common rubric: complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence
- [ ] **PROP-04**: Each proposal includes written justification explaining why this structure fits the given outcome
- [ ] **PROP-05**: System validates proposals against constraints (available agent types, resource limits, project config) before presenting to user
- [ ] **PROP-06**: Proposal confidence scores are comparative across candidates (not absolute) so user can see relative strengths

### Correction System

- [ ] **CORR-01**: User can give textual feedback on a proposal and receive a re-proposal that addresses the feedback (soft correction)
- [ ] **CORR-02**: User can directly edit a proposed topology (add/remove/modify roles, change hierarchy) and the system executes the edited version (hard correction)
- [ ] **CORR-03**: System computes and stores the diff between proposed and approved topology after every correction
- [ ] **CORR-04**: On hard correction, system executes immediately then analyzes the diff asynchronously
- [ ] **CORR-05**: When system had high confidence in its original proposal and the edit contradicts it, system surfaces a non-blocking note explaining its reasoning
- [ ] **CORR-06**: System enforces a cycle limit (max 3 re-proposals per soft correction loop) to prevent infinite iteration
- [ ] **CORR-07**: User must explicitly approve a topology before it can be used for execution (approval gate)

### Structural Memory

- [ ] **SMEM-01**: System stores all topology correction diffs with timestamps, project context, and correction type (soft/hard)
- [ ] **SMEM-02**: Structural memory is categorically isolated from L3 execution memory — topology data never appears in L3 SOUL injection
- [ ] **SMEM-03**: System extracts recurring patterns from accumulated corrections (e.g., "user flattens hierarchies for low-complexity tasks")
- [ ] **SMEM-04**: System builds a user structural preference profile from correction history that influences the "preference fit" rubric score
- [ ] **SMEM-05**: Preference profiling includes decay (older corrections weighted less) and exploration (epsilon-greedy to prevent archetype lock-in)
- [ ] **SMEM-06**: System can report how many corrections have been accumulated per project and whether preference profiling has reached minimum data threshold

### Topology Observability

- [ ] **TOBS-01**: Dashboard displays the currently proposed topology as a visual graph (nodes = roles, edges = relationships)
- [ ] **TOBS-02**: Dashboard displays the approved topology alongside the proposed topology for comparison
- [ ] **TOBS-03**: Dashboard shows correction history for a project with structural diffs between versions
- [ ] **TOBS-04**: Dashboard shows a structural diff timeline — chronological view of how topology evolved across proposals and corrections
- [ ] **TOBS-05**: Dashboard shows confidence evolution — how proposal confidence scores changed across correction cycles
- [ ] **TOBS-06**: Dashboard shows the multi-proposal comparison view with rubric scores, key deltas, and archetype labels

## v2.1 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Runtime Adaptation

- **RADP-01**: System can detect mid-execution that topology needs adjustment and propose changes
- **RADP-02**: System can auto-scale agent count based on task load during execution
- **RADP-03**: System can dynamically spawn specialist roles when tension/bottlenecks are detected
- **RADP-04**: System can shrink topology when task simplifies during execution

### Self-Refactoring

- **SREF-01**: System can identify recurring subgraphs across projects and propose them as reusable topology templates
- **SREF-02**: System can recommend that a pattern of work deserves its own permanent agent class
- **SREF-03**: System can simulate alternative orchestration strategies and compare predicted outcomes

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mid-flight topology mutation | Requires topology-as-data to be stable first; v2.1+ |
| Auto-scaling during execution | Dependent on structural scoring being proven; v2.1+ |
| Self-refactoring execution graphs | Research-grade complexity; v2.1+ |
| Dynamic role spawning at runtime | Needs runtime topology mutation; v2.1+ |
| Consumer-facing UI | Audience is AI-native teams, platform teams, researchers |
| ACP protocol standardization | Deferred until structural intelligence is proven internally |
| Generic graph visualization | Domain-specific topology viz only; no general-purpose graph tool |
| Topology simulation/what-if | Requires scoring to be validated empirically first; v2.1+ |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TOPO-01 | Phase 61 | Complete |
| TOPO-02 | Phase 61 | Complete |
| TOPO-03 | Phase 61 | Complete |
| TOPO-04 | Phase 61 | Complete |
| TOPO-05 | Phase 61 | Complete |
| TOPO-06 | Phase 61 | Complete |
| PROP-01 | Phase 62 | Pending |
| PROP-02 | Phase 62 | Pending |
| PROP-03 | Phase 62 | Pending |
| PROP-04 | Phase 62 | Pending |
| PROP-05 | Phase 62 | Pending |
| PROP-06 | Phase 62 | Pending |
| CORR-01 | Phase 63 | Pending |
| CORR-02 | Phase 63 | Pending |
| CORR-03 | Phase 63 | Pending |
| CORR-04 | Phase 63 | Pending |
| CORR-05 | Phase 63 | Pending |
| CORR-06 | Phase 63 | Pending |
| CORR-07 | Phase 63 | Pending |
| SMEM-01 | Phase 64 | Pending |
| SMEM-02 | Phase 64 | Pending |
| SMEM-03 | Phase 64 | Pending |
| SMEM-04 | Phase 64 | Pending |
| SMEM-05 | Phase 64 | Pending |
| SMEM-06 | Phase 64 | Pending |
| TOBS-01 | Phase 65 | Pending |
| TOBS-02 | Phase 65 | Pending |
| TOBS-03 | Phase 65 | Pending |
| TOBS-04 | Phase 65 | Pending |
| TOBS-05 | Phase 65 | Pending |
| TOBS-06 | Phase 65 | Pending |

**Coverage:**
- v2.0 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0

---
*Requirements defined: 2026-03-03*
*Last updated: 2026-03-03 — traceability complete, phases 61-65 assigned*
