# Phase 61: Topology Foundation - Research

**Researched:** 2026-03-04
**Domain:** Python dataclass topology data model, JSON serialization, structural diff, archetype classification, fcntl-based file storage
**Confidence:** HIGH

## Summary

Phase 61 represents the topology data substrate for the v2.0 Structural Intelligence milestone. The goal is to represent, serialize, version, diff, and classify swarm topologies as explicit data objects stored in their own isolated files. This is the pure data model layer — no LLM proposal engine, no correction system, no dashboard.

Critically, all six TOPO-XX requirements have already been implemented as part of the work done in Phases 62-65. The code lives under `packages/orchestration/src/openclaw/topology/` and has full test coverage in `packages/orchestration/tests/test_topology_models.py`, `test_topology_diff.py`, and `test_topology_classifier.py`. All 55 tests pass. This means Phase 61 planning must focus on verifying, organizing, and formally validating the existing implementation rather than building net-new code.

The implementation follows established project patterns: `@dataclass` models (not Pydantic, consistent with `AgentSpec`), JSON file storage at `workspace/.openclaw/{project_id}/topology/`, fcntl-based locking (LOCK_EX writes, LOCK_SH reads), `.tmp`+rename atomic writes, `.bak` backup-and-recovery, and strict separation from `workspace-state.json` to avoid L3 flock contention.

**Primary recommendation:** Phase 61 plans should verify existing code satisfies each TOPO requirement explicitly, confirm file isolation invariant holds, and run the full test suite as the gate. No new modules need to be written.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Graph Model Scope**
- Rich edge types: delegation, coordination, review gate, information flow, escalation. Each edge is typed with semantics.
- Topology is a true graph (DAG), not a tree. Peer-to-peer edges (coordination) exist alongside vertical edges (delegation).
- Medium-weight nodes: role name, expected capability, resource constraints (mem/cpu), intent description (what this role does), risk level (what happens if it fails), estimated load.
- Aggregate metrics (complexity, coordination overhead, cost) computed on demand by rubric — NOT cached on the topology object.
- Topology carries a `proposal_id` field linking back to its proposal context. Structure is clean; context is traceable via reference.

**Archetype Classification**
- Pattern-matching classifier, not hard thresholds. Classifies by structural shape.
- Lean: Linear chain or flat delegation. Minimal coordination edges. No review gates. Fast, direct.
- Balanced: Tree with explicit coordination edges. Has review or escalation edges. Moderate role specialization.
- Robust: DAG with multiple coordination paths. Review gates, fallback roles, redundancy. Safety over speed.
- Primary archetype + trait annotations (e.g., "Balanced with review-heavy coordination").
- Edge cases: assign nearest archetype with explanation of why it was classified that way and what's atypical. Always classify, always explain.

**Version and Diff Format**
- Two-file storage: `topology/current.json` (latest approved version) + `topology/changelog.json` (array of diff entries).
- Diff entries have layered structure: immutable structural delta (nodes/edges added/removed/modified) + mutable annotation field (for structural memory to enrich later with pattern tags, preference signals).
- Diff metadata: correction type (soft/hard/initial), timestamp, version number. Structural memory enriches annotations in Phase 64.
- Retention: decay-aligned — keep all entries, no pruning. The 14-day preference decay in Phase 64 handles relevance naturally.

**Relationship to AgentSpec**
- Topology is an independent data model — NOT an extension of AgentSpec. Clean separation of design-time (topology) and runtime (AgentSpec).
- At spawn time, a mapper converts topology nodes to AgentSpec instances. Topology is the blueprint; AgentSpec is the execution config.
- Topology metadata (intent, risk, coordination partners) that AgentSpec doesn't carry gets injected into SOUL templates. Agents are structurally self-aware at runtime.
- AgentSpec stays unchanged — no new fields added to the runtime model.
- Dual validation gates: constraint linter validates at proposal time (Phase 62), mapper validates again before spawn.

### Claude's Discretion
- Exact Pydantic model field names and types
- JSON serialization format details
- Diff algorithm implementation (deepdiff or custom)
- File locking strategy for topology directory (can follow state_engine.py fcntl pattern)
- Test structure and coverage approach

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOPO-01 | System represents swarm topology as an explicit graph object with nodes (roles) and edges (delegation/coordination relationships) | `TopologyGraph`, `TopologyNode`, `TopologyEdge`, `EdgeType` in `topology/models.py` — fully implemented |
| TOPO-02 | User can serialize a topology to JSON and deserialize it back without data loss | `to_json()`/`from_json()` on `TopologyGraph` — round-trip equality tested in `test_topology_models.py` |
| TOPO-03 | System tracks topology versions with timestamps and associates each version with a project | `version` and `created_at` fields on `TopologyGraph`; `project_id` scoping — implemented and tested |
| TOPO-04 | System can compute a structural diff between two topology versions showing added/removed/modified nodes and edges | `topology_diff()` and `format_diff()` in `topology/diff.py` — 21 tests green |
| TOPO-05 | System classifies each topology into an archetype (Lean/Balanced/Robust) based on role count, hierarchy depth, and coordination patterns | `ArchetypeClassifier.classify()` in `topology/classifier.py` — 19 tests green, deterministic |
| TOPO-06 | Topology data is stored in a separate file from workspace-state.json to avoid lock contention with L3 execution | `topology/storage.py` writes to `workspace/.openclaw/{project_id}/topology/` — separate from `workspace-state.json` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | Topology model definitions | Consistent with `AgentSpec` pattern in `agent_registry.py`; no Pydantic dependency needed |
| fcntl | stdlib | File locking for topology reads/writes | Proven pattern from `state_engine.py` (JarvisState); POSIX-standard for Linux containers |
| json | stdlib | Serialization of topology graphs to/from disk | All existing state files use stdlib json; human-readable, no binary format needed |
| pathlib | stdlib | File path manipulation | Used throughout the codebase |
| pytest | 7.x | Test runner | Already configured via `packages/orchestration/pyproject.toml` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shutil | stdlib | `.bak` file creation (shutil.copy2) | Before overwriting `current.json`; follows `state_engine.py` pattern |
| enum | stdlib | `EdgeType` enum with 5 string values | Human-readable JSON serialization ("delegation" not "EdgeType.DELEGATION") |
| datetime | stdlib | ISO 8601 timestamps for `created_at` | `datetime.now(timezone.utc).isoformat()` in `__post_init__` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib @dataclass | Pydantic | Pydantic has built-in validation but adds dependency; project decision is @dataclass for consistency with AgentSpec |
| Custom diff algorithm | deepdiff library | deepdiff handles arbitrary dicts but is an external dependency; custom diff is simpler for the bounded schema |
| fcntl direct | portalocker | portalocker is cross-platform but adds a dependency; fcntl is proven and sufficient on Linux |

**Installation:** No new dependencies required. All stdlib.

## Architecture Patterns

### Recommended Project Structure
```
packages/orchestration/src/openclaw/topology/
├── __init__.py          # Public API exports
├── models.py            # EdgeType, TopologyNode, TopologyEdge, TopologyGraph
├── diff.py              # TopologyDiff, topology_diff(), format_diff()
├── classifier.py        # ArchetypeClassifier, ArchetypeResult
├── storage.py           # save_topology(), load_topology(), append_changelog(), load_changelog()
├── proposal_models.py   # RubricScore, TopologyProposal, ProposalSet (Phase 62)
├── rubric.py            # RubricScorer (Phase 62)
├── linter.py            # ConstraintLinter (Phase 62)
├── renderer.py          # render_dag(), render_full_output() (Phase 62)
├── proposer.py          # LLM topology proposal generation (Phase 62)
├── correction.py        # CorrectionSession (Phase 63)
├── approval.py          # Approval gate (Phase 63)
└── memory.py            # MemoryProfiler (Phase 64)
```

**Data storage layout (per project):**
```
workspace/.openclaw/{project_id}/topology/
├── current.json              # Latest approved topology (TopologyGraph.to_json())
├── current.json.bak          # Previous version (crash recovery)
├── current.json.tmp          # Atomic write staging (transient)
├── changelog.json            # Array of diff entries (append-only)
├── changelog.json.tmp        # Atomic changelog write staging (transient)
├── changelog.json.lock       # Dedicated lock file for changelog RMW
├── pending-proposals.json    # In-flight proposals (Phase 62)
├── memory-profile.json       # Archetype affinity profile (Phase 64)
└── patterns.json             # Extracted structural patterns (Phase 64)
```

### Pattern 1: Dataclass with to_dict/from_dict

**What:** Each topology model implements `to_dict()` (returns plain dict for JSON encoding) and `from_dict(cls, data)` (deserializes from dict). Top-level `TopologyGraph` adds `to_json()` and `from_json()` convenience wrappers.

**When to use:** All topology model serialization — both for disk persistence and for changelog diff entries.

**Example:**
```python
# Source: packages/orchestration/src/openclaw/topology/models.py
@dataclass
class TopologyGraph:
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]
    project_id: str
    proposal_id: Optional[str] = None
    version: int = 1
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "version": self.version,
            "created_at": self.created_at,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            ...
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
```

### Pattern 2: Atomic Write with fcntl + .tmp rename

**What:** Write to `.tmp` file under `LOCK_EX`, flush, release lock, then `rename()` to target. Rename is atomic on POSIX. Back up existing file to `.bak` before overwrite.

**When to use:** All topology file writes (`save_topology`, `save_pending_proposals`, `save_memory_profile`, `save_patterns`).

**Example:**
```python
# Source: packages/orchestration/src/openclaw/topology/storage.py
def save_topology(project_id: str, graph: TopologyGraph) -> None:
    topo_dir = _topology_dir(project_id)
    current_path = topo_dir / "current.json"
    tmp_path = topo_dir / "current.json.tmp"
    bak_path = topo_dir / "current.json.bak"

    if current_path.exists():
        shutil.copy2(str(current_path), str(bak_path))

    with open(tmp_path, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(graph.to_json())
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    tmp_path.rename(current_path)
```

### Pattern 3: Changelog Append via Dedicated Lock File

**What:** `changelog.json` uses a separate `.lock` sidecar file for the read-modify-write cycle. This allows the changelog to be extended without holding a lock on the data file itself.

**When to use:** `append_changelog()` only.

**Example:**
```python
# Source: packages/orchestration/src/openclaw/topology/storage.py
def append_changelog(project_id: str, entry: dict) -> None:
    topo_dir = _topology_dir(project_id)
    changelog_path = topo_dir / "changelog.json"
    tmp_path = topo_dir / "changelog.json.tmp"

    with open(str(changelog_path) + ".lock", "w", encoding="utf-8") as lock_f:
        fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
        try:
            entries = json.load(open(changelog_path)) if changelog_path.exists() else []
            entries.append(entry)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
            tmp_path.rename(changelog_path)
        finally:
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
```

### Pattern 4: Pattern-Matching Archetype Classifier

**What:** `ArchetypeClassifier.classify()` first extracts structural features (edge type counts, max delegation depth, multiple-coordination-path detection), then applies priority-ordered pattern rules (Robust > Lean > Balanced as explicit catch-all). Returns `ArchetypeResult` with archetype string, confidence float, explanation string, and trait list.

**When to use:** Any time a topology needs to be labeled (proposal generation, correction analysis, storage).

**Anti-Patterns to Avoid**
- **Caching aggregate metrics on TopologyGraph:** Aggregate metrics (complexity score, coordination overhead, cost estimate) must be computed on demand by the rubric. Never add them as fields on `TopologyGraph` — this was an explicit design decision.
- **Mixing topology storage with workspace-state.json:** The topology directory is strictly separate from the workspace state file. Never write topology data through `JarvisState`. This is the TOPO-06 invariant.
- **Using Pydantic for topology models:** The project decision is `@dataclass` for consistency with `AgentSpec`. Pydantic would add a dependency and break the pattern.
- **EdgeType.value vs EdgeType.name:** EdgeType serializes as its `.value` (e.g., `"delegation"`) not its `.name` (`"DELEGATION"`). The `from_dict` constructor passes the string through `EdgeType(data["edge_type"])` which requires the value form.
- **Matching edges by (from_role, to_role, edge_type) triplet for diff:** Edges are matched by endpoint pair `(from_role, to_role)` only. A change in `edge_type` on the same endpoint pair is a modification, not an add+remove. This is the CONTEXT decision from Phase 62.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file write | Custom write-then-rename logic | The established `.tmp`+rename pattern from storage.py | Already tested, handles crash safety and concurrent writes |
| Backup recovery | Custom .bak management | `shutil.copy2()` + pattern from storage.py | Mirrors state_engine.py exactly; consistent recovery behavior |
| File locking | Custom retry loop | `fcntl.flock(LOCK_EX)` with `.lock` sidecar for changelog | Proven in state_engine.py; POSIX correct |
| Topology serialization | Hand-crafted JSON dict | `to_dict()`/`from_dict()` on each model class | Already zero-loss round-trip verified in 55 tests |

**Key insight:** The topology package already provides the complete set of primitives needed for Phase 61. The planning work is verification and integration, not construction.

## Common Pitfalls

### Pitfall 1: Assuming Phase 61 Requires Net-New Code

**What goes wrong:** A plan creates tasks to implement models, diff engine, storage, and classifier from scratch — but all of this exists already in `packages/orchestration/src/openclaw/topology/`.

**Why it happens:** Phase 61 is listed as a foundation phase with no "depends on" entries in STATE.md, giving the impression it hasn't been built yet.

**How to avoid:** Read the existing code first. The implementation was done forward (Phases 62-65 were executed before Phase 61 was formally planned). Plans should audit and validate existing code against requirements, not rebuild.

**Warning signs:** Any task description saying "create topology/models.py" or "implement TopologyNode" — these files already exist.

### Pitfall 2: TOPO-06 Isolation Regression

**What goes wrong:** A future refactor accidentally routes topology reads/writes through `JarvisState.read_state()` or `update_task()`, causing flock contention with L3 containers.

**Why it happens:** `JarvisState` is the dominant state management pattern in the codebase, so it's tempting to extend it.

**How to avoid:** Topology operations use `topology/storage.py` exclusively. The flock scope for `workspace-state.json` must never expand to include topology files. Each topology file has its own lock context.

**Warning signs:** Any import of `JarvisState` in `topology/storage.py`, or any `topology/` path appearing inside a `JarvisState` context manager.

### Pitfall 3: EdgeType Serialization Inconsistency

**What goes wrong:** New code serializes `EdgeType` using `.name` (e.g., `"DELEGATION"`) instead of `.value` (e.g., `"delegation"`), causing `from_dict` deserialization to fail with `ValueError`.

**Why it happens:** Python enums have both `.name` and `.value`; using the wrong one produces human-readable but undeserializable output.

**How to avoid:** Always use `edge_type.value` in `to_dict()`. Always reconstruct with `EdgeType(data["edge_type"])` in `from_dict()`. Existing code does this correctly — never change this pattern.

### Pitfall 4: Changelog as Mutable Data

**What goes wrong:** A plan treats changelog entries as mutable and edits existing entries (e.g., to add timestamps or fix fields after the fact), breaking the append-only invariant.

**Why it happens:** The annotation field on diff entries is explicitly designed to be enriched by Phase 64 — this looks like mutation.

**How to avoid:** Phase 64 enrichment adds to the `annotations` subfield only. The structural delta fields (`added_nodes`, `removed_nodes`, etc.) are immutable after appending. The changelog array itself is append-only.

## Code Examples

Verified patterns from existing code:

### Constructing a Full Topology Graph
```python
# Source: packages/orchestration/tests/test_topology_models.py
from openclaw.topology.models import TopologyGraph, TopologyNode, TopologyEdge, EdgeType

nodes = [
    TopologyNode(id="l1", level=1, intent="Strategic orchestration", risk_level="high"),
    TopologyNode(id="l2", level=2, intent="Manage tasks", risk_level="medium"),
    TopologyNode(id="l3", level=3, intent="Execute code", risk_level="low",
                 resource_constraints={"mem": "4g", "cpu": 1}, estimated_load=0.8),
]
edges = [
    TopologyEdge("l1", "l2", EdgeType.DELEGATION),
    TopologyEdge("l1", "l2", EdgeType.COORDINATION),
    TopologyEdge("l2", "l3", EdgeType.REVIEW_GATE),
    TopologyEdge("l2", "l1", EdgeType.ESCALATION),
]
graph = TopologyGraph(
    nodes=nodes, edges=edges,
    project_id="pumplai", proposal_id="prop-001", version=1,
    metadata={"source": "proposal-engine"},
)
# Round-trip with zero data loss
assert TopologyGraph.from_dict(graph.to_dict()).to_dict() == graph.to_dict()
```

### Computing and Rendering a Diff
```python
# Source: packages/orchestration/src/openclaw/topology/diff.py
from openclaw.topology.diff import topology_diff, format_diff

diff = topology_diff(old_graph, new_graph)
print(format_diff(diff))
# Output:
# ADDED NODES
#   + new-agent (level=2, intent=..., risk=low)
# REMOVED EDGES
#   - orchestrator -> worker (delegation)

# Serialize for changelog:
entry = {
    "version": new_graph.version,
    "timestamp": new_graph.created_at,
    "correction_type": "hard",
    "structural_delta": diff.to_dict(),
}
```

### Classifying a Topology
```python
# Source: packages/orchestration/src/openclaw/topology/classifier.py
from openclaw.topology.classifier import ArchetypeClassifier

classifier = ArchetypeClassifier()
result = classifier.classify(graph)
# result.archetype: "lean" | "balanced" | "robust"
# result.confidence: 0.0 - 1.0
# result.explanation: "Classified as robust because review gate present, 2 escalation path(s)."
# result.traits: ["fallback-roles", "review-heavy"]
```

### Saving and Loading Topology Files
```python
# Source: packages/orchestration/src/openclaw/topology/storage.py
import os
os.environ["OPENCLAW_ROOT"] = "/path/to/openclaw"

from openclaw.topology.storage import save_topology, load_topology, append_changelog, load_changelog

save_topology("pumplai", graph)
loaded = load_topology("pumplai")
assert loaded.to_dict() == graph.to_dict()

append_changelog("pumplai", {"version": 2, "correction_type": "soft", "structural_delta": diff.to_dict()})
entries = load_changelog("pumplai")  # list of dicts
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Topology as part of AgentSpec | Independent TopologyGraph data model | Phase 62 decision | Clean design/runtime separation; AgentSpec unchanged |
| Tree-only hierarchy | True DAG with typed edges | Phase 61 CONTEXT | Supports peer-to-peer coordination, review gates, escalation paths |
| Hard classification thresholds | Pattern-matching with structural features | Phase 61 CONTEXT | Classification adapts naturally to graph size; consistent for edge cases |
| Single state file (workspace-state.json) | Separate topology/ directory | Phase 61/TOPO-06 | Eliminates flock contention between topology ops and L3 execution |

**Already implemented (no longer "state of the art" questions):**
- Topology models with all 5 edge types: DONE
- JSON round-trip serialization: DONE, tested
- Two-file storage (current.json + changelog.json): DONE
- Structural diff engine: DONE, 21 tests
- Archetype classifier: DONE, 19 tests, deterministic

## Open Questions

1. **Role name field on TopologyNode**
   - What we know: `TopologyNode` has `id` (used as role identifier) and `intent` (free-text description of what the role does). The CONTEXT mentions "role name" as a node field.
   - What's unclear: The distinction between `id` (machine identifier, e.g., `"pumplai_pm"`) and a human-facing "role name" (e.g., `"Project Manager"`) — are these the same field or separate?
   - Recommendation: The current `id` field serves as both identifier and role name. If the planner determines a separate `role_name` field is needed, it can be added without breaking the round-trip (add to `to_dict`/`from_dict` with a default). Given all downstream phases (62-65) already use the existing model, keep as-is unless a concrete downstream requirement surfaces.

2. **Expected capability field**
   - What we know: CONTEXT mentions "expected capability" as a node field, but `TopologyNode` has `intent` (what the role does) rather than a discrete `expected_capability`.
   - What's unclear: Whether `intent` is sufficient or if a separate structured field is needed for constraint linting.
   - Recommendation: `intent` covers the use case in practice (Phase 62 linter uses it this way). No change needed.

3. **Topology directory path when `workspace` subdirectory is absent**
   - What we know: `_topology_dir()` in `storage.py` calls `get_project_root() / "workspace" / ".openclaw" / project_id / "topology"` with `mkdir(parents=True, exist_ok=True)`.
   - What's unclear: Whether bare environments (no workspace subdirectory) need a different path resolution.
   - Recommendation: `mkdir(parents=True)` handles this automatically. Not a real gap.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (via `uv run pytest`) |
| Config file | `packages/orchestration/pyproject.toml` |
| Quick run command | `uv run pytest packages/orchestration/tests/test_topology_models.py packages/orchestration/tests/test_topology_diff.py packages/orchestration/tests/test_topology_classifier.py -v` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOPO-01 | TopologyGraph with nodes and edges | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "test_graph_with_all_edge_types" -x` | Yes |
| TOPO-02 | JSON round-trip serialization | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "roundtrip" -x` | Yes |
| TOPO-03 | Version and timestamp tracking | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "created_at or version" -x` | Yes |
| TOPO-04 | Structural diff engine | unit | `uv run pytest packages/orchestration/tests/test_topology_diff.py -x` | Yes |
| TOPO-05 | Archetype classification | unit | `uv run pytest packages/orchestration/tests/test_topology_classifier.py -x` | Yes |
| TOPO-06 | Topology dir isolation from workspace-state.json | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "topology_dir" -x` | Yes |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/orchestration/tests/test_topology_models.py packages/orchestration/tests/test_topology_diff.py packages/orchestration/tests/test_topology_classifier.py -v`
- **Per wave merge:** `uv run pytest packages/orchestration/tests/ -v`
- **Phase gate:** All 55 topology tests green before `/gsd:verify-work`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. 55 tests exist and pass as of 2026-03-04.

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `packages/orchestration/src/openclaw/topology/models.py` — TopologyGraph, TopologyNode, TopologyEdge, EdgeType implementations
- Direct code inspection: `packages/orchestration/src/openclaw/topology/diff.py` — topology_diff(), format_diff(), TopologyDiff
- Direct code inspection: `packages/orchestration/src/openclaw/topology/classifier.py` — ArchetypeClassifier, ArchetypeResult, pattern-matching rules
- Direct code inspection: `packages/orchestration/src/openclaw/topology/storage.py` — save_topology(), load_topology(), append_changelog(), load_changelog()
- Direct code inspection: `packages/orchestration/src/openclaw/topology/__init__.py` — full public API surface
- Direct code inspection: `packages/orchestration/src/openclaw/state_engine.py` — fcntl pattern baseline
- Test verification: `uv run pytest` — 55 tests pass as of 2026-03-04

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — Accumulated decisions from Phases 62-65 clarifying model decisions (EdgeType string values, edge matching by endpoint pair, Balanced as explicit catch-all)
- `.planning/REQUIREMENTS.md` — TOPO-01 through TOPO-06 definitions and traceability

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by reading all topology module source files
- Architecture: HIGH — verified by running 55 tests green, inspecting storage patterns
- Pitfalls: HIGH — derived from documented decisions in STATE.md and direct code inspection
- Test coverage: HIGH — test files exist and all pass

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable stdlib patterns; topology module unlikely to change without explicit phase work)
