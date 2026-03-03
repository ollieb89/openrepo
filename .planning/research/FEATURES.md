# Feature Research

**Domain:** Multi-agent orchestration — v2.0 Structural Intelligence
**Researched:** 2026-03-03
**Confidence:** MEDIUM-HIGH (verified against published research, ecosystem analysis, and codebase inspection)

---

## Context: What This Milestone Adds

v1.6 shipped the autonomy framework (confidence scoring, self-directed decomposition, escalation).
The system can execute, but the structure it executes against is designed entirely by humans.

v2.0 makes the system propose its own structure — before execution, with inspectable reasoning, and
learning from corrections. Five capability areas are in scope:

1. **Topology as Data** — swarm structures as explicit, serializable, versionable, diffable objects
2. **Structure Proposal Engine** — multi-proposal with scored rubric and archetype rationale
3. **Dual Correction System** — soft feedback (re-propose) + hard direct edit (execute, diff-analyze async)
4. **Structural Memory** — topology diffs, correction rationales, preference profiling
5. **Topology Observability** — proposed/approved structures, correction history, confidence evolution

This document covers table stakes, differentiators, and anti-features for each capability area,
with complexity ratings and dependency mapping to existing OpenClaw infrastructure.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any pre-execution structural intelligence system must provide. Missing these means the
system feels like a toy or a black box.

| Feature | Why Expected | Complexity | Infrastructure Dependency |
|---------|--------------|------------|--------------------------|
| Topology serialization to JSON | Users need to inspect, version-control, and diff structures without running the system. Research shows "Agent Spec" and similar approaches treat agent configs as portable, platform-agnostic serializable objects (HIGH confidence — arxiv 2510.04173) | MEDIUM | Extends `workspace-state.json` pattern from `state_engine.py` |
| Multiple scored candidates (not one answer) | In orchestration design, "best answer" depends on context the system cannot fully know. Multi-candidate output with scoring criteria surfaces the reasoning so humans can make informed choices. AI evaluation research shows rubric-based scoring is the accepted pattern (MEDIUM confidence — Arize/Galileo patterns) | MEDIUM | Extends `autonomy/confidence.py` scoring model |
| Human approval gate before execution | Pre-execution human review is table stakes for consequential structure changes. HITL research confirms it is the dominant pattern for high-stakes agentic decisions (HIGH confidence — Microsoft reference architecture, AWS patterns) | LOW | Fits into existing L2 → L3 spawn gate in `spawn.py` |
| Soft feedback pathway (re-propose) | Users expect to say "try again with fewer agents" without rewriting JSON manually. This is the baseline interactive pattern in HITL orchestration systems | LOW | New API endpoint; calls proposal engine again with feedback context |
| Hard edit pathway (execute immediately) | Users who know what they want should be able to edit the structure directly and proceed without friction. Execute-then-analyze is the standard pattern (respects user authority) | MEDIUM | Requires edit input, topology validation, then spawn |
| Structured scoring rubric (visible dimensions) | Scoring must be transparent to be trusted. Research shows users disengage from opaque recommendations — criteria must be named and each score justified, not just a single confidence number | LOW | New data field; extends existing confidence score model |
| Topology version history | "What changed between the approved structure and what was actually spawned?" is a basic audit question. Version history is standard in any configuration-as-code system | MEDIUM | New persistence layer; reuses `state_engine.py` flock pattern |
| Topology diff display | When a user edits a proposed topology, they need to see what changed. Structural diff is the same expectation as git diff for code | MEDIUM | Python `deepdiff` or JSON patch (RFC 6902); dashboard display |
| Correction storage | The system must store what correction was made, by whom, and what topology it produced. Without this, learning is impossible and the audit trail is missing | LOW | New storage schema; integrates with existing memU REST API |

### Differentiators (Competitive Advantage)

Features that make OpenClaw's structural intelligence meaningfully better than a basic
"suggest a plan" prompt.

| Feature | Value Proposition | Complexity | Infrastructure Dependency |
|---------|-------------------|------------|--------------------------|
| Fixed archetype system (Lean / Balanced / Robust) | Most orchestration frameworks produce one-off outputs with no interpretable shape. Named archetypes make proposals legible — users learn what "Lean" means over time, reducing cognitive load on each decision. Research on multi-agent architectures shows archetypes (hierarchical, swarm, pipeline) are the dominant conceptual model, but systems rarely make them explicit and comparable | MEDIUM | New archetype engine in orchestration package |
| Per-dimension rubric scoring with justification | A composite confidence number is not inspectable. Per-dimension scoring (complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence) lets users understand *why* Balanced scores higher than Lean on a given task. Rubric research confirms 7 primary dimensions is the operationally optimal range before cognitive overload (MEDIUM confidence — Galileo agent evaluation 2026) | MEDIUM | New scoring data model; LLM prompt for justification text |
| Async diff analysis after direct edits | When a user edits a proposal and runs it, OpenClaw should asynchronously compare the edit against what it would have proposed and surface non-blocking notes when divergence is high-confidence and significant. This closes the learning loop without slowing execution. No existing framework does this | HIGH | New async task; requires topology diff engine; memU for storage |
| Preference profiling from correction history | By accumulating diffs between proposals and corrections, the system builds a preference profile per project. Future proposals are then biased toward known preferences. Research on PRELUDE-style learning from user edits confirms this is viable with structured diff inputs (MEDIUM confidence — RLHF/HITL literature 2025) | HIGH | Requires structural memory store + LLM analysis of correction diffs |
| Confidence evolution timeline | Showing how the system's structural confidence has changed across tasks for a project makes learning visible and auditable. Users can see whether corrections are improving proposal quality | MEDIUM | Requires time-series storage of per-proposal confidence scores |
| Structural memory as retrieval context | Before proposing a structure, retrieve similar past topologies and their outcomes from memU. Use successful past structures as positive anchors, failed ones as negative examples. This is the "memory-augmented recommendation" pattern from 2025 research (MEDIUM confidence — MAP framework, MARM) | HIGH | Integrates with existing `memory_client.py` and memU REST API |
| Non-blocking insight surfacing | When async diff analysis completes and finds significant divergence, surface a non-blocking note in the dashboard rather than blocking execution or raising an alert. This respects user authority while building the learning dataset | MEDIUM | SSE event to dashboard; new event type in `events/protocol.py` |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Mid-flight topology adaptation | "The structure should evolve as the task progresses" | Requires topology-as-data to be proven and stable first. Mid-flight changes invalidate the approval gate (users approved structure A, system changed to structure B). Container lifecycle and pool management are designed for static topologies. This is explicitly deferred to v2.1+ in PROJECT.md | Pre-execution proposal covers 90% of the value. Post-execution retrospective analysis captures the rest |
| Single-best recommendation | "Just tell me the right answer" | Single-best removes the reasoning surface and makes the learning signal weaker. When the system is wrong, there is no alternative to fall back to. Multi-proposal is the correct default per PROJECT.md key decisions | Present all three archetypes, clearly rank them, and make the top candidate visually prominent — this satisfies users who want a recommendation without hiding the alternatives |
| Auto-approval on high-confidence proposals | "If confidence > 0.95, just run it automatically" | Removes the human from consequential structure decisions. Autonomy v1.6 already has confidence-based escalation for task execution — structural decisions are a tier above task decisions in consequence. Auto-approval erodes the trust model | Reduce friction on high-confidence proposals (pre-fill the approval form, highlight "this matches your past preferences") but never remove the gate |
| Freeform topology editor (drag-and-drop) | "I want a GUI to design agent graphs" | Visual graph editors have high implementation cost and are the wrong interaction model for a platform used by developers and researchers who work in code and config | Structured JSON edit with schema validation and diff preview is the right interface for this audience |
| Topology diff on every task run | "Compare every run to the last one" | Most task-to-task topology variation is intentional (different task types get different structures). Diffing everything creates noise. The relevant diff is proposal vs user correction, not run vs run | Diff on correction events only. Store the proposed topology and the approved topology; compute the delta explicitly when a correction occurs |
| LLM-generated scoring without rubric constraints | "Let the LLM score proposals however it wants" | Unconstrained LLM scoring is non-deterministic and non-comparable across proposals. Users cannot build intuition about what scores mean. Research on rubric-based evaluation confirms that constrained, named dimensions produce more reliable and trustworthy outputs (HIGH confidence — Arize, Galileo patterns) | Fixed 7-dimension rubric with LLM filling in justification text per dimension. Scores are computed from structured criteria, not free-form assessment |
| Dynamic role spawning at runtime | "Add a specialized agent when the task needs one" | Same reason as mid-flight adaptation — changes the topology after approval. L3 pool management uses static semaphores per project. Dynamic spawning requires pool capacity reservation at proposal time and runtime renegotiation | Define all roles in the pre-execution proposal. If a task genuinely needs an unexpected role, that is a signal that the proposal engine needs to be improved for that task type |
| Correction feedback as RLHF fine-tuning | "Use corrections to fine-tune the proposal LLM" | Fine-tuning requires large labeled datasets, infrastructure for training runs, and introduces model versioning complexity that is out of scope. The proposal engine is a prompted LLM, not a trained model | Use corrections as retrieval context (structural memory) and heuristic updates (preference profile). This achieves learning without fine-tuning overhead |

---

## Feature Dependencies

```
[Topology Serialization]
    └──required by──> [Multi-Candidate Proposals] (candidates are serialized topology objects)
    └──required by──> [Human Approval Gate] (gate operates on serialized topology)
    └──required by──> [Topology Version History] (serialized objects are what gets versioned)
    └──required by──> [Topology Diff Display] (diff operates on two serialized objects)
    └──required by──> [Correction Storage] (corrections are stored as before/after topology pairs)

[Multi-Candidate Proposals]
    └──required by──> [Per-Dimension Rubric Scoring] (rubric is evaluated per candidate)
    └──required by──> [Archetype System] (each candidate maps to an archetype)
    └──requires──> [Topology Serialization]

[Human Approval Gate]
    └──required by──> [Soft Feedback Pathway] (gate provides the "re-propose" action)
    └──required by──> [Hard Edit Pathway] (gate provides the "edit and approve" action)
    └──requires──> [Multi-Candidate Proposals]

[Correction Storage]
    └──required by──> [Preference Profiling] (profiling reads correction history)
    └──required by──> [Async Diff Analysis] (diff results are stored as corrections)
    └──required by──> [Confidence Evolution Timeline] (timeline reads per-correction confidence)
    └──requires──> [Topology Serialization]
    └──integrates──> [memU REST API] (existing infrastructure)

[Async Diff Analysis]
    └──requires──> [Hard Edit Pathway] (diff is triggered by direct edit)
    └──requires──> [Topology Diff Display] (diff engine is shared)
    └──requires──> [Correction Storage] (diff result is written to structural memory)
    └──feeds──> [Non-Blocking Insight Surfacing] (insight is the async diff result)

[Preference Profiling]
    └──requires──> [Correction Storage] (minimum 3-5 corrections needed for signal)
    └──feeds──> [Multi-Candidate Proposals] (profile biases future proposals)
    └──feeds──> [Structural Memory as Retrieval Context]

[Structural Memory as Retrieval Context]
    └──requires──> [Correction Storage]
    └──requires──> [Topology Version History]
    └──integrates──> [memory_client.py] (existing retrieve/store API)
    └──feeds──> [Multi-Candidate Proposals] (retrieved past structures as context)

[Non-Blocking Insight Surfacing]
    └──requires──> [Async Diff Analysis]
    └──integrates──> [SSE event transport] (existing events/transport.py)
    └──integrates──> [Dashboard] (existing notification patterns)
```

### Dependency Notes

- **Topology Serialization is the foundation.** Everything else operates on serialized topology objects.
  Build this first. No other v2.0 feature is possible without it.

- **Correction Storage is the memory anchor.** Preference profiling, async diff analysis, confidence
  evolution, and structural memory retrieval all read from or write to the correction store.
  Build this second (after serialization and proposal engine exist to produce data to store).

- **Async Diff Analysis depends on Hard Edit being built first.** You cannot analyze a diff until
  users can perform direct edits. Hard Edit must ship before Async Diff Analysis.

- **Preference Profiling requires data accumulation.** It cannot produce useful output on the first
  1-2 tasks. The feature becomes useful only after 5+ corrections have been stored. Build the
  storage and retrieval first; enable profiling as a background enrichment process that improves
  silently as data accumulates.

- **Structural Memory as Retrieval Context enhances Proposal Engine but is not required for it.**
  The Proposal Engine can launch without retrieval context (cold start), then gradually improve as
  memory accumulates. This means Proposal Engine and Structural Memory can be built in parallel.

---

## MVP Definition

### Launch With (v2.0 core — structural intelligence is not functional without these)

- [ ] **TOPO-01: Topology Serialization Schema** — JSON schema for topology objects (nodes, edges,
  roles, resource limits, archetype tag). The foundation. All other features depend on this shape.

- [ ] **PROP-01: Multi-Candidate Proposal Engine** — Given a task directive, produce 2-3 topology
  candidates (Lean, Balanced, Robust archetypes) with per-dimension rubric scores and justification
  text. Integrates with existing L2 agent context.

- [ ] **PROP-02: Archetype System** — Lean (1-2 agents, fast, minimal coordination), Balanced
  (explicit coordinator + specialists), Robust (reviewer gate, risk containment, slower). Fixed
  archetypes with defined characteristics, not generated on the fly.

- [ ] **GATE-01: Human Approval Gate** — Before L3 spawn, present proposals to the human. Accept
  approval, soft feedback, or direct edit. Block spawn until approved. Integrates with existing
  spawn.py gate pattern.

- [ ] **CORR-01: Correction Storage** — Store every correction event: task context, proposed
  topologies, which was approved, direct edits made, feedback text. This is the data foundation for
  all learning features.

- [ ] **DIFF-01: Topology Diff Engine** — Compute structural diff between two topology objects
  (node additions/removals, edge changes, resource limit changes). Used by both the UI display and
  the async analysis pipeline.

- [ ] **OBS-01: Topology Observability Panel** — Dashboard view showing proposed topologies, which
  was approved, correction history for a task/project. Uses existing SSE infrastructure and
  dashboard patterns.

### Add After Validation (v2.0 extension — once core is working and data is accumulating)

- [ ] **CORR-02: Async Diff Analysis** — After direct edit + execution, asynchronously analyze
  the diff between proposed and approved topology. Store analysis. Surface non-blocking note if
  divergence is significant and high-confidence. Trigger: after correction event is stored.

- [ ] **MEM-01: Structural Memory Retrieval** — Before proposing, retrieve similar past topologies
  from memU. Use as positive/negative anchors in the proposal prompt. Trigger: add to proposal
  engine once correction data exists.

- [ ] **OBS-02: Confidence Evolution Timeline** — Show per-project trend of proposal confidence
  scores over time. Requires accumulated correction data (minimum 5 tasks).

### Future Consideration (v2.1+)

- [ ] **MEM-02: Preference Profiling** — Derive structured preference profile from correction diff
  history. Requires substantial correction data (10+ per project). Feeds future proposals.

- [ ] **TOPO-MID: Mid-Flight Topology Adaptation** — Explicitly deferred in PROJECT.md. Requires
  topology-as-data to be stable and proven under real workload first.

- [ ] **TOPO-AUTO: Auto-Approval on High Confidence** — Only viable once preference profiling is
  accurate enough to predict approval reliably (estimated 50+ corrections per project minimum).

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Topology Serialization Schema (TOPO-01) | HIGH — everything depends on it | LOW-MEDIUM — data modeling, no new services | P1 |
| Multi-Candidate Proposal Engine (PROP-01) | HIGH — core value proposition | HIGH — LLM integration + rubric evaluation | P1 |
| Archetype System (PROP-02) | HIGH — makes proposals interpretable | MEDIUM — fixed definitions + constraints | P1 |
| Human Approval Gate (GATE-01) | HIGH — required for responsible execution | MEDIUM — new API endpoint + spawn integration | P1 |
| Correction Storage (CORR-01) | HIGH — data foundation for all learning | LOW — schema + storage; reuses memU patterns | P1 |
| Topology Diff Engine (DIFF-01) | HIGH — needed by gate display and async analysis | MEDIUM — deepdiff or JSON patch + test suite | P1 |
| Topology Observability Panel (OBS-01) | MEDIUM-HIGH — structural visibility | MEDIUM — new dashboard panel + SSE integration | P1 |
| Async Diff Analysis (CORR-02) | MEDIUM — closes learning loop | HIGH — async pipeline + LLM analysis | P2 |
| Structural Memory Retrieval (MEM-01) | MEDIUM — improves proposals with history | MEDIUM — extends existing memory_client.py | P2 |
| Confidence Evolution Timeline (OBS-02) | MEDIUM — makes learning visible | LOW — time-series query + chart | P2 |
| Preference Profiling (MEM-02) | HIGH long-term — drives personalization | HIGH — requires substantial data + LLM analysis | P3 |

**Priority key:**
- P1: Must have for v2.0 to be called "Structural Intelligence"
- P2: Should have — builds on P1 foundations, high value-to-cost ratio once core works
- P3: Future consideration — high value but requires substantial data accumulation first

---

## Capability Area Deep-Dives

### 1. Topology as Data

**What it is:** Swarm structures represented as explicit serializable objects — not implicit agent
spawn calls buried in code.

**Table stakes behavior:**
- Every proposed and approved topology is a named, timestamped JSON object stored to disk
- Topology objects are diffable: two topologies produce a structured diff (nodes added/removed,
  edges changed, resource limits modified)
- Topology objects reference existing agent configs (agents/ directory) rather than redefining them
- Topology objects include the archetype tag, the scoring rubric results, and the task context

**Schema shape (recommended):**
```json
{
  "topology_id": "topo-20260303-abc123",
  "task_id": "task-001",
  "project_id": "pumplai",
  "archetype": "balanced",
  "created_at": "2026-03-03T10:00:00Z",
  "status": "proposed | approved | rejected | executed",
  "nodes": [
    { "role": "coordinator", "agent_id": "pumplai_pm", "resource_limit_gb": 4 },
    { "role": "coder", "agent_id": "python_backend_worker", "resource_limit_gb": 4 }
  ],
  "edges": [
    { "from": "coordinator", "to": "coder", "type": "delegate" }
  ],
  "scoring": {
    "complexity": { "score": 0.3, "justification": "Two-agent structure..." },
    "coordination_overhead": { "score": 0.4, "justification": "..." },
    "risk_containment": { "score": 0.5, "justification": "..." },
    "time_to_first_output": { "score": 0.8, "justification": "..." },
    "cost_estimate": { "score": 0.7, "justification": "..." },
    "preference_fit": { "score": 0.6, "justification": "..." },
    "overall_confidence": 0.62
  },
  "correction": null
}
```

**Infrastructure dependency:** Extends workspace-state.json pattern. Uses same `fcntl.flock()` mechanism as Jarvis Protocol. New file path: `workspace/.openclaw/{project_id}/topologies/{topology_id}.json`.

---

### 2. Structure Proposal Engine

**What it is:** Given a task directive, generates 2-3 candidate topologies using fixed archetypes, a
common scoring rubric, and justification text per dimension.

**Table stakes behavior:**
- Always produces at least 2 candidates (Lean and Balanced minimum; Robust when task risk is high)
- Each candidate has a named archetype with documented characteristics
- Each candidate has per-dimension scores with one sentence of justification text
- Proposals are generated before any L3 container is spawned
- Proposal generation time < 30 seconds (acceptable latency for a pre-execution gate)

**Archetype definitions:**
- **Lean:** 1-2 agents, minimal coordination overhead, fast time-to-first-output, appropriate for
  well-understood tasks with clear scope. Higher risk if requirements are ambiguous.
- **Balanced:** Explicit coordinator + 1-2 specialists, structured handoffs, moderate coordination
  overhead. Good default for most tasks.
- **Robust:** Coordinator + specialists + reviewer gate, risk containment built in, slower but safer.
  Appropriate for tasks touching production systems, large diffs, or ambiguous requirements.

**Scoring rubric (7 dimensions, 0.0-1.0 each, higher = better):**
1. `complexity` — how many moving parts (lower complexity = higher score)
2. `coordination_overhead` — inter-agent communication cost (lower overhead = higher score)
3. `risk_containment` — safety nets built into the structure (more containment = higher score)
4. `time_to_first_output` — how quickly results start flowing (faster = higher score)
5. `cost_estimate` — relative token/compute cost (lower cost = higher score)
6. `preference_fit` — alignment with past approved topologies for this project (higher fit = higher score)
7. `overall_confidence` — weighted composite of the above

**Implementation approach:** LLM-generated proposals with structured output schema. The proposal
prompt includes: task directive, task complexity estimate (from existing `autonomy/confidence.py`),
past approved topologies for this project (from structural memory), and archetype definitions.
LLM fills in nodes, edges, and scoring justifications; scoring numbers are computed deterministically
from the structured output, not generated by the LLM.

---

### 3. Dual Correction System

**What it is:** Two distinct pathways for human input at the approval gate.

**Soft feedback (re-propose):**
- User provides natural language feedback: "Try with fewer agents", "Add a reviewer"
- System passes feedback text + original proposals back to the proposal engine
- New proposals are generated incorporating the feedback
- Original proposals remain visible for comparison
- Feedback text is stored in correction record

**Hard edit (direct edit):**
- User edits the topology JSON directly (or via a structured form) and approves
- Spawn proceeds immediately — no re-proposal, no waiting
- The topology diff (proposed vs approved) is computed and stored
- An async task begins: analyze the diff, determine if it represents a preference signal or
  a one-off override
- Non-blocking note is surfaced in dashboard if divergence is high-confidence and significant
  (does not block the running task)

**Key interaction principle:** User authority is never blocked or second-guessed synchronously.
The system learns asynchronously. This is the "execute-then-analyze" pattern from PROJECT.md.

**Infrastructure dependency:**
- Soft feedback: New API endpoint calling proposal engine again with feedback context
- Hard edit: Topology validation (schema check) → existing spawn.py gate → async diff analysis task
- Non-blocking note: New event type in `events/protocol.py`, SSE to dashboard

---

### 4. Structural Memory

**What it is:** The persistence layer that makes correction learning possible.

**Correction record schema:**
```json
{
  "correction_id": "corr-20260303-xyz789",
  "task_id": "task-001",
  "project_id": "pumplai",
  "created_at": "2026-03-03T10:05:00Z",
  "correction_type": "direct_edit | soft_feedback | approval",
  "proposed_topology_ids": ["topo-abc", "topo-def", "topo-ghi"],
  "approved_topology_id": "topo-abc-edited",
  "feedback_text": "Reduced to one agent — task is simpler than estimated",
  "diff_summary": { "nodes_removed": ["reviewer"], "edges_removed": [...] },
  "async_analysis": {
    "completed_at": "2026-03-03T10:12:00Z",
    "confidence": 0.82,
    "interpretation": "User consistently removes reviewer gate for read-only tasks",
    "preference_signal": true
  }
}
```

**Preference profiling (deferred to v2.1 MVP, built in P3):**
After 5+ corrections, extract recurring patterns:
- "This project consistently prefers Lean archetype for data analysis tasks"
- "This project always removes the reviewer gate for read-only tasks"
- "This project always adds a reviewer gate for tasks touching the payments module"

These are stored as structured preference rules, not free-form text, so they can be applied
deterministically to bias future proposals.

**Infrastructure dependency:** memU REST API (existing). New collection/namespace in memU:
`structural_memory` scoped per project. Uses same `memory_client.py` patterns as task memory.

---

### 5. Topology Observability

**What it is:** Dashboard views and event streams for structural decisions.

**Required views:**
- **Proposal view:** For a given task, show all proposed topologies side-by-side with rubric scores.
  Highlight which was approved. Show correction type.
- **Correction history:** Per-project timeline of corrections. Diff visualization for direct edits.
  Feedback text for soft re-proposals.
- **Confidence evolution:** Per-project chart of `overall_confidence` scores over time across tasks.
  Shows whether corrections are improving proposal quality.
- **Structural diff view:** When a direct edit occurred, show the diff between proposed and approved
  topology. Highlight additions (green) and removals (red). Format as structured change list, not
  raw JSON diff.

**Event types needed (new additions to `events/protocol.py`):**
- `TOPOLOGY_PROPOSED` — emitted when proposal engine completes
- `TOPOLOGY_APPROVED` — emitted when human approves (with or without edit)
- `TOPOLOGY_CORRECTION` — emitted when direct edit occurs (includes diff summary)
- `TOPOLOGY_INSIGHT` — emitted when async diff analysis completes with a preference signal

**Infrastructure dependency:** All events route through existing `events/transport.py` → gateway
SSE bridge → dashboard. New dashboard panel alongside existing TaskBoard, AutonomyPanel,
EscalationContextPanel, and CourseCorrectionHistory components.

---

## User Interaction Patterns

Based on research into HITL orchestration patterns and the existing OpenClaw user base (AI-native
product teams, platform engineers, multi-agent researchers):

**Expected primary flow (most common):**
1. User submits task directive to L2
2. Proposal engine generates 3 candidates (takes < 30s)
3. User reviews proposals in dashboard, selects Balanced candidate
4. L3 containers spawn against approved topology
5. No correction stored (straight approval is still a data point)

**Expected secondary flow (soft feedback):**
1. Same as above, but user sees "Add a dedicated test agent" is missing from all proposals
2. User types "Add a test agent role" in the feedback box
3. System re-proposes with test agent included in all candidates
4. User approves

**Expected secondary flow (direct edit):**
1. User sees proposals but knows exactly what they want
2. User removes the reviewer node from Balanced candidate, approves
3. Spawn proceeds immediately
4. 2-3 minutes later, async analysis completes
5. Dashboard shows non-blocking note: "You removed the reviewer gate — this matches your pattern
   for low-risk data tasks"

**Expected power user pattern:**
- User with 20+ corrections stored
- Proposals are now biased toward known preferences
- Proposals feel "on target" more often
- Approval rate increases, corrections decrease

---

## Existing Integration Points (v1.6 foundations v2.0 builds on)

| v1.6 Component | v2.0 Usage |
|----------------|------------|
| `autonomy/confidence.py::ConfidenceFactors` | Extended with structural confidence dimensions; 7-dimension rubric maps onto existing complexity/ambiguity/past_success factors |
| `autonomy/confidence.py::ConfidenceScorer` | Proposal engine uses this protocol to score each candidate |
| `state_engine.py` (Jarvis Protocol) | Topology objects stored using same flock pattern; new topology file alongside workspace-state.json |
| `skills/spawn/spawn.py` | Approval gate inserted before container spawn; topology object passed as spawn context |
| `memory_client.py` | Used for structural memory retrieval (retrieve similar past topologies) and correction storage |
| `events/protocol.py` | Extended with 4 new topology event types |
| `events/transport.py` | Topology events route through existing SSE bridge |
| `soul_renderer.py` | L3 SOUL injection extended to include approved topology as context |
| `packages/dashboard/` | New topology observability panel alongside existing AutonomyPanel and CourseCorrectionHistory |
| `agent_registry.py` | Proposal engine queries agent registry to enumerate available agent roles |
| `autonomy/hooks.py` | Topology approval hook added to before-spawn lifecycle |

---

## Sources

- [AgentConductor: Topology Evolution for Multi-Agent Code Generation (arxiv 2602.17100)](https://arxiv.org/abs/2602.17100) — RL-optimized topology evolution, density-aware design, difficulty-adaptive structures
- [Multi-Agent Collaboration via Evolving Orchestration (arxiv 2505.19591)](https://arxiv.org/html/2505.19591v1) — graph topology evolution patterns, inspection of activation patterns
- [Open Agent Specification Technical Report (arxiv 2510.04173)](https://arxiv.org/html/2510.04173v1) — portable, serializable agent configs, platform-agnostic schema
- [AI Agent Orchestration Patterns — Microsoft Azure Architecture Center (2026)](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) — sequential, concurrent, hierarchical patterns; complexity spectrum guidance
- [Multi-Agent Reference Architecture: Observability — Microsoft](https://microsoft.github.io/multi-agent-reference-architecture/docs/observability/Observability.html) — observability signals for multi-agent systems
- [Agent Evaluation Framework: Rubrics and Benchmarks — Galileo 2026](https://galileo.ai/blog/agent-evaluation-framework-metrics-rubrics-benchmarks) — 7-dimension rubric structure, sub-dimensions
- [Rubric-Based Evaluation for Agentic Systems — AI4HUMAN/Medium 2025](https://medium.com/@aiforhuman/rubric-based-evaluation-for-agentic-systems-db6cb14d8526) — constrained rubric vs free-form LLM scoring
- [Human-in-the-Loop Agentic AI Systems — OneReach 2026](https://onereach.ai/blog/human-in-the-loop-agentic-ai-systems/) — HITL patterns for high-stakes decisions, approval gates
- [LLM-Based Human-Agent Collaboration Survey (arxiv 2505.00753)](https://arxiv.org/html/2505.00753v4) — HITL collaboration patterns, corrective feedback mechanisms
- [RLHF and Learning from Corrections (arxiv 2504.12501)](https://arxiv.org/html/2504.12501v3) — preference learning from edit diffs, PRELUDE-style approaches
- [Multi-Agent Architectures — Swarms Framework Docs](https://docs.swarms.world/en/latest/swarms/concept/swarm_architectures/) — chain, star, mesh, hierarchical archetype patterns
- [Best Practices for Multi-Agent Orchestration — Skywork 2025](https://skywork.ai/blog/ai-agent-orchestration-best-practices-handoffs/) — handoff patterns, schema versioning pitfalls
- Codebase analysis: `packages/orchestration/src/openclaw/autonomy/`, `state_engine.py`, `memory_client.py`, `events/protocol.py`, `skills/spawn/spawn.py`, `packages/dashboard/src/components/`

---

*Feature research for: OpenClaw v2.0 Structural Intelligence*
*Researched: 2026-03-03*
