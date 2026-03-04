# Phase 62: Structure Proposal Engine - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Given an outcome description, generate 2-3 scored topology proposals across Lean/Balanced/Robust archetypes using constraint-validated LLM output. Includes the proposal engine, constraint linter, rubric scoring, and CLI presentation. Does NOT include correction/feedback system (Phase 63), structural memory (Phase 64), or dashboard visualization (Phase 65).

</domain>

<decisions>
## Implementation Decisions

### Outcome Input Design
- Hybrid input: start with freeform text, engine asks 1-2 clarifying questions (risk tolerance, timeline pressure) before generating proposals
- Entry point: both CLI command (`openclaw propose`) and L1 directive. CLI is primary interface; L1 calls the same underlying engine
- Adaptive detail level: accept whatever the user gives. Minimal input → engine fills gaps with defaults and flags assumptions. Detailed input → engine respects all specifics
- Context-aware by default: read topology/changelog.json to avoid repeating rejected patterns. `--fresh` flag to generate without history influence

### Proposal Presentation
- Comparative matrix layout: side-by-side with rows = dimensions (roles, scores, risk), columns = archetypes. Highlights where proposals differ most. Full justification below the matrix
- Rank-ordered by overall confidence (highest first). Position implies preference without labeling one as "the" recommendation. Non-prescriptive
- ASCII DAG visualization for topology structure: roles as nodes, edges labeled by type (delegation, coordination, etc.). Visual and immediately readable in terminal
- Assumptions shown in shared section above proposals: one "Assumptions" block with common inferences shown once. Keeps proposals clean

### Constraint Linter Behavior
- Unknown agent roles: reject the invalid proposal variant and regenerate with valid roles only. Show what was rejected and why. User never sees invalid proposals
- Pool limit violations: auto-constrain — automatically adjust topology to fit within max_concurrent limits (reduce parallelism, sequence work). Note the constraint and show what changed
- Lint timing: after LLM generation. LLM generates freely with constraints as prompt guidance, linter validates and rejects/adjusts after. Simpler pipeline
- Retry limit: 2 retries max (3 total attempts). If all fail linting, show best-effort proposals with constraint violations highlighted. User decides

### Rubric Scoring Display
- Score format: 0-10 integers per dimension. Easy to compare at a glance. "Complexity: 3/10, Risk: 7/10"
- Emphasis: highlight the 2-3 dimensions where proposals differ most. Show all 7, but visually call out key differentiators
- Preference fit pre-Phase 64: default baseline of 5/10 (neutral) for all proposals with note "No correction history yet". Keeps rubric structure consistent. Phase 64 replaces with real scores
- Overall confidence: weighted average of 7 dimensions. Weights configurable in topology config. Transparent, reproducible, tunable
- Low confidence warning: visual warning on proposal if overall confidence < threshold. "Low confidence — consider simplifying the outcome or adding constraints." Non-blocking, informational

### Claude's Discretion
- LLM prompt engineering strategy (single prompt vs per-archetype)
- Exact clarifying questions in hybrid input flow
- ASCII DAG rendering algorithm
- Constraint injection format in LLM prompts
- Rubric dimension weight defaults
- Error handling for LLM API failures
- JSON schema for proposal output validation

</decisions>

<specifics>
## Specific Ideas

- The comparative matrix should feel like a decision table — not a wall of text. Key differentiators should jump out visually
- ASCII DAG should show the hierarchy clearly — think `tree` command but for agent topology, with edge type labels
- When the engine auto-constrains for pool limits, the change should be transparent — show "Adjusted: 4 parallel L3 → 3 (max_concurrent limit)" inline
- Context-aware mode should feel natural — if the user previously rejected a flat topology, the engine shouldn't propose essentially the same flat topology again

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AgentSpec` dataclass (agent_registry.py): Has `skill_registry`, `max_concurrent`, `role` fields — constraint linter reads these to validate proposals
- `AgentRegistry` (agent_registry.py): Registry loader that merges openclaw.json + agents/ directory. Provides the "available agent types" for constraint validation
- `ConfidenceScorer` protocol (autonomy/confidence.py): Existing 0.0-1.0 scoring pattern. Topology scoring uses 0-10 integers instead but the protocol pattern is reusable
- `ConfidenceFactors` dataclass (autonomy/confidence.py): Prior art for multi-factor scoring. Topology rubric is the richer version (7 dimensions)
- State engine fcntl.flock pattern (state_engine.py): For reading/writing topology files safely

### Established Patterns
- Pydantic/dataclass models for data objects (AgentSpec, JarvisState, ConfidenceFactors)
- JSON file storage with fcntl locking and .bak backup recovery
- Project-scoped state files under `workspace/.openclaw/{project_id}/`
- CLI commands follow `openclaw-{name}` pattern (openclaw-project, openclaw-monitor)
- Config keys namespaced by feature: `autonomy.confidence_threshold`, `memory.conflict_threshold`

### Integration Points
- Topology files at `workspace/.openclaw/{project_id}/topology/` (current.json, changelog.json) — from Phase 61
- Topology data model classes from Phase 61 (nodes, edges, archetype classifier)
- CLI entry point: new `openclaw-propose` command alongside existing CLI tools
- L1 routing: skills/router/index.js dispatches to new proposal skill
- Config: `topology.proposal_confidence_warning_threshold` key in openclaw.json
- Rubric dimension weights: `topology.rubric_weights` config key (new)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 62-structure-proposal-engine*
*Context gathered: 2026-03-03*
