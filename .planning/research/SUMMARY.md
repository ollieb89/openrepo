# Project Research Summary

**Project:** OpenClaw v2.0 — Structural Intelligence
**Domain:** AI Swarm Orchestration — pre-execution topology modeling, LLM-driven proposal, correction-as-learning
**Researched:** 2026-03-03
**Confidence:** HIGH

## Executive Summary

OpenClaw v2.0 adds a "Structural Intelligence" layer that sits between task receipt and L3 container spawn. Instead of implicitly spawning whatever containers seem appropriate, the system explicitly models, proposes, and gets human approval for the swarm topology before any containers run. The five capability areas — Topology as Data, Structure Proposal Engine, Dual Correction System, Structural Memory, Topology Observability — form a strict dependency chain: topology serialization is the foundation, the proposal engine consumes it, the correction system consumes the proposal engine, structural memory consumes corrections, and observability surfaces all of the above. Nothing in v2.0 ships usefully unless Topology as Data is solid first.

The recommended approach is a concrete-first build order: define a domain-specific Python dataclass (not a generic graph library abstraction) for the topology model, implement three fixed archetypes (Lean, Balanced, Robust) with deterministic constraint linting before any LLM is involved, then layer in LLM-based proposal generation using `instructor` for validated structured output. Dual correction paths (soft feedback to re-propose; hard edit to execute-then-analyze async) respect user authority while accumulating the learning signal needed for structural memory. The entire feature set integrates into existing infrastructure: `state_engine.py` flock patterns for file storage, `memory_client.py` and memU for structural preferences, `event_bus` for observability, and the dashboard's existing SSE and component patterns.

The two key risks are: (1) over-engineering the topology data model with generic graph abstractions creates an impedance mismatch at spawn time and inflates implementation cost dramatically — the fix is to start with a concrete dataclass and only generalize if a fourth archetype is actually needed; (2) structural memory stored in the wrong memU namespace (without explicit category exclusion) will contaminate L3 SOUL context injections and exhaust the 2000-character memory budget — this must be addressed before any structural data is written to memU. Both risks have clear prevention strategies and are phase-addressable.

---

## Key Findings

### Recommended Stack

The v2.0 stack is deliberately minimal — three net-new Python libraries and three net-new npm packages layered on top of the complete, unchanged v1.x baseline. On the Python side: `networkx>=3.6.1` provides DiGraph-based topology modeling with `node_link_data()` JSON round-trip that feeds the React Flow frontend directly; `deepdiff>=8.6.1` provides typed structural diff analysis with a `Delta` class for patch-then-analyze patterns in the correction system; and `instructor>=1.14.5` wraps Anthropic's tool_use to enforce a validated `RubricScore` Pydantic model on every proposal — eliminating JSON parsing failures in the critical pre-execution path. On the TypeScript side: `@xyflow/react>=12.10.1` (React 19 and Next.js 15 compatible) renders the agent topology DAG, `@dagrejs/dagre>=2.0.4` computes hierarchical layout, and `elkjs>=0.11.1` is loaded lazily only for the multi-proposal side-by-side comparison view.

**Core technologies — net new:**
- `networkx>=3.6.1`: Topology graph data structure and JSON serialization — pure Python, no C extensions, DiGraph maps cleanly to L1→L2→L3 delegation hierarchy, `node_link_data()` output consumed directly by React Flow
- `deepdiff>=8.6.1`: Structural diff for dual correction analysis — `Delta` class required for the reconstruct-then-analyze pattern in async correction analysis
- `instructor>=1.14.5`: Structured LLM output for proposal scoring — enforces `RubricScore` Pydantic schema with automatic retry-on-validation-failure, 3M+ monthly downloads, full Anthropic support
- `@xyflow/react>=12.10.1`: Interactive topology DAG visualization — React 19 compatible, maps 1:1 to NetworkX `node_link_data` output, SSR-compatible with Next.js 15
- `@dagrejs/dagre>=2.0.4`: Hierarchical layout for L1→L2→L3 DAG — maintained fork, standard pairing with React Flow v12
- `elkjs>=0.11.1`: Alternative layout for multi-proposal comparison view — lazy-loaded only, not the default; use with `ssr: false` dynamic import in Next.js

**What not to add:** New PostgreSQL tables (topology proposals are JSON files under existing flock discipline), a separate vector store (memU's pgvector handles structural preference retrieval), numpy in orchestration (not needed), the old `reactflow` npm package (replaced by `@xyflow/react` in v12; pins to React 16 era), or `pydantic-graph` (designed for state machine workflow execution, not topology data modeling).

### Expected Features

The feature dependency chain is strict. Topology Serialization is the foundation — every other v2.0 feature operates on serialized topology objects. Correction Storage is the memory anchor — preference profiling, async diff analysis, confidence evolution, and structural memory retrieval all read from or write to it. Async Diff Analysis requires Hard Edit to exist first. Preference Profiling requires 5+ corrections to produce any signal and is explicitly P3 (v2.1+).

**Must have — v2.0 core (P1):**
- Topology Serialization Schema (TOPO-01) — JSON schema for topology objects; everything depends on this shape
- Multi-Candidate Proposal Engine (PROP-01) — Lean/Balanced/Robust candidates with per-dimension rubric scores and justification text
- Archetype System (PROP-02) — fixed definitions with documented characteristics (not generated on the fly)
- Human Approval Gate (GATE-01) — blocks L3 spawn until topology is approved; supports soft feedback and hard edit paths
- Correction Storage (CORR-01) — stores every correction event; the data foundation for all learning
- Topology Diff Engine (DIFF-01) — structural diff used by gate display and async analysis pipeline
- Topology Observability Panel (OBS-01) — dashboard view with proposals, approval status, correction history

**Should have — v2.0 extension (P2, after core is validated and data is accumulating):**
- Async Diff Analysis (CORR-02) — post-edit async analysis; surfaces non-blocking notes when divergence is significant and high-confidence
- Structural Memory Retrieval (MEM-01) — past topologies as proposal context; can cold-start without this, improves with use
- Confidence Evolution Timeline (OBS-02) — per-project confidence trend (requires minimum 5 tasks of data)

**Defer to v2.1+ (P3):**
- Preference Profiling (MEM-02) — structured preference rules from correction history; requires 10+ corrections to be useful
- Mid-Flight Topology Adaptation — explicitly out of scope; requires topology-as-data proven stable under real workload first
- Auto-Approval on High Confidence — only viable after preference profiling is accurate (estimated 50+ corrections per project)

**Anti-features to avoid entirely:**
- Single-best recommendation (destroys reasoning surface; always return all three archetypes)
- Auto-approval (removes human gate from consequential structural decisions; erodes the trust model)
- Freeform drag-and-drop topology editor (wrong interface for this audience; structured JSON edit is correct)
- LLM-generated scoring without rubric constraints (non-deterministic and non-comparable; use external constraint linting for checkable properties)
- Topology diff on every task run (noise; diff on correction events only)

### Architecture Approach

The v2.0 architecture introduces a new `topology/` Python package inside `packages/orchestration/src/openclaw/` with seven modules: `model.py` (SwarmTopology dataclass), `diff.py` (TopologyDiff engine), `rubric.py` (RubricEvaluator with configurable weights), `proposer.py` (StructureProposer with three archetype builders), `correction.py` (CorrectionHandler with soft/hard paths), `structural_memory.py` (StructuralMemory + StructuralPreferenceProfile), and `__init__.py`. On the dashboard side, a new `topology/` component directory and matching API routes under `app/api/topology/[projectId]/`. Only six existing files require modification — all surgical and backwards-compatible: `config.py`, `memory_client.py`, `events/protocol.py`, `spawn.py` (one optional parameter), `project_config.py`, and `Sidebar.tsx` (one nav item). Core infrastructure — `state_engine.py`, `spawn/pool.py`, Docker images, `autonomy/`, `snapshot.py`, `soul_renderer.py`, the memU service itself — is untouched.

**Major components:**
1. `topology/model.py` — SwarmTopology, AgentNode, TopologyEdge, RubricScore, ScoredProposal; the foundation all other topology modules depend on
2. `topology/proposer.py` — StructureProposer; retrieves structural preferences from memU, builds three archetypes, scores each with RubricEvaluator, returns List[ScoredProposal] stored to `topology/proposals/` directory
3. `topology/correction.py` — CorrectionHandler; `soft_correct()` re-proposes with feedback context; `hard_correct()` writes `current.json` immediately then spawns daemon thread for async diff analysis
4. `topology/structural_memory.py` — StructuralMemory; uses existing MemoryClient with `AgentType.TOPOLOGY` namespace and `category="structural_topology"` to isolate structural memories from L3 SOUL injection
5. Topology Observability (dashboard) — ProposalCard, TopologyGraph (React Flow + dagre), RubricScoreBar, CorrectionHistory, ConfidenceEvolution; served by Next.js API routes reading topology JSON files directly (same pattern as existing metrics routes)

**Build order:** Phase A (data layer: model, diff, config additions, events additions, memory_client enum) → Phase B (core engine: rubric, structural_memory, proposer, correction) → Phase C (execution integration: spawn.py optional param) → Phase D (observability API: Next.js routes, TypeScript types, parallel with C) → Phase E (dashboard UI: components, page, sidebar, depends on D).

### Critical Pitfalls

1. **Over-abstraction of the topology graph model** — Using a generic graph library as the primary data model produces 300-line graph traversal functions for properties expressible as simple field lookups on a domain-specific dataclass, plus an impedance mismatch at spawn time that requires a "compile graph to spawn config" translation layer. Prevention: define topology as a concrete Python dataclass with explicit fields (`archetype` enum, `l3_roles` list, `coordination_pattern` enum, `estimated_pool_size` int); treat `networkx` as a serialization/rendering utility, not the primary model. Phase 1 deliverable: all three archetypes serialize to valid spawn configs with no translation layer.

2. **Structural memory contaminating L3 SOUL context** — Topology diffs stored in memU without explicit category exclusion get retrieved during L3 pre-spawn memory assembly, injecting topology proposal JSON (verbose, irrelevant to executors) into the 2000-character SOUL context budget, crowding out "Past Review Outcomes" and "Task Outcomes" that executors actually need. Prevention: define `category="structural_topology"` and add it to the exclusion list in `_format_memory_context()` in `spawn.py` before any structural data is written to memU. Verify by running `grep -i "topology\|archetype\|rubric" /run/openclaw/soul.md` in a running L3 container after a proposal has been approved.

3. **LLM proposal quality degrading silently under real workloads** — Proposals drift over time: roles not in the skill registry, pool sizes exceeding `max_concurrent`, inconsistent rubric scores on re-proposal for identical input. Prevention: build a constraint linter (validates `l3_roles ⊆ skill_registry`, `estimated_pool_size ≤ max_concurrent`) before integrating LLM output; compute rubric scores externally from structured LLM output rather than having the LLM generate scores directly.

4. **Correction loop instability — oscillating proposals that never converge** — Contradictory soft feedback ("too many agents" then "add a reviewer") produces oscillating proposals, filling structural memory with contradictory signals. Prevention: enforce maximum 3 re-propose cycles per session; implement a convergence check (if new proposal differs from a previous proposal in this session by fewer than 2 role changes, surface the trade-off explicitly instead of re-proposing).

5. **Structural confidence conflicting with autonomy escalation** — The proposal engine's `overall_confidence` and v1.6's `autonomy.confidence_threshold` are semantically distinct (pre-execution structural fit vs. runtime task complexity) but share the same vocabulary. If they share a config key or escalation trigger, a low-confidence topology proposal could trigger ESCALATING state before the user ever sees the proposal. Prevention: use a separate `topology.proposal_confidence_warning_threshold` config key; document the interaction contract (structural confidence below threshold → present with warning, proceed normally; execution confidence → existing autonomy escalation logic).

6. **Observability overhead degrading execution performance** — Storing full topology proposals in `workspace-state.json` creates lock contention with L3 container state updates (both use `fcntl.LOCK_EX`); after 10 tasks with 2 correction cycles each the state file grows 150KB+ and L3 lock wait times increase. Prevention: topology observability data goes in a separate `topology/` directory never locked by L3 containers; store minimal precomputed summaries, not full 3-archetype proposal JSON; precompute diffs server-side.

7. **Preference feedback loop locking in early mistakes** — After 10 approvals of Lean (even if chosen by default, not genuine preference), the proposal engine gains high confidence in Lean and stops presenting alternatives effectively. Users never escape the locally-optimal preference established by path dependence. Prevention: build preference decay (14-day half-life) and epsilon-greedy exploration (20% random archetype ordering) into the preference scoring before it processes its first correction.

8. **Backwards compatibility break on schema changes** — Adding new topology fields to `OPENCLAW_JSON_SCHEMA` with `additionalProperties: False` breaks all existing project.json files silently. Prevention: all topology-related schema fields must be optional with defaults; test all existing `projects/*/project.json` files through the new validator before merging any schema change.

---

## Implications for Roadmap

The feature dependency chain dictates a strict build order. Topology Serialization must come first (everything depends on it), then the Proposal Engine (requires the model), then the Correction System (requires proposals to correct), then Structural Memory integration (requires corrections to learn from), then Observability polish (requires all of the above to have data). The dashboard API (Next.js routes) can be built in parallel with execution integration once the core Python engine is stable.

### Phase 1: Topology Foundation (Data Layer)

**Rationale:** All other v2.0 features operate on serialized topology objects. This phase is also where backwards-compatibility risk is highest — schema changes must be made with optional fields and tested against all existing project configs before any spawn parameter additions occur. Build this before touching any other module.
**Delivers:** `SwarmTopology` dataclass with all three archetypes serializable to spawn configs; `TopologyDiff` engine (`topology/diff.py`); `EventDomain.TOPOLOGY` event types added to `events/protocol.py`; `AgentType.TOPOLOGY` enum added to `memory_client.py`; topology file storage structure (`topology/proposals/`, `topology/history/`, `topology/current.json`); `get_topology_dir()` helper in `config.py`; all new schema fields as optional-with-defaults tested against all existing project.json files.
**Addresses:** TOPO-01 (topology serialization), DIFF-01 (diff engine)
**Avoids:** Over-abstraction pitfall (concrete dataclass, networkx as serialization utility not primary model); backwards-compatibility break (optional fields, validator run against all existing configs before merge)
**Research flag:** Standard patterns — data modeling is well-understood; no additional research needed

### Phase 2: Structure Proposal Engine

**Rationale:** The core user-facing value of v2.0. Requires the topology data layer from Phase 1. The constraint linter must be built before LLM integration (per pitfall prevention for silent quality degradation). The two-confidence-system interaction contract must be documented here before any LLM-generated confidence scores exist.
**Delivers:** `StructureProposer` with three archetype builders; `RubricEvaluator` with 7-dimension scoring and configurable weights (via `openclaw.json → topology.rubric_weights`); `instructor`-based structured LLM output enforcing `RubricScore` Pydantic schema; constraint linter (validates roles against skill registry, pool size against `max_concurrent`); proposals stored to topology file directory; `TOPOLOGY_PROPOSED` event emitted via event_bus; `topology.proposal_confidence_warning_threshold` config key (separate from `autonomy.confidence_threshold`).
**Addresses:** PROP-01 (multi-candidate proposal engine), PROP-02 (archetype system)
**Uses:** `networkx>=3.6.1`, `instructor>=1.14.5`, `pydantic>=2.9`
**Avoids:** Silent LLM quality degradation (constraint linter built before LLM integration); autonomy framework conflict (separate config keys, interaction contract documented)
**Research flag:** Archetype-to-task-type heuristic mapping needs a small implementation spike — the research defines archetype characteristics but not the exact task classification heuristic; start with keyword/size/ambiguity heuristics and tune empirically

### Phase 3: Human Approval Gate and Dual Correction System

**Rationale:** Without the approval gate, the proposal engine produces output that is never acted upon. Gate and correction system are tightly coupled — soft feedback and hard edit are both gate interaction patterns. Build together. Cycle limits and convergence checks must be built before structural memory integration to prevent oscillation contaminating the learning signal.
**Delivers:** `CorrectionHandler` with `soft_correct()` (re-propose with feedback context) and `hard_correct()` (write `current.json` immediately, spawn daemon thread for async diff analysis); approval gate API endpoint integrated with `spawn.py`; `TOPOLOGY_APPROVED` and `TOPOLOGY_CORRECTED` events; `spawn.py` optional `topology_id` parameter (1-line addition); correction storage schema; maximum 3 re-propose cycles per session enforced; convergence check before re-proposing.
**Addresses:** GATE-01 (approval gate), CORR-01 (correction storage), CORR-02 (async diff analysis — daemon thread pattern)
**Uses:** `deepdiff>=8.6.1` (structural diff in async analysis path)
**Avoids:** Correction loop instability (cycle limit and convergence check built in this phase, before structural memory integration); blocking user on async analysis (execute-then-analyze daemon thread, same pattern as `_run_memory_extractor()` in `state_engine.py`)
**Research flag:** Standard patterns — the execute-then-analyze daemon thread pattern is established in the codebase and directly replicable

### Phase 4: Structural Memory Integration

**Rationale:** Requires correction data to exist (Phase 3). Category exclusion rule and preference extraction format must be defined before any structural data is written to memU — if structural memories are ever injected into L3 SOUL context (even once), the behavior is immediately visible and incorrect. Preference profiling (P3) is out of scope for v2.0 — only storage, retrieval, and preference profile scaffolding ships here.
**Delivers:** `StructuralMemory` class with `store_diff()`, `store_outcome()`, `get_preference_profile()`, `update_preference_profile()`, `retrieve_relevant()`; `StructuralPreferenceProfile` dataclass; `category="structural_topology"` exclusion added to `_format_memory_context()` in `spawn.py`; preference decay function (half-life ~14 days, configurable); epsilon-greedy exploration (20% random archetype ordering on proposals); per-project structural memory retention limit (20 records max); MEM-01 structural memory retrieval wired into `StructureProposer`.
**Addresses:** MEM-01 (structural memory retrieval as proposal context)
**Avoids:** Memory bloat (store preference extractions ~50 chars, not full topology JSON ~2KB per record); L3 SOUL contamination (explicit category exclusion before first write); preference feedback loop lock-in (decay function and epsilon-greedy built before preference scoring influences proposals)
**Research flag:** Preference decay rate (14-day half-life) is a starting estimate requiring empirical calibration after real correction data accumulates; flag for tuning after Phase 4 ships

### Phase 5: Topology Observability (Dashboard)

**Rationale:** The dashboard layer depends on the full backend pipeline existing (Phases 1–4 stable). Next.js API routes (Phase D in architecture build order) can be developed in parallel with Phase 3 execution integration once Phase 2 is stable. UI components depend on API routes. Add `@xyflow/react`, `@dagrejs/dagre`, and `elkjs`.
**Delivers:** Next.js API routes for topology proposals, current topology, correction history, confidence evolution; TypeScript topology type definitions (`src/lib/types/topology.ts`); `TopologyGraph.tsx` (React Flow + dagre layout), `ProposalCard.tsx`, `RubricScoreBar.tsx`, `CorrectionHistory.tsx`, `ConfidenceEvolution.tsx` (using existing Recharts); `topology/page.tsx`; Sidebar nav item addition (single line in `Sidebar.tsx`); `TOPOLOGY_INSIGHT` event for non-blocking async diff notes surfaced as dismissable info banners.
**Addresses:** OBS-01 (topology observability panel), OBS-02 (confidence evolution timeline)
**Uses:** `@xyflow/react>=12.10.1`, `@dagrejs/dagre>=2.0.4`, `elkjs>=0.11.1` (lazy-loaded, `ssr: false`)
**Avoids:** Observability overhead on execution (topology data stored in separate `topology/` directory, never in `workspace-state.json`; precomputed diff summaries returned by API, not raw JSON for client-side diffing; `elkjs` lazy-loaded to avoid SSR issues)
**Research flag:** React Flow + dagre integration is well-documented; Next.js API route pattern matches existing routes exactly; standard patterns apply

### Phase Ordering Rationale

- Phase 1 before all others — topology serialization is the literal foundation; no other feature can be built without a stable, validated topology schema.
- Phase 2 before Phase 3 — the correction system corrects proposals; proposals must exist before corrections are possible.
- Phase 3 before Phase 4 — structural memory learns from corrections; corrections must be stored before memory can accumulate.
- Phase 4 before Phase 5 API routes — observability surfaces structural memory data; the retrieval paths must be stable before the dashboard reads from them.
- Phase 5 dashboard UI components can partially overlap with Phase 3 and Phase 4 — once Phase 2 produces stable proposal JSON, the UI component shapes are known and dashboard development can begin.
- Backwards compatibility validation must happen at Phase 1 before any schema changes are merged — the blast radius (all existing projects fail to load) is large; the fix window is small.

### Research Flags

Phases needing deeper research or implementation spikes during planning:
- **Phase 2 (Proposal Engine) — archetype-to-task-type heuristic mapping:** Research documents define archetype characteristics but not the exact classification heuristic for task descriptions. Resolve during implementation with a small spike: start with keyword/length/ambiguity heuristics, validate against a handful of representative tasks, tune empirically.
- **Phase 4 (Structural Memory) — preference decay rate tuning:** The 14-day half-life is a reasonable starting point but depends on project usage frequency and preference stability. Flag for empirical calibration after the first real-world correction data is available.

Phases with standard patterns (skip additional research):
- **Phase 1 (Topology Foundation):** Pure data modeling with existing Python patterns; JSON file storage with existing atomic rename and flock discipline; no novel integration.
- **Phase 3 (Correction System):** Execute-then-analyze daemon thread pattern is established in codebase (`_run_memory_extractor()` and `snapshot._memorize_review_decision()`); directly replicable.
- **Phase 5 (Observability Dashboard):** React Flow + dagre integration is thoroughly documented; Next.js API route pattern matches existing `/api/metrics/route.ts` exactly; `elkjs` lazy-load with `ssr: false` is documented by both xyflow and Next.js.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All package versions verified via PyPI and npm registries; React Flow v12 React 19 compatibility confirmed via official blog; codebase inspection confirmed existing baseline (React 19, Next.js 15, Recharts >=3.7.0, zod >=3.23.8, better-sqlite3 >=12.6.2) unchanged |
| Features | MEDIUM-HIGH | Table stakes and differentiators grounded in published HITL and multi-agent research; anti-features well-justified by system constraints; preference profiling data requirements (5+ corrections for signal, 10+ for profiling) are estimates from RLHF literature, not empirically validated numbers for this specific system |
| Architecture | HIGH | Direct codebase analysis of all integration points; build order derived from actual dependency graph; modified-vs-new-vs-untouched classification verified against live source files; seven untouched components confirmed via direct inspection |
| Pitfalls | HIGH | Six of eight pitfalls are codebase-derived (flock contention analysis, memU category pattern, autonomy hooks interaction, `additionalProperties: False` schema behavior, SOUL injection path, daemon thread patterns); two pitfalls (correction loop instability, preference feedback loop) are MEDIUM-confidence from general ML/recommendation systems literature but well-aligned with specific system constraints |

**Overall confidence:** HIGH

### Gaps to Address

- **Archetype-to-task heuristic:** The proposal engine must classify task descriptions into complexity/risk buckets to select which archetypes to emphasize. Research documents archetype characteristics but not the classification heuristic. Resolve during Phase 2 with a small implementation spike — start with keyword and length heuristics and tune empirically with first real-world proposals.
- **Rubric weight defaults:** The 7 rubric dimensions are defined with clear semantics, but the default weight configuration for `overall_confidence` computation is not specified. Start with equal weights (0.143 each), make them configurable via `openclaw.json → topology.rubric_weights`, and adjust based on observed proposal quality.
- **Preference decay rate calibration:** The 14-day half-life for preference decay is a starting estimate. Real-world calibration requires observing how frequently project preferences change under actual usage. Not a blocking gap — preference profiling is P3 (v2.1+) and will have correction data to calibrate against before it influences proposals significantly.
- **`instructor` vs. native structured outputs:** Anthropic's structured outputs (`structured-outputs-2025-11-13` beta) is an alternative to `instructor` but remains in public beta as of March 2026. Use `instructor` for v2.0 (stable, proven); reevaluate native structured outputs for v2.1+ once general availability is confirmed.

---

## Sources

### Primary (HIGH confidence)

- PyPI index — `networkx>=3.6.1` (Python >=3.11, Dec 2025), `deepdiff>=8.6.1` (Jan 2026), `instructor>=1.14.5` (Jan 2026)
- npm registry — `@xyflow/react>=12.10.1`, `@dagrejs/dagre>=2.0.4`, `elkjs>=0.11.1`
- NetworkX official docs — `node_link_data()`, `node_link_graph()` JSON serialization API
- React Flow v12 official blog — React 19 + Next.js 15 SSR compatibility confirmation
- instructor official docs — `from_anthropic()`, `Mode.TOOLS`, retry-on-validation-failure behavior
- Codebase inspection: `packages/orchestration/src/openclaw/state_engine.py`, `spawn.py`, `autonomy/hooks.py`, `autonomy/types.py`, `config.py`, `soul_renderer.py`, `project_config.py`, `memory_client.py`, `events/protocol.py` — all integration points and patterns verified directly
- Codebase inspection: `packages/dashboard/src/` — confirmed React 19, Next.js 15, Recharts >=3.7.0, zod >=3.23.8, better-sqlite3 >=12.6.2, SWR, Tailwind CSS 3
- `.planning/PROJECT.md` — v2.0 feature requirements and key decisions (topology-as-data, three archetypes, dual correction, structural memory, no mid-flight adaptation)

### Secondary (MEDIUM confidence)

- [AgentConductor (arxiv 2602.17100)](https://arxiv.org/abs/2602.17100) — RL-optimized topology evolution, density-aware design
- [Open Agent Specification (arxiv 2510.04173)](https://arxiv.org/html/2510.04173v1) — portable serializable agent configs, platform-agnostic schema
- [Microsoft Azure AI Agent Design Patterns (2026)](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) — sequential, concurrent, hierarchical patterns; HITL for consequential decisions
- [Galileo Agent Evaluation Framework (2026)](https://galileo.ai/blog/agent-evaluation-framework-metrics-rubrics-benchmarks) — 7-dimension rubric structure
- [Human-in-the-Loop Agentic AI Systems — OneReach (2026)](https://onereach.ai/blog/human-in-the-loop-agentic-ai-systems/) — approval gate patterns for high-stakes agentic decisions
- [RLHF and Learning from Corrections (arxiv 2504.12501)](https://arxiv.org/html/2504.12501v3) — preference learning from edit diffs; PRELUDE-style approaches
- [Multi-Agent Collaboration via Evolving Orchestration (arxiv 2505.19591)](https://arxiv.org/html/2505.19591v1) — graph topology evolution patterns

### Tertiary (LOW confidence / needs validation)

- Correction loop cycle limit of 3 — reasonable default based on interactive ML termination patterns; no empirical data for this specific domain
- Preference profiling minimum corrections (5 for retrieval signal, 10 for profiling) — estimated from RLHF literature; needs calibration against real usage data
- 14-day preference decay half-life — reasonable starting point; should be tuned based on actual project correction frequency after v2.0 ships

---
*Research completed: 2026-03-03*
*Ready for roadmap: yes*
