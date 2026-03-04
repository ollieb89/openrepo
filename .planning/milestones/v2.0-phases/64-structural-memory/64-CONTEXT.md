# Phase 64: Structural Memory - Context

**Gathered:** 2026-03-03
**Status:** Ready for planning

<domain>
## Phase Boundary

The system accumulates correction history, extracts structural preferences, and uses them to improve future proposals — while keeping topology data completely isolated from L3 agent SOUL context. Includes correction storage enrichment, LLM-based pattern extraction, preference profiling with decay and exploration, L3 isolation enforcement, and a CLI reporting interface. Does NOT include dashboard visualization (Phase 65) or mid-flight adaptation (out of scope for v2.0).

</domain>

<decisions>
## Implementation Decisions

### L3 Isolation Mechanism
- Dual-layer enforcement: filter at memU query level (topology memories never returned for L3 queries) AND exclusion in spawn.py's CATEGORY_SECTION_MAP as defense-in-depth
- Three sub-typed memory categories for granular control: `structural_correction`, `structural_preference`, `structural_pattern` — all excluded from L3 retrieval
- If a structural memory somehow slips through to spawn layer: silent drop + log warning. Non-disruptive — L3 still spawns normally
- Verification: unit test that mocks spawn and asserts `_build_augmented_soul()` output contains zero topology content when structural memories exist. Fast, CI-friendly, no Docker required

### Pattern Extraction
- LLM-based analysis: feed correction diffs + context to LLM, extract recurring structural preferences (e.g., "user flattens hierarchies for low-complexity tasks")
- Trigger: threshold-triggered (every 5 corrections) AND on-demand via CLI command. Automatic updates plus manual refresh anytime
- Minimum data threshold: 5 corrections before pattern extraction is meaningful. Below this, system reports "not enough data yet"
- Storage: dedicated `topology/patterns.json` file per project as source of truth (array of patterns with timestamps, confidence, source correction IDs). Also tag changelog annotations with pattern IDs for traceability

### Preference Profile & Scoring
- preference_fit calculation: combined approach — archetype affinity as base score (which archetypes user approves vs corrects) + pattern match as modifier (structural feature alignment with extracted patterns)
- Decay: exponential decay with configurable lambda. Weight = e^(-λ * age_in_days). Phase 61's 14-day relevance window informs the default lambda
- Exploration: epsilon-greedy with configurable rate via `topology.exploration_rate` config key. Default 20% (matches success criteria). 20% of proposals randomize archetype ordering regardless of preferences
- Below minimum threshold (< 5 corrections): preference_fit stays at 5/10 neutral baseline (consistent with Phase 62). The report shows threshold status separately
- Profile stored in `topology/memory-profile.json` per project — current preference scores, archetype affinity distribution, active patterns

### Correction Storage & Reporting
- Storage architecture: topology files only — no memU REST API for structural data. Clean separation: memU is for L3 execution memory, topology directory is for structural memory
- Enrich existing changelog.json annotations (Phase 61 designed the mutable annotation field for this) AND maintain summary files:
  - `topology/memory-profile.json` — current preference profile, stats, threshold status
  - `topology/patterns.json` — extracted patterns with confidence and source references
  - `topology/changelog.json` — enriched annotations with pattern IDs and preference signals
- CLI: `openclaw-propose memory [--detail]` subcommand. Default shows compact summary (project, correction count soft/hard, profile status active/below threshold, top 3 patterns). `--detail` shows full breakdown (archetype distribution, decay-weighted timeline, pattern confidence scores, preference_fit breakdown)

### Claude's Discretion
- LLM prompt design for pattern extraction (what context to include, how to structure the extraction request)
- Exact exponential decay lambda default value
- Pattern confidence scoring algorithm
- memory-profile.json and patterns.json schema details
- Error handling for LLM failures during pattern extraction
- How enriched changelog annotations are structured internally

</decisions>

<specifics>
## Specific Ideas

- Structural memory should feel like the system is genuinely learning — not just counting. Patterns like "user flattens hierarchies for low-complexity tasks" should read as insights, not statistics
- The compact report should be immediately useful — a quick "is the system learning from my corrections?" check
- Topology files as the sole structural memory store keeps a clean conceptual boundary: memU = execution memory, topology/ = structural intelligence
- Pattern extraction threshold of 5 aligns naturally with the auto-trigger interval — every 5 corrections, run extraction

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CATEGORY_SECTION_MAP` in spawn.py (line 219): Memory category routing for L3 SOUL injection. Add structural_* categories as exclusions here for defense-in-depth
- `_format_memory_context()` in spawn.py (line 225): Memory formatting with budget cap. Second enforcement layer for isolation
- `TopologyDiff` dataclass (topology/diff.py): Has mutable `annotations` dict designed for Phase 64 enrichment
- `TopologyStorage` (topology/storage.py): fcntl-locked read/write for current.json and changelog.json. Extend for patterns.json and memory-profile.json
- `RubricScore.preference_fit` (topology/proposal_models.py): Currently hardcoded to 5. Phase 64 replaces with computed score
- `RubricScorer` (topology/rubric.py): Has preference_fit=5 placeholder at line 100-101. Hook point for dynamic scoring

### Established Patterns
- fcntl.flock for file operations (state_engine.py, topology/storage.py)
- Pydantic/dataclass models with to_dict/from_dict serialization
- Project-scoped files under `workspace/.openclaw/{project_id}/topology/`
- CLI commands as subcommands of existing tools (propose → propose memory)
- Config keys namespaced: `topology.exploration_rate`, `topology.decay_lambda`

### Integration Points
- `topology/changelog.json`: existing annotation field ready for pattern ID and preference signal enrichment
- `RubricScorer.score()` in rubric.py: replace hardcoded preference_fit=5 with dynamic calculation from memory-profile.json
- `spawn.py` CATEGORY_SECTION_MAP: add `structural_correction`, `structural_preference`, `structural_pattern` exclusions
- `openclaw-propose` CLI: add `memory` subcommand alongside existing propose flow
- Config: new keys `topology.exploration_rate`, `topology.decay_lambda`, `topology.pattern_extraction_threshold`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 64-structural-memory*
*Context gathered: 2026-03-03*
