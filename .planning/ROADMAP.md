# Roadmap: OpenClaw Agent Orchestration

## Milestones

- ✅ **v1.0 Grand Architect Protocol Foundation** - Phases 1-10 (shipped 2026-02-23)
- ✅ **v1.1 Project Agnostic** - Phases 11-18 (shipped 2026-02-23)
- ✅ **v1.2 Orchestration Hardening** - Phases 19-25 (shipped 2026-02-24)
- ✅ **v1.3 Agent Memory** - Phases 26-38 (shipped 2026-02-24)
- ✅ **v1.4 Operational Maturity** - Phases 39-44 (shipped 2026-02-25)
- ✅ **v1.5 Config Consolidation** - Phases 45-53 (shipped 2026-02-25)
- ✅ **v1.6 Agent Autonomy** - Phases 54-60 (shipped 2026-02-26)
- 🚧 **v2.0 Structural Intelligence** - Phases 61-65 (in progress)

---

<details>
<summary>✅ v1.0–v1.6 (Phases 1-60) - SHIPPED</summary>

60 phases shipped across 6 milestones. See MILESTONES.md for full retrospective.

</details>

---

### 🚧 v2.0 Structural Intelligence (In Progress)

**Milestone Goal:** OpenClaw proposes its own orchestration structure — pre-execution structural intelligence with inspectable reasoning and learning from corrections.

## Phases

- [ ] **Phase 61: Topology Foundation** - Topology data model, serialization, diff engine, and isolated file storage
- [x] **Phase 62: Structure Proposal Engine** - Multi-candidate proposals (Lean/Balanced/Robust) with rubric scoring and constraint linting (completed 2026-03-03)
- [x] **Phase 63: Correction System and Approval Gate** - Soft re-proposal, hard direct edit, async diff analysis, and execution gate (completed 2026-03-03)
- [ ] **Phase 64: Structural Memory** - Correction storage, preference profiling, isolation from L3 SOUL injection
- [ ] **Phase 65: Topology Observability** - Dashboard topology graph, proposal comparison, correction history, confidence timeline

## Phase Details

### Phase 61: Topology Foundation
**Goal**: The system can represent, serialize, version, diff, and classify swarm topologies as explicit data objects stored in their own isolated files
**Depends on**: Phase 60 (v1.6 Autonomy)
**Requirements**: TOPO-01, TOPO-02, TOPO-03, TOPO-04, TOPO-05, TOPO-06
**Success Criteria** (what must be TRUE):
  1. User can inspect a topology as a structured JSON object showing agent nodes, delegation edges, archetype classification, and role count
  2. A topology round-trips through serialize/deserialize (JSON → dataclass → JSON) with zero data loss, verified by equality check
  3. System generates a human-readable structural diff between any two topology versions showing exactly which nodes and edges were added, removed, or modified
  4. System classifies a topology as Lean, Balanced, or Robust based on role count, hierarchy depth, and coordination pattern — consistently for the same topology
  5. Topology data files live under a dedicated `topology/` directory and are never read or written by L3 container flock operations
**Plans**: TBD

### Phase 62: Structure Proposal Engine
**Goal**: Given an outcome description, the system generates 2-3 scored, justified topology proposals across Lean/Balanced/Robust archetypes using constraint-validated LLM output
**Depends on**: Phase 61
**Requirements**: PROP-01, PROP-02, PROP-03, PROP-04, PROP-05, PROP-06
**Success Criteria** (what must be TRUE):
  1. User submits an outcome description and receives exactly 2-3 topology proposals, one per archetype, each with named roles, hierarchy, and delegation boundaries
  2. Each proposal displays a rubric score across all 7 dimensions (complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence) with a written justification
  3. Proposals that include roles not in the skill registry, or pool sizes exceeding project `max_concurrent`, are rejected by the constraint linter before they reach the user
  4. Proposal confidence scores are shown comparatively so the user can see which candidate scores higher on each dimension relative to the others
  5. Topology confidence threshold is configured under `topology.proposal_confidence_warning_threshold` — a separate key from the autonomy framework's `autonomy.confidence_threshold`
**Plans**: 5 plans
- [ ] 62-01-PLAN.md — Topology data model, serialization, and file storage (Phase 61 prerequisite)
- [ ] 62-02-PLAN.md — Topology diff engine and archetype classifier (Phase 61 prerequisite)
- [ ] 62-03-PLAN.md — Proposal data models, rubric scoring, and constraint linter
- [ ] 62-04-PLAN.md — LLM proposal generation pipeline with hybrid input
- [ ] 62-05-PLAN.md — CLI entry point, ASCII renderer, and config integration

### Phase 63: Correction System and Approval Gate
**Goal**: Users can correct proposals through textual feedback or direct edits, with the system enforcing an approval gate before execution and learning from every correction event
**Depends on**: Phase 62
**Requirements**: CORR-01, CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-07
**Success Criteria** (what must be TRUE):
  1. User can type feedback on a proposal and receive a revised proposal that visibly addresses the feedback, with a maximum of 3 re-proposals per feedback loop before the system surfaces the trade-off and stops cycling
  2. User can directly edit a proposed topology (roles, hierarchy) and the edited version executes immediately without waiting for async diff analysis to complete
  3. After any correction, the system stores a diff record showing the structural delta between the proposed and approved topology, timestamped and typed as soft or hard
  4. When the system had high confidence in a proposal that the user overrode, the system surfaces a non-blocking informational note explaining its original reasoning — this note never blocks execution
  5. No L3 container spawn occurs until the user has explicitly approved a topology version
**Plans**: 3 plans
Plans:
- [ ] 63-01-PLAN.md — Correction models, approval logic, storage extensions, and tests
- [ ] 63-02-PLAN.md — Interactive CLI session loop and openclaw-approve resume command
- [ ] 63-03-PLAN.md — L1 router approval gate and config extensions

### Phase 64: Structural Memory
**Goal**: The system accumulates correction history, extracts structural preferences, and uses them to improve future proposals — while keeping topology data completely isolated from L3 agent SOUL context
**Depends on**: Phase 63
**Requirements**: SMEM-01, SMEM-02, SMEM-03, SMEM-04, SMEM-05, SMEM-06
**Success Criteria** (what must be TRUE):
  1. After a correction, the system stores the diff record with timestamp, project id, correction type (soft/hard), and project context — retrievable by project
  2. Running a test L3 spawn after structural data has been written to memU shows zero topology, archetype, or rubric content in the L3 SOUL context (`/run/openclaw/soul.md`)
  3. User can query per-project correction count and see whether the preference profile has reached the minimum data threshold for active influence
  4. After sufficient corrections accumulate, the system surfaces an extracted pattern (e.g., "user flattens hierarchies for low-complexity tasks") visible in the structural memory report
  5. Preference profiling applies decay (older corrections weighted less) and epsilon-greedy exploration (20% random archetype ordering) so the system does not lock into early archetype preferences
**Plans**: TBD

### Phase 65: Topology Observability
**Goal**: The dashboard surfaces proposed and approved topologies as interactive graphs, shows correction history with structural diffs, and displays confidence and proposal evolution over time
**Depends on**: Phase 64 (Phase 63 for API route development)
**Requirements**: TOBS-01, TOBS-02, TOBS-03, TOBS-04, TOBS-05, TOBS-06
**Success Criteria** (what must be TRUE):
  1. Dashboard topology page renders the currently proposed topology as an interactive DAG with nodes labeled by role and edges labeled by relationship type
  2. Proposed and approved topologies appear side-by-side so the user can see what was suggested versus what was approved
  3. Correction history panel lists all corrections for a project with the structural diff (added/removed/modified nodes and edges) for each correction event
  4. Structural diff timeline shows how topology evolved chronologically across all proposals and corrections for a project in a single scrollable view
  5. Confidence evolution chart shows how each archetype's overall confidence score changed across correction cycles for a project
  6. Multi-proposal comparison view displays all 3 archetype candidates with their rubric scores, key differentiators, and archetype labels simultaneously
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 61 → 62 → 63 → 64 → 65

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 61. Topology Foundation | v2.0 | 0/? | Not started | - |
| 62. Structure Proposal Engine | 5/5 | Complete    | 2026-03-03 | - |
| 63. Correction System and Approval Gate | 3/3 | Complete   | 2026-03-03 | - |
| 64. Structural Memory | v2.0 | 0/? | Not started | - |
| 65. Topology Observability | v2.0 | 0/? | Not started | - |

---
*Roadmap created: 2026-03-03*
*v2.0 phases added: 2026-03-03 — phases 61-65 covering 31 requirements*
