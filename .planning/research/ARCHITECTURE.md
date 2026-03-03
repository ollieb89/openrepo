# Architecture Research

**Domain:** AI Swarm Orchestration — v2.0 Structural Intelligence Integration
**Researched:** 2026-03-03
**Confidence:** HIGH — direct codebase analysis of all integration points

---

## Context: Scope of This Document

This document is scoped to v2.0 Structural Intelligence integration. It answers:
- What new components are needed?
- Which existing modules get modified vs. left untouched?
- What is the data flow for a full proposal → correction → learning cycle?
- What is the recommended build order given dependencies?

The five features: Topology as Data, Structure Proposal Engine, Dual Correction System, Structural Memory, Topology Observability.

---

## System Overview: Existing Architecture Baseline

```
┌─────────────────────────────────────────────────────────────────────────┐
│  L1: ClawdiaPrime (skills/router/index.js)                               │
│    dispatches via execFileSync → openclaw agent CLI                      │
├─────────────────────────────────────────────────────────────────────────┤
│  L2: Project Manager (agents/<pm_id>/agent/SOUL.md)                     │
│    skills/spawn/spawn.py  →  Docker L3 containers                       │
│    skills/review/         →  git diff review + merge/reject             │
├─────────────────────────────────────────────────────────────────────────┤
│  L3: Ephemeral Specialists (Docker, openclaw-l3-specialist:latest)       │
│    Jarvis Protocol state sync (fcntl.flock on workspace-state.json)     │
│    SOUL injection via /run/openclaw/soul.md bind mount                  │
├─────────────────────────────────────────────────────────────────────────┤
│  Orchestration Engine (packages/orchestration/src/openclaw/)            │
│    state_engine.py     — workspace-state.json read/write with flock     │
│    soul_renderer.py    — template substitution + section merging        │
│    agent_registry.py   — AgentSpec objects from openclaw.json           │
│    memory_client.py    — async memU REST client (scoped)                │
│    autonomy/           — AutonomyContext state machine, hooks           │
│    event_bus.py        — in-process fire-and-forget pub/sub             │
│    events/protocol.py  — OrchestratorEvent cross-runtime types          │
│    snapshot.py         — git staging branch workflow                    │
│    config.py           — constants, path resolution, schema             │
├─────────────────────────────────────────────────────────────────────────┤
│  Memory Layer (packages/memory/ — FastAPI + PostgreSQL + pgvector)      │
│    /memorize    — store with embeddings, category tagging               │
│    /retrieve    — semantic search, user_id scoping, cursor              │
│    port 18791, Docker network openclaw-net                              │
├─────────────────────────────────────────────────────────────────────────┤
│  Dashboard (packages/dashboard/ — Next.js 14, port 6987)               │
│    /api/tasks, /api/memory, /api/metrics, /api/suggestions             │
│    Autonomy panels, escalation, course-correction history               │
│    Reads workspace-state.json + Docker API + memU                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## New Components Required for v2.0

### 1. Topology Data Model (NEW — Python)

**File:** `packages/orchestration/src/openclaw/topology/model.py`

The core serializable graph object. All other features depend on this.

```python
@dataclass
class AgentNode:
    id: str                  # agent identifier
    role: str                # "orchestrator" | "coordinator" | "executor"
    tier: int                # 1, 2, or 3
    skill_hints: List[str]   # ["code", "test", "review"]
    resource_profile: ResourceProfile   # mem_limit, cpu_quota, max_concurrent

@dataclass
class TopologyEdge:
    from_id: str
    to_id: str
    relationship: str        # "delegates_to" | "reports_to" | "reviews"

@dataclass
class SwarmTopology:
    id: str                  # uuid, stable across edits
    project_id: str
    archetype: str           # "lean" | "balanced" | "robust"
    version: int             # monotonic, incremented on every save
    nodes: List[AgentNode]
    edges: List[TopologyEdge]
    created_at: float
    parent_id: Optional[str] # id of topology this was derived from (for diffs)

    def to_dict(self) -> dict: ...
    def to_spawn_config(self) -> dict: ...   # convert to spawn.py-compatible format
    def diff(self, other: "SwarmTopology") -> "TopologyDiff": ...
```

**Persistence:** `workspace/.openclaw/<project_id>/topology/` directory
- `current.json` — approved active topology
- `proposals/<proposal_id>.json` — pending proposals (multiple coexist)
- `history/<topology_id>.json` — immutable archive of each approved version

**Why new, not extend state_engine:** `workspace-state.json` stores task runtime state (status, activity_log) under Jarvis Protocol with strict LOCK_EX semantics. Topology is pre-execution structural configuration, not runtime task state. Separate file prevents lock contention and schema interference.

---

### 2. Topology Diff Engine (NEW — Python)

**File:** `packages/orchestration/src/openclaw/topology/diff.py`

```python
@dataclass
class NodeChange:
    change_type: str    # "added" | "removed" | "modified"
    node_id: str
    before: Optional[dict]
    after: Optional[dict]

@dataclass
class TopologyDiff:
    from_id: str
    to_id: str
    node_changes: List[NodeChange]
    edge_changes: List[EdgeChange]
    score_delta: Dict[str, float]   # per rubric dimension

    def summary(self) -> str: ...   # human-readable description
    def is_structural(self) -> bool: ...   # True if nodes/edges changed, not just scores
```

This is called by the Proposal Engine when generating multi-candidate output, by the Dual Correction System when analyzing direct edits, and by Structural Memory when extracting learning signals.

---

### 3. Structure Proposal Engine (NEW — Python)

**File:** `packages/orchestration/src/openclaw/topology/proposer.py`

```python
class StructureProposer:
    def __init__(self, project_id: str, registry: AgentRegistry): ...

    def propose(
        self,
        task_description: str,
        context: Dict[str, Any],
        preferred_archetype: Optional[str] = None,
    ) -> List[ScoredProposal]: ...

    def _build_archetype(
        self,
        archetype: str,   # "lean" | "balanced" | "robust"
        context: Dict[str, Any],
    ) -> SwarmTopology: ...

    def _score(
        self,
        topology: SwarmTopology,
        context: Dict[str, Any],
        preferences: StructuralPreferenceProfile,
    ) -> RubricScore: ...
```

```python
@dataclass
class RubricScore:
    complexity: float
    coordination_overhead: float
    risk_containment: float
    time_to_first_output: float
    cost_estimate: float
    preference_fit: float
    overall_confidence: float

@dataclass
class ScoredProposal:
    topology: SwarmTopology
    score: RubricScore
    justification: str   # prose explanation of scoring decisions
    archetype: str
```

**Fixed archetypes:**
- **Lean:** L1 → L2 → 1-2 L3 (minimal agents, fast time-to-output, low coordination cost)
- **Balanced:** L1 → L2 → {code L3, test L3, review L3} (explicit coordination, standard)
- **Robust:** L1 → L2 → multiple specialized L3 with peer review edges (high risk containment)

Proposer always returns all three archetypes scored. The call site picks 2-3 to present to L1/L2 based on confidence delta.

**Integration with spawn.py:** `ScoredProposal.topology.to_spawn_config()` produces the dict passed to `spawn_l3_specialist()`. Backwards-compatible — existing spawn call signature unchanged.

---

### 4. Scoring Rubric Registry (NEW — Python)

**File:** `packages/orchestration/src/openclaw/topology/rubric.py`

Centralizes rubric dimension definitions, weight configuration, and scoring helpers.

```python
RUBRIC_DIMENSIONS = [
    "complexity",
    "coordination_overhead",
    "risk_containment",
    "time_to_first_output",
    "cost_estimate",
    "preference_fit",
    "overall_confidence",
]

class RubricEvaluator:
    def __init__(self, weights: Dict[str, float] = DEFAULT_WEIGHTS): ...
    def evaluate(self, topology: SwarmTopology, context: dict) -> RubricScore: ...
    def compare(self, a: RubricScore, b: RubricScore) -> int: ...  # -1, 0, 1
```

Weights are configurable via `openclaw.json` → `topology.rubric_weights`. Default weights ship in `config.py`.

---

### 5. Dual Correction System (NEW — Python)

**File:** `packages/orchestration/src/openclaw/topology/correction.py`

```python
class CorrectionHandler:
    def soft_correct(
        self,
        proposal_id: str,
        feedback: str,
        project_id: str,
    ) -> List[ScoredProposal]:
        """Re-run proposer with feedback injected into context. Non-destructive."""
        ...

    def hard_correct(
        self,
        proposal_id: str,
        edited_topology: SwarmTopology,
        project_id: str,
    ) -> ApprovedTopology:
        """Accept user's direct edit immediately. Analyze diff asynchronously."""
        ...

    def _analyze_correction_async(
        self,
        original: SwarmTopology,
        edited: SwarmTopology,
        feedback: Optional[str],
        project_id: str,
    ) -> None:
        """Daemon thread: compute diff, update preference profile, emit note if high-confidence divergence."""
        ...
```

**Hard correction execute-then-analyze pattern:**
1. `hard_correct()` writes `current.json` immediately, emits `topology.approved` event.
2. Spawns daemon thread calling `_analyze_correction_async()`.
3. Async analysis: computes `TopologyDiff`, updates `StructuralPreferenceProfile` via StructuralMemory.
4. If diff contradicts high-confidence original score, emits `topology.correction_note` event (non-blocking).
5. Dashboard surfaces note as dismissable info banner — never blocks execution.

**Soft correction re-propose pattern:**
1. Feedback string appended to proposer context under `correction_history`.
2. Proposer re-runs all three archetypes with updated context.
3. Returns new `List[ScoredProposal]` — no topology is committed yet.

---

### 6. Structural Memory (NEW — Python + memU integration)

**File:** `packages/orchestration/src/openclaw/topology/structural_memory.py`

```python
class StructuralMemory:
    """Persists topology learning signals to memU with structural category scoping."""

    def __init__(self, memu_url: str, project_id: str): ...

    async def store_diff(self, diff: TopologyDiff, rationale: str) -> None:
        """Store a correction diff with human rationale for pattern extraction."""
        ...

    async def store_outcome(
        self,
        topology_id: str,
        outcome: str,  # "success" | "partial" | "failure"
        notes: str,
    ) -> None:
        """Store execution outcome against the topology that ran it."""
        ...

    async def get_preference_profile(self) -> StructuralPreferenceProfile:
        """Retrieve the current preference profile from memU."""
        ...

    async def update_preference_profile(self, update: ProfileUpdate) -> None:
        """Merge a ProfileUpdate into the stored preference profile."""
        ...

    async def retrieve_relevant(self, context: str) -> List[dict]:
        """Semantic retrieval of past structural decisions relevant to context."""
        ...
```

**memU integration:** Uses existing `MemoryClient` with a new `AgentType.TOPOLOGY = "topology"` enum value. Category tag: `"topology_correction"` or `"topology_outcome"`. The `user_id` scope is `project_id` — same scoping as task memory, structurally isolated by category.

**StructuralPreferenceProfile:**
```python
@dataclass
class StructuralPreferenceProfile:
    project_id: str
    preferred_archetypes: Dict[str, float]   # archetype → weight
    rubric_overrides: Dict[str, float]       # dimension → learned weight
    correction_count: int
    last_updated: float

    def to_rubric_weights(self) -> Dict[str, float]: ...
```

Profile is stored as a structured JSON memory item in memU, retrieved and applied each time the proposer runs. Enables the system to learn toward human preferences over time without changing any source code.

---

### 7. Topology Observability Layer (NEW — Python API + TypeScript UI)

**Python side — new API endpoints in the Gateway or a new FastAPI router:**

```
GET  /api/topology/{project_id}/proposals       → list pending proposals
GET  /api/topology/{project_id}/proposals/{id}  → single proposal with scores
POST /api/topology/{project_id}/proposals/{id}/accept  → hard-approve
POST /api/topology/{project_id}/proposals/{id}/feedback → soft correct
GET  /api/topology/{project_id}/current         → approved active topology
GET  /api/topology/{project_id}/history         → timeline of approved topologies
GET  /api/topology/{project_id}/corrections     → correction history with diffs
```

These endpoints can live in the Next.js API layer (route handlers reading topology files directly, same pattern as existing `/api/tasks/route.ts` reading `workspace-state.json`) rather than needing a new Python service.

**TypeScript dashboard — new pages/components:**

| File | Purpose |
|------|---------|
| `src/app/topology/page.tsx` | Main topology page |
| `src/components/topology/ProposalCard.tsx` | Single proposal with rubric scores |
| `src/components/topology/TopologyGraph.tsx` | DAG visualization (nodes + edges) |
| `src/components/topology/RubricScoreBar.tsx` | 7-dimension score display |
| `src/components/topology/CorrectionHistory.tsx` | Timeline of corrections with diffs |
| `src/components/topology/ConfidenceEvolution.tsx` | Score trend over time |
| `src/app/api/topology/[projectId]/proposals/route.ts` | API route |
| `src/app/api/topology/[projectId]/current/route.ts` | API route |

Add "Topology" to `Sidebar.tsx` nav items (single line addition).

---

## Component Classification: Modified vs. New vs. Untouched

### Modified (surgical additions, backwards-compatible)

| Component | File | What Changes |
|-----------|------|-------------|
| `config.py` | `packages/orchestration/src/openclaw/config.py` | Add `TOPOLOGY_DIR` path helper, topology rubric weight constants, `topology` section to `OPENCLAW_JSON_SCHEMA` |
| `memory_client.py` | `.../memory_client.py` | Add `AgentType.TOPOLOGY = "topology"` enum value |
| `events/protocol.py` | `.../events/protocol.py` | Add `EventDomain.TOPOLOGY`, new `EventType` values: `TOPOLOGY_PROPOSED`, `TOPOLOGY_APPROVED`, `TOPOLOGY_CORRECTED`, `TOPOLOGY_OUTCOME_STORED` |
| `agent_registry.py` | `.../agent_registry.py` | No code change. `AgentSpec` objects are the source of truth for `AgentNode` population in the proposer — proposer imports `AgentRegistry` directly |
| `spawn.py` | `skills/spawn/spawn.py` | One new optional parameter: `topology_id: Optional[str]` stamped onto task metadata for traceability. No other changes |
| `project_config.py` | `.../project_config.py` | Add `get_topology_dir(project_id)` helper |
| `state_engine.py` | `.../state_engine.py` | No structural changes. `set_task_metric()` used as-is to stamp `topology_id` on tasks |
| `Sidebar.tsx` | `packages/dashboard/src/components/layout/Sidebar.tsx` | Add one nav item: `{ href: '/topology', label: 'Topology', icon: ... }` |
| `openclaw.json` schema | `config.py` `OPENCLAW_JSON_SCHEMA` | Add optional `topology` top-level key with rubric weights, proposal defaults |

### New (net-new files, no modification to callers required)

| Component | Location | Purpose |
|-----------|----------|---------|
| `topology/model.py` | `packages/orchestration/src/openclaw/topology/` | `SwarmTopology`, `AgentNode`, `TopologyEdge`, `RubricScore`, `ScoredProposal` |
| `topology/diff.py` | same | `TopologyDiff`, `NodeChange`, `EdgeChange` |
| `topology/proposer.py` | same | `StructureProposer`, archetype builders, rubric scoring |
| `topology/rubric.py` | same | `RubricEvaluator`, dimension constants, weight config |
| `topology/correction.py` | same | `CorrectionHandler`, soft/hard correction paths |
| `topology/structural_memory.py` | same | `StructuralMemory`, `StructuralPreferenceProfile` |
| `topology/__init__.py` | same | Public exports |
| `src/app/topology/page.tsx` | `packages/dashboard/src/app/` | Topology observability page |
| `src/components/topology/*.tsx` | `packages/dashboard/src/components/topology/` | Proposal cards, graph, rubric bars |
| `src/app/api/topology/...` | `packages/dashboard/src/app/api/topology/` | API routes for topology data |
| `src/lib/types/topology.ts` | `packages/dashboard/src/lib/types/` | TypeScript types for topology objects |

### Untouched (verified no changes needed)

| Component | Reason |
|-----------|--------|
| `state_engine.py` (core JarvisState logic) | Topology files use independent directory, no lock contention |
| `soul_renderer.py` | SOUL templates unchanged; topology context is pre-spawn, not in SOUL |
| `skills/spawn/pool.py` | Pool semaphore logic independent of topology; topology_id passed as metadata only |
| `docker/l3-specialist/Dockerfile` | Containers receive topology via task metadata/env; no image changes |
| `autonomy/` | Autonomy framework runs post-spawn; topology is pre-execution only (v2.0 scope) |
| `snapshot.py` | Git staging branch workflow unchanged; reviews still operate on code diffs |
| `packages/memory/` | memU service is backend infrastructure; new category tags require no service changes |
| `extensions/memory-memu/` | Agent auto-capture extension unchanged |

---

## Data Flow: Full Proposal → Correction → Learning Cycle

```
[1] REQUEST
L1/L2 requests structure for a new task
    ↓
[2] PROPOSE
StructureProposer.propose(task_description, context)
    ↓ retrieves
StructuralMemory.retrieve_relevant(context)   → memU /retrieve
    ↓ applies
StructuralPreferenceProfile → RubricEvaluator weights
    ↓ builds
Three archetypes: Lean, Balanced, Robust
    ↓ scores each with
RubricEvaluator.evaluate(topology, context) → RubricScore
    ↓ returns
List[ScoredProposal] stored to proposals/ directory
    ↓ emits
EventType.TOPOLOGY_PROPOSED → event_bus → Dashboard SSE → ProposalCards rendered
    ↓
[3a] SOFT CORRECTION (user provides feedback, wants re-proposal)
User submits feedback text via Dashboard
    ↓ POST /api/topology/{id}/proposals/{proposal_id}/feedback
CorrectionHandler.soft_correct(proposal_id, feedback)
    ↓ appends feedback to context["correction_history"]
StructureProposer.propose(updated_context)
    ↓ returns new List[ScoredProposal]
Dashboard re-renders proposal cards (no topology committed)
    ↓
[3b] HARD CORRECTION (user directly edits topology)
User edits topology graph in Dashboard, submits
    ↓ POST /api/topology/{id}/proposals/{proposal_id}/accept with edited_topology
CorrectionHandler.hard_correct(proposal_id, edited_topology)
    ↓ IMMEDIATE:
Writes current.json → project approved topology
Emits EventType.TOPOLOGY_APPROVED
    ↓ ASYNC (daemon thread):
TopologyDiff.diff(original_proposal, edited_topology)
StructuralMemory.store_diff(diff, rationale)   → memU /memorize
StructuralMemory.update_preference_profile(update)
    ↓ IF high-confidence divergence:
Emits EventType.TOPOLOGY_CORRECTION_NOTE → Dashboard info banner (dismissable)
    ↓
[4] EXECUTE
spawn.py called with topology_id stamped to task metadata
L3 containers spawned per topology nodes (unchanged spawn flow)
state_engine.update_task() stamps topology_id on task record
    ↓
[5] LEARN (post-execution)
Task completes → state_engine triggers memory extractor (existing)
    ↓ NEW: topology outcome extracted
StructuralMemory.store_outcome(topology_id, outcome, notes) → memU /memorize
    ↓ next proposal cycle reads this via retrieve_relevant()
Preference profile updated → rubric weights drift toward proven patterns
```

---

## Patterns to Follow

### Pattern 1: Lazy Import + Daemon Thread (memory operations)

**What:** All blocking I/O (memU writes, preference profile updates) runs in daemon threads. Main flow never blocks.
**When to use:** Any `StructuralMemory` write operation, any correction analysis.
**Example:** See `snapshot._memorize_review_decision()` and `state_engine._run_memory_extractor()` — identical pattern.

```python
def _analyze_correction_async(self, original, edited, project_id):
    def _run():
        try:
            asyncio.run(self._do_analysis(original, edited, project_id))
        except Exception as e:
            logger.error(f"Correction analysis failed: {e}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()
```

### Pattern 2: File-Per-Proposal with Atomic Write

**What:** Each proposal is a separate JSON file in `proposals/`. Approval writes `current.json` atomically.
**When to use:** Proposal storage and current topology management.
**Why:** Avoids locking multiple proposals simultaneously. Each file can be independently read, written, or deleted. `current.json` overwrites atomically (write-then-rename pattern).

```python
# Write proposal
path = topology_dir / "proposals" / f"{proposal.topology.id}.json"
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(proposal.topology.to_dict(), indent=2))
tmp.rename(path)  # atomic on POSIX

# Approve (overwrite current)
tmp = topology_dir / "current.json.tmp"
tmp.write_text(json.dumps(topology.to_dict(), indent=2))
tmp.rename(topology_dir / "current.json")
```

### Pattern 3: Event-First Observability

**What:** Emit typed `OrchestratorEvent` via `event_bus.emit()` at every topology lifecycle point.
**When to use:** After propose, after approve, after soft correction, after outcome stored.
**Why:** Dashboard SSE stream picks these up without polling. Consistent with existing task/autonomy event patterns.

### Pattern 4: memU Category Scoping for Structural Memory

**What:** All structural memory items use `category="topology_correction"` or `category="topology_outcome"`. Retrieval uses `where={"user_id": project_id}` plus category filter.
**Why:** Prevents structural memory from polluting task memory retrieval. Existing `MemoryClient.memorize()` already supports the `category` parameter — no service changes needed.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Topology State in workspace-state.json

**What people do:** Store topology proposals alongside task state in `workspace-state.json` because it's already the main state file.
**Why it's wrong:** `workspace-state.json` uses `fcntl.flock()` — adding topology read/write paths to the proposal flow creates lock contention between the pre-execution proposal UI and concurrent L3 task updates. Schema interference risk is high.
**Do this instead:** Separate `topology/` directory inside `workspace/.openclaw/<project_id>/`. No locking needed for proposal files (single-writer: L2 PM or dashboard user). Atomic rename for `current.json`.

### Anti-Pattern 2: Blocking on Correction Analysis

**What people do:** Wait for `TopologyDiff` computation and preference update before returning the approved topology to the user.
**Why it's wrong:** diff analysis + memU write can take 2-5 seconds. User submitted a direct edit, they expect immediate confirmation.
**Do this instead:** Execute-then-analyze. `hard_correct()` writes `current.json` and returns immediately. Daemon thread does the analysis asynchronously. Notes surface as non-blocking UI banners.

### Anti-Pattern 3: Single-Proposal Response

**What people do:** Return only the highest-scoring topology proposal.
**Why it's wrong:** Destroys the reasoning surface. User cannot see why alternatives were scored lower. Corrections are less informative when the user has no comparison baseline.
**Do this instead:** Always return all three archetype proposals scored. Dashboard presents comparison view. The call site can filter to top-2 by confidence delta if UI space is limited, but never compute single-best internally.

### Anti-Pattern 4: Mid-Execution Topology Mutation

**What people do:** Attempt to change the topology after containers have been spawned.
**Why it's wrong:** Out of v2.0 scope, and technically dangerous — pool semaphores are already acquired, containers are running, state_engine has task records. Would require coordinated shutdown.
**Do this instead:** Topology is pre-execution only (v2.0). Any mid-flight changes are queued for the next task batch. Dashboard clearly labels the current topology as "locked during execution."

### Anti-Pattern 5: Embedding Topology Logic in spawn.py

**What people do:** Put proposal generation inside `spawn_l3_specialist()` to colocate spawning and topology.
**Why it's wrong:** spawn.py is an L2 action called after structure is decided. Mixing proposal logic into spawn violates the temporal separation: propose → approve → spawn. Testability is also worse.
**Do this instead:** Proposer and correction live in `topology/`. spawn.py receives `topology_id` as an optional metadata annotation only.

---

## Integration Points Summary

### Existing → New Connections

| Existing Component | Connection | New Component |
|-------------------|------------|---------------|
| `AgentRegistry` | Read agent specs to populate `AgentNode` objects | `topology/proposer.py` |
| `MemoryClient` | Reused as-is with new `AgentType.TOPOLOGY` | `topology/structural_memory.py` |
| `event_bus.emit()` | New topology event types emitted | `topology/proposer.py`, `topology/correction.py` |
| `events/protocol.py` `EventDomain` | Add `TOPOLOGY` domain | All topology modules |
| `config.py` | New `get_topology_dir()` path helper | All topology modules |
| `spawn.py` `spawn_l3_specialist()` | Receives optional `topology_id` metadata | Caller (L2 PM) |
| `state_engine.set_task_metric()` | Stamp `topology_id` on task record | `spawn.py` |
| `workspace-state.json` tasks | Read `topology_id` field to link tasks → topologies | Dashboard topology API |
| `packages/memory/` (memU service) | New category tags, no service code changes | `structural_memory.py` |
| Dashboard `Sidebar.tsx` | One new nav item | `topology/page.tsx` |
| Dashboard SSE event stream | New `topology.*` event types | `topology/page.tsx` components |

---

## Suggested Build Order (Dependencies First)

**Phase A — Data Layer (no dependencies on other new components)**
1. `topology/model.py` — `SwarmTopology`, `AgentNode`, `TopologyEdge`, `RubricScore`, `ScoredProposal`
2. `topology/diff.py` — `TopologyDiff`, diff computation
3. `config.py` additions — `get_topology_dir()`, `TOPOLOGY_DIR`, schema additions
4. `events/protocol.py` additions — `EventDomain.TOPOLOGY`, new `EventType` values
5. `memory_client.py` — add `AgentType.TOPOLOGY`

**Phase B — Core Engine (depends on Phase A)**
6. `topology/rubric.py` — `RubricEvaluator`, dimension constants, weight loading
7. `topology/structural_memory.py` — `StructuralMemory`, `StructuralPreferenceProfile` (depends on `MemoryClient`, `AgentType.TOPOLOGY`)
8. `topology/proposer.py` — `StructureProposer` (depends on rubric, structural_memory, AgentRegistry, model)
9. `topology/correction.py` — `CorrectionHandler` (depends on proposer, structural_memory, diff)

**Phase C — Execution Integration (depends on Phase B)**
10. `spawn.py` modification — optional `topology_id` parameter (1-line addition + metadata stamp)
11. `project_config.py` — `get_topology_dir()` if not placed in `config.py`

**Phase D — Observability API (depends on Phase B, parallel with Phase C)**
12. `src/app/api/topology/[projectId]/proposals/route.ts` — list proposals
13. `src/app/api/topology/[projectId]/current/route.ts` — current topology
14. `src/app/api/topology/[projectId]/corrections/route.ts` — correction history
15. `src/lib/types/topology.ts` — TypeScript type definitions

**Phase E — Dashboard UI (depends on Phase D)**
16. `src/components/topology/TopologyGraph.tsx` — DAG visualization
17. `src/components/topology/ProposalCard.tsx` — proposal with rubric scores
18. `src/components/topology/RubricScoreBar.tsx` — 7-dimension bar
19. `src/components/topology/CorrectionHistory.tsx` — correction timeline
20. `src/components/topology/ConfidenceEvolution.tsx` — score trend
21. `src/app/topology/page.tsx` — main page wiring components
22. `Sidebar.tsx` — add topology nav item

---

## Recommended Project Structure (New Files)

```
packages/orchestration/src/openclaw/
└── topology/
    ├── __init__.py           # exports: SwarmTopology, StructureProposer, CorrectionHandler
    ├── model.py              # data model: SwarmTopology, AgentNode, TopologyEdge, RubricScore
    ├── diff.py               # diff engine: TopologyDiff, NodeChange, EdgeChange
    ├── rubric.py             # scoring: RubricEvaluator, RUBRIC_DIMENSIONS, weights
    ├── proposer.py           # engine: StructureProposer, archetype builders
    ├── correction.py         # dual correction: CorrectionHandler, soft/hard paths
    └── structural_memory.py  # learning: StructuralMemory, StructuralPreferenceProfile

packages/dashboard/src/
├── app/
│   ├── topology/
│   │   └── page.tsx          # main topology observability page
│   └── api/
│       └── topology/
│           └── [projectId]/
│               ├── proposals/
│               │   ├── route.ts                    # GET list, POST create
│               │   └── [proposalId]/
│               │       ├── route.ts                # GET single proposal
│               │       ├── accept/route.ts          # POST hard approve
│               │       └── feedback/route.ts        # POST soft correct
│               ├── current/route.ts                # GET approved topology
│               ├── history/route.ts                # GET topology timeline
│               └── corrections/route.ts            # GET correction history
├── components/
│   └── topology/
│       ├── ProposalCard.tsx           # single scored proposal
│       ├── TopologyGraph.tsx          # DAG nodes + edges
│       ├── RubricScoreBar.tsx         # 7-dimension horizontal bars
│       ├── CorrectionHistory.tsx      # correction timeline with diffs
│       └── ConfidenceEvolution.tsx    # confidence trend chart
└── lib/
    └── types/
        └── topology.ts                # TypeScript type definitions
```

Workspace topology files (runtime data, gitignored):
```
workspace/.openclaw/<project_id>/
├── topology/
│   ├── current.json                   # approved active topology
│   ├── proposals/
│   │   └── <uuid>.json               # pending proposals (multiple coexist)
│   └── history/
│       └── <uuid>.json               # immutable archive per approved version
```

---

## Scalability Considerations

| Concern | At current scale (1-10 projects) | At 50+ projects |
|---------|----------------------------------|-----------------|
| Topology file I/O | File-per-project directory is trivially fast | Still fast; consider index file if listing many histories |
| Proposal generation | Single-process, synchronous acceptable | Move to background job if proposal latency > 2s |
| memU structural memory writes | Async daemon threads, non-blocking | Existing memU service handles; no changes needed |
| Dashboard topology graph render | Client-side D3/SVG for < 20 nodes | Fine for expected topology sizes (3-10 agents) |
| Preference profile retrieval | One memU retrieve per propose call | Cache profile in-memory with 60s TTL |

The structural intelligence layer is pre-execution, human-in-the-loop, and not on any hot path. Scale is not a concern for v2.0 deployment.

---

## Sources

- Direct codebase analysis: `packages/orchestration/src/openclaw/` (all modules)
- Direct codebase analysis: `packages/dashboard/src/` (components, API routes, types)
- Direct codebase analysis: `skills/spawn/spawn.py`, `skills/spawn/pool.py`
- `.planning/PROJECT.md` — v2.0 feature requirements and key decisions

---
*Architecture research for: OpenClaw v2.0 Structural Intelligence*
*Researched: 2026-03-03*
