# Phase 61: Topology Foundation - Context

**Gathered:** 2026-03-03
**Updated:** 2026-03-04
**Status:** Ready for planning (post-implementation sync)

<domain>
## Phase Boundary

Represent, serialize, version, diff, and classify swarm topologies as explicit data objects stored in their own isolated files. This is the data substrate — no proposal engine, no correction system, no observability UI. Pure data model + operations.

</domain>

<decisions>
## Implementation Decisions

### Graph Model (Locked — built in Phase 62-01)
- `@dataclass` models (not Pydantic) — consistent with `AgentSpec` pattern
- `TopologyNode`: id, role (str), level (int 1-3), intent (str), risk_level (str), optional resource_constraints (dict), optional estimated_load (float)
- `TopologyEdge`: from_role, to_role, edge_type (EdgeType enum). Five edge types: DELEGATION, COORDINATION, REVIEW_GATE, INFORMATION_FLOW, ESCALATION
- `TopologyGraph`: nodes (list), edges (list), project_id, proposal_id (optional), version (int), created_at (ISO timestamp), metadata (dict)
- `EdgeType` serializes as lowercase string value (e.g., `"delegation"`) not enum name — human-readable JSON
- Aggregate metrics (complexity, coordination overhead, cost) computed on demand by rubric — NOT cached on the topology object
- Full `to_dict()`/`from_dict()` and `to_json()`/`from_json()` serialization with zero data loss on round-trip

### Archetype Classification (Locked — built in Phase 62-02)
- Pattern-matching classifier using feature extraction, not hard thresholds
- **Robust**: Requires `review_gate` AND (`escalation` edges OR multiple coordination paths). Confidence 0.6–0.9 based on feature count
- **Lean**: No coordination/review edges AND (linear chain OR flat delegation). Confidence 0.8–0.9
- **Balanced**: Explicit catch-all fallback — has coordination or review gates but doesn't meet Robust threshold. Confidence 0.6–0.8. Classification is always exhaustive
- `ArchetypeResult`: archetype string, confidence float (0.0–1.0), explanation (always non-empty), traits list
- Trait annotations: "linear-chain", "flat-delegation", "review-heavy", "fallback-roles", "redundant-paths", "coordination-linked", "review-gated"
- Edge cases: assign nearest archetype with explanation of why and what's atypical. Always classify, always explain

### Diff Engine (Locked — built in Phase 62-02)
- Edges matched by endpoint pair `(from_role, to_role)` — changing edge_type on the same pair is a modification, not add+remove
- `TopologyDiff` dataclass: added/removed/modified nodes and edges as structured dicts
- Tracks modified node fields (level, intent, risk_level, resource_constraints, estimated_load)
- Human-readable `format_diff()` for terminal output
- `annotations` dict field designed for Phase 64 structural memory enrichment

### Rubric Scoring (Locked — built in Phase 62-03)
- 7-dimension `RubricScore`: complexity, coordination_overhead, risk_containment, time_to_first_output, cost_estimate, preference_fit, overall_confidence (all integer 0–10)
- Dimension weights (sum to 1.0): risk_containment 0.20, time_to_first_output 0.20, preference_fit 0.20, complexity 0.15, coordination_overhead 0.15, cost_estimate 0.10
- `key_differentiators`: dimensions with ≥3 score spread across proposals
- Phase 64 integration: preference_fit dynamically scored via archetype affinity profiles. Explore mode (20% epsilon-greedy) defaults preference_fit to neutral 5

### Version & Diff Storage (Locked — built across Phases 62-64)
- Five-file storage under `workspace/.openclaw/{project_id}/topology/`:
  - `current.json` — Latest approved topology snapshot (atomic write with .bak backup)
  - `changelog.json` — Append-only diff entries (with .lock file for consistency)
  - `pending-proposals.json` — Proposal data awaiting approval (deleted after approval)
  - `memory-profile.json` — Phase 64 correction history profile (with defaults)
  - `patterns.json` — Phase 64 extracted structural patterns
- Changelog entries: timestamp (ISO 8601), correction_type ("soft"|"hard"|"initial"), diff_dict, annotations (mutable, enriched by Phase 64)
- Retention: decay-aligned — keep all entries, no pruning. 14-day preference decay in Phase 64 handles relevance

### Relationship to AgentSpec
- Topology is an independent data model — NOT an extension of AgentSpec. Clean separation of design-time (topology) and runtime (AgentSpec)
- At spawn time, a mapper converts topology nodes to AgentSpec instances. Topology is the blueprint; AgentSpec is the execution config
- Topology metadata (intent, risk, coordination partners) injected into SOUL templates via `_build_augmented_soul()`. Agents are structurally self-aware at runtime
- AgentSpec stays unchanged — no new fields added to the runtime model
- Dual validation: constraint linter at proposal time (Phase 62), mapper validates again before spawn

### Claude's Discretion (Resolved)
- ~~Exact Pydantic model field names and types~~ → Locked: @dataclass with fields documented above
- ~~JSON serialization format details~~ → Locked: to_dict/from_dict pattern with EdgeType as lowercase string
- ~~Diff algorithm implementation~~ → Locked: custom diff matching edges by endpoint pair
- ~~File locking strategy~~ → Locked: fcntl.flock pattern from state_engine.py with .tmp atomic rename and .bak recovery
- ~~Test structure~~ → Locked: test_topology_models.py, test_topology_diff.py, test_topology_classifier.py

</decisions>

<specifics>
## Specific Ideas

- Topology should feel like a DAG you can inspect, not a config blob — inspectable, navigable, meaningful
- The archetype classifier gives reasoning, not just labels — "Classified as Robust because DAG structure with 3 review gates; atypical because no fallback roles"
- Changelog annotations are explicitly designed to be enriched by Phase 64 structural memory — the annotation field is extensible

</specifics>

<code_context>
## Existing Code — Topology Package

### Module Inventory (`packages/orchestration/src/openclaw/topology/`)
| Module | Role |
|--------|------|
| `models.py` | Core data models: TopologyNode, TopologyEdge, TopologyGraph, EdgeType |
| `diff.py` | TopologyDiff dataclass, topology_diff() comparator, format_diff() renderer |
| `classifier.py` | ArchetypeClassifier with pattern matching, ArchetypeResult, feature extraction |
| `storage.py` | File I/O with fcntl locking, atomic writes, .bak recovery. Manages all 5 topology files |
| `proposal_models.py` | RubricScore, TopologyProposal, ProposalSet dataclasses |
| `proposer.py` | LLM-driven proposal generation, build_proposals(), ask_clarifications() |
| `rubric.py` | RubricScorer class, score_proposal() wrapper, weighted dimension scoring |
| `linter.py` | ConstraintLinter: AgentRegistry + pool limit validation, auto-constrain strategy |
| `correction.py` | CorrectionSession: soft re-proposal + hard draft edit cycles |
| `approval.py` | approve_topology(), compute_pushback_note(), check_approval_gate() |
| `renderer.py` | ASCII DAG, comparative matrix, diff summary, justifications, confidence warnings |
| `llm_client.py` | Provider-configurable LLM calls (Anthropic/OpenAI/Gemini) |
| `memory.py` | Phase 64: MemoryProfiler (decay-weighted affinity), PatternExtractor (LLM pattern mining) |
| `__init__.py` | Public API exports |

### Tests (`packages/orchestration/tests/`)
- `test_topology_models.py` — Serialization round-trips, EdgeType values, optional fields
- `test_topology_diff.py` — Node/edge addition/removal/modification, summary generation
- `test_topology_classifier.py` — Archetype classification, pattern matching, confidence ranges

### Cross-Cutting Integration Points
- **SOUL injection**: `_build_augmented_soul()` in `spawn.py` receives topology context as template variables
- **Event bus**: `EventDomain.TOPOLOGY` with topology-specific event types in `events/protocol.py`
- **Approval gate**: `check_approval_gate()` guards downstream operations requiring approved topology
- **Memory isolation**: `category="structural_topology"` exclusion in `CATEGORY_SECTION_MAP` prevents L3 SOUL contamination
- **Autonomy hooks**: Approval gate integrated into autonomy framework execution path

### Established Patterns (Followed)
- `@dataclass` models consistent with AgentSpec, JarvisState
- JSON file storage with fcntl.flock() locking and .bak backup recovery
- Project-scoped state under `workspace/.openclaw/{project_id}/topology/`
- .tmp + atomic rename for crash safety

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 61-topology-foundation*
*Context gathered: 2026-03-03, updated: 2026-03-04*
