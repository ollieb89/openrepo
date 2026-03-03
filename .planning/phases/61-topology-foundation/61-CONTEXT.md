# Phase 61: Topology Foundation - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Represent, serialize, version, diff, and classify swarm topologies as explicit data objects stored in their own isolated files. This is the data substrate — no proposal engine, no correction system, no observability UI. Pure data model + operations.

</domain>

<decisions>
## Implementation Decisions

### Graph Model Scope
- Rich edge types: delegation, coordination, review gate, information flow, escalation. Each edge is typed with semantics.
- Topology is a true graph (DAG), not a tree. Peer-to-peer edges (coordination) exist alongside vertical edges (delegation).
- Medium-weight nodes: role name, expected capability, resource constraints (mem/cpu), intent description (what this role does), risk level (what happens if it fails), estimated load.
- Aggregate metrics (complexity, coordination overhead, cost) computed on demand by rubric — NOT cached on the topology object.
- Topology carries a `proposal_id` field linking back to its proposal context. Structure is clean; context is traceable via reference.

### Archetype Classification
- Pattern-matching classifier, not hard thresholds. Classifies by structural shape.
- Lean: Linear chain or flat delegation. Minimal coordination edges. No review gates. Fast, direct.
- Balanced: Tree with explicit coordination edges. Has review or escalation edges. Moderate role specialization.
- Robust: DAG with multiple coordination paths. Review gates, fallback roles, redundancy. Safety over speed.
- Primary archetype + trait annotations (e.g., "Balanced with review-heavy coordination").
- Edge cases: assign nearest archetype with explanation of why it was classified that way and what's atypical. Always classify, always explain.

### Version & Diff Format
- Two-file storage: `topology/current.json` (latest approved version) + `topology/changelog.json` (array of diff entries).
- Diff entries have layered structure: immutable structural delta (nodes/edges added/removed/modified) + mutable annotation field (for structural memory to enrich later with pattern tags, preference signals).
- Diff metadata: correction type (soft/hard/initial), timestamp, version number. Structural memory enriches annotations in Phase 64.
- Retention: decay-aligned — keep all entries, no pruning. The 14-day preference decay in Phase 64 handles relevance naturally.

### Relationship to AgentSpec
- Topology is an independent data model — NOT an extension of AgentSpec. Clean separation of design-time (topology) and runtime (AgentSpec).
- At spawn time, a mapper converts topology nodes to AgentSpec instances. Topology is the blueprint; AgentSpec is the execution config.
- Topology metadata (intent, risk, coordination partners) that AgentSpec doesn't carry gets injected into SOUL templates. Agents are structurally self-aware at runtime.
- AgentSpec stays unchanged — no new fields added to the runtime model.
- Dual validation gates: constraint linter validates at proposal time (Phase 62), mapper validates again before spawn. Direct edits bypass the proposal linter, so the mapper catches what they introduce.

### Claude's Discretion
- Exact Pydantic model field names and types
- JSON serialization format details
- Diff algorithm implementation (deepdiff or custom)
- File locking strategy for topology directory (can follow state_engine.py fcntl pattern)
- Test structure and coverage approach

</decisions>

<specifics>
## Specific Ideas

- Topology should feel like a DAG you can inspect, not a config blob — inspectable, navigable, meaningful.
- The archetype classifier should give reasoning, not just labels — "Classified as Robust because DAG structure with 3 review gates; atypical because no fallback roles."
- Changelog annotations are explicitly designed to be enriched by Phase 64 structural memory — build the annotation field extensibly.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AgentSpec` dataclass (agent_registry.py): Canonical agent definition with hierarchy fields (reports_to, subordinates, level, role). The mapper will produce these.
- `AgentRegistry.get_hierarchy()` / `get_subordinates()`: Existing hierarchy walking — topology graph operations will be the richer version of these.
- State engine fcntl.flock pattern (state_engine.py): Proven file locking for concurrent access. Topology files should follow the same discipline.
- `CATEGORY_SECTION_MAP` in spawn.py: Memory category routing. Phase 64 will need a `structural_topology` exclusion here.
- `EventDomain` / `EventType` enums (events/protocol.py): Will need `TOPOLOGY` domain and topology-specific event types.

### Established Patterns
- Pydantic/dataclass models for data objects (AgentSpec, JarvisState)
- JSON file storage with fcntl locking and .bak backup recovery
- Project-scoped state files under `workspace/.openclaw/{project_id}/`
- mtime-based caching for read-heavy state files

### Integration Points
- Topology files stored at `workspace/.openclaw/{project_id}/topology/` — parallel to existing state file location
- Mapper output feeds into `spawn_l3_specialist()` via AgentSpec instances
- SOUL injection path: `_build_augmented_soul()` in spawn.py can receive topology context as additional variables
- Event bus: topology events emitted through existing `EventBus` infrastructure

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 61-topology-foundation*
*Context gathered: 2026-03-03*
