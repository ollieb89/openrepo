# Pitfalls Research

**Domain:** Adding structural intelligence (topology modeling, LLM-driven structure proposal, correction-as-training, structural observability) to an existing 60-phase multi-agent orchestration system (~340K LOC) with Docker isolation, memU memory, and autonomy framework.
**Researched:** 2026-03-03
**Confidence:** HIGH — derived from direct codebase inspection of `state_engine.py`, `spawn.py`, `autonomy/hooks.py`, `autonomy/types.py`, `config.py`, `soul_renderer.py`, `project_config.py`, `dashboard/src/lib/types.ts`, plus analysis of v1.0–v1.6 architectural patterns and integration points that the v2.0 features must layer on top of.

---

## Critical Pitfalls

### Pitfall 1: Over-Abstraction of the Topology Graph Model

**What goes wrong:**
The topology data model is designed to be "maximally general" — a fully generic directed graph with arbitrary node types, edge labels, and metadata fields. Implementation begins with a graph library (NetworkX or a custom adjacency structure) capable of representing any conceivable agent topology. Three archetypes (Lean, Balanced, Robust) are implemented as subclasses or parameterized templates of this generic model. The scoring rubric operates on generic graph properties.

The result: proposal generation requires 300-line graph traversal functions to extract "number of coordination edges" or "critical path length" — properties that could be computed trivially if the model was constrained to the domain's actual topology vocabulary. The graph model accumulates fields that are never used ("edge latency hints", "node affinity scores") because they were added for theoretical completeness. Serialization to/from JSON becomes non-trivial as the generic graph structure doesn't map cleanly to flat JSON.

The existing system's agent model is flat: level (1/2/3), `reports_to` (one parent), `subordinates` (list). The v2.0 topology must be expressible as container configurations that spawn into this exact structure. A generic graph model diverges from this constraint and creates an impedance mismatch at spawn time — the graph must be "compiled" into spawn parameters, adding a translation layer that becomes a bug surface.

**Why it happens:**
Topology feels like a graph problem, so developers reach for graph abstractions. The urge to build something reusable and general is strong. The three archetypes make the model feel like it needs parameterization. But the actual topology space for this system is narrow: L1 (one), L2 per project (one), L3 pool (2-5 containers). The complexity is in the *coordination patterns*, not the structure.

**How to avoid:**
Define the topology schema as a concrete Python dataclass, not a generic graph. It should have explicit fields: `archetype` (enum), `l3_roles` (list of typed role descriptors), `coordination_pattern` (enum: direct, hub-and-spoke, pipeline), `estimated_pool_size` (int), and `rationale` (str per component). The scoring rubric operates on these named fields directly — not on graph traversal.

The graph visualization in the dashboard is a *rendering concern*, not a storage concern. Compute the visual graph representation from the dataclass at render time. Do not store a graph data structure in memU or the state file.

**Warning signs:**
- The topology schema has more than 8 top-level fields after initial design
- "Compile topology to spawn config" is planned as a separate phase item rather than a trivial dict translation
- Graph traversal functions are written before a single archetype is manually representable as JSON
- The schema requires importing a graph library (`networkx`, etc.) in the orchestration package

**Phase to address:** Topology-as-data phase (Phase 1 of v2.0). Define the schema first as a dataclass with the three archetypes hard-coded, validate that each archetype serializes to a valid spawn config, and only then generalize if needed.

---

### Pitfall 2: LLM Proposal Quality Degrades Silently Under Real Workloads

**What goes wrong:**
The structure proposal engine is built, tested with a handful of representative task descriptions, and deployed. Initial proposals are high quality. Over time, the LLM's proposals drift: roles proposed don't match the actual skill registry in `l3_config`, `estimated_pool_size` exceeds the project's `max_concurrent` (currently 3), archetypes are selected incorrectly for task type (Robust proposed for a 2-hour refactor), and scoring rubric values are inconsistent across proposals (same task, different scores on re-proposal). None of this is detected because there is no proposal quality measurement in place.

The scoring rubric is the mechanism intended to surface quality — but if the LLM generates scores as part of the proposal (rather than scores being computed externally), it can produce self-consistent but incorrect scores (e.g., a proposal that claims low coordination overhead while specifying a 4-agent hub-and-spoke structure). There is no ground truth for proposal quality until execution completes, and by then the causal connection between proposal and outcome is lost.

**Why it happens:**
LLM-generated structured output is easy to get right in controlled demos and hard to keep right as the prompt context, model version, and task distribution shift. Proposal quality is assumed to be the LLM's responsibility — if the model is good, the proposals will be good. No instrumentation is built to detect quality regression because it is not obvious what "quality" means for a pre-execution proposal.

**How to avoid:**
Separate proposal generation from scoring. The LLM generates the proposed structure (archetype, roles, rationale text). An external scoring function computes the rubric values from the proposal's properties against known system constraints: `pool_size ≤ project.max_concurrent`, `roles ⊆ skill_registry`, `archetype matches task_size_heuristic(description)`. These constraint checks are deterministic and can be tested.

Log every proposal with a proposal ID. When the topology is executed and completes, log outcome (success/failure, actual execution time vs. estimate). This creates the feedback loop for detection of quality drift: if estimated `time_to_first_output` is consistently 3x the actual, the scoring heuristic is wrong.

Define a proposal linting step: before presenting proposals to the user, validate that all proposed roles exist in the skill registry, that `estimated_pool_size` is within bounds, and that the archetype label matches the constraints claimed. Reject malformed proposals at generation time with a re-prompt, not at correction time.

**Warning signs:**
- Proposed `l3_roles` contain role names that don't exist in `agents/l3_specialist/config.json`
- `estimated_pool_size` in a proposal exceeds the project's `max_concurrent` (default: 3)
- Both `Lean` and `Robust` archetypes are proposed for the same task description on consecutive calls
- Scoring rubric values change by >0.3 on re-proposal for identical input
- No proposal ID is stored in the correction record, preventing outcome attribution

**Phase to address:** Structure proposal engine phase. Build the constraint linter before the LLM prompt. Test the linter independently. Only integrate LLM output with the linter already in place.

---

### Pitfall 3: Correction Loop Instability — Feedback Creates Diverging Proposals

**What goes wrong:**
The dual correction system (soft feedback → re-propose, hard direct edit → execute-then-analyze) is implemented. A user provides soft feedback: "Too many agents, simplify." The engine re-proposes. The new proposal removes a role. The user provides feedback again: "Now missing the reviewer role." The engine adds it back. The user again: "Still too complex." This oscillation continues. The feedback history grows, but the proposals don't converge — they cycle between two configurations that each address different feedback items.

The harder failure: feedback from correction is injected into the structural memory, and structural memory is retrieved to inform future proposals. After 10 corrections on a task, the memory contains contradictory preference signals — "user prefers Lean" and "user requires reviewer role" — and the proposal engine is given both. The next proposal for a new but similar task is a confusing hybrid that satisfies neither constraint.

**Why it happens:**
Feedback signals are stored as additive preferences without conflict detection. "Simplify" and "add reviewer role" are treated as independent preferences that can both be satisfied. They cannot — Lean topology has no dedicated reviewer by definition. The correction system has no model of which preferences are in tension.

**How to avoid:**
Limit correction cycles per session. Define a maximum re-propose count (2-3 attempts) after which the system presents the closest available option and requires a hard edit or a manual override. Prevent infinite oscillation by design.

For structural memory, store correction signals with the archetype context: "When task type is 'refactor', user prefers Lean over Balanced" — not "user prefers Lean generally." Retrieve only signals that match the current task type and archetype context, not all historical corrections. This limits cross-contamination.

Implement a convergence check before re-proposing: if the new proposal would differ from a previous proposal in this session by fewer than 2 role changes, do not re-propose — instead, surface the trade-off explicitly: "Adding the reviewer role requires upgrading from Lean to Balanced. Accept?"

**Warning signs:**
- A single session requires more than 3 re-proposal cycles
- Structural memory contains more than 5 corrections for the same project with contradictory archetype preferences
- A proposal presented to the user is identical to one already rejected in the same session
- The convergence rate metric (corrections per session before approval) is increasing over time rather than decreasing as preferences are learned

**Phase to address:** Dual correction system phase. Build the cycle limit and convergence check before building structural memory integration. Validate with a simulated oscillation test: inject contradictory feedback signals, verify the system terminates within 3 cycles rather than oscillating.

---

### Pitfall 4: Structural Memory Bloat from Full Topology Diffs

**What goes wrong:**
Every correction generates a structural diff that is stored in memU. A structural diff is a before/after comparison of two topology proposals: which roles were added, removed, or changed; how scores changed; the user's rationale. The full diff is serialized as a JSON object and stored as a memory entry.

After 50 corrections, each project has 50 memory entries. Each entry is retrieved during pre-spawn memory context assembly. The existing `MEMORY_CONTEXT_BUDGET` is 2000 characters — structural diffs are verbose and quickly exhaust this budget, crowding out the existing "Past Review Outcomes" and "Task Outcomes" memory categories that the L3 containers actually need for execution.

The second failure: structural diffs contain full topology JSON (all 3 proposed archetypes, all scores). When retrieved, this data is injected into L3 SOUL context, which is incorrect — L3 containers are executors that don't need topology history. They need task context and past code decisions, not proposal history.

**Why it happens:**
Structural memory is stored in the same memU namespace as execution memory because it's the existing memory service. There's no memory category segmentation in the retrieval path — `_format_memory_context()` in `spawn.py` routes by `category` and `agent_type` fields, but structural topology diffs are stored without an explicit category that would exclude them from L3 injection.

**How to avoid:**
Store structural memory in a separate memU namespace or with an explicit `category: "structural_topology"` field. Update `_format_memory_context()` in `spawn.py` to explicitly exclude `structural_topology` category from L3 SOUL injection. Structural memory is only retrieved for the proposal engine (L1/L2 context), never for L3 executors.

Store preference extractions, not raw diffs. Instead of storing the full before/after topology JSON, store the extracted preference signal: `{"preference": "Lean preferred for refactors", "strength": 0.8, "project": "myproject", "task_type": "refactor"}`. This is a single sentence, not a 200-line JSON object.

Define a structural memory retention limit per project: maximum 20 structural preference records per project. When the limit is reached, aggregate old preferences into a project preference profile summary and discard the individual records.

**Warning signs:**
- L3 containers' SOUL files contain topology JSON from past proposals (check `/run/openclaw/soul.md` in a running L3 container)
- `_format_memory_context()` returns structural diff content in the "Past Work Context" section for L3 SOUL injection
- Memory context budget is exhausted by structural memory, leaving the "Past Review Outcomes" section empty for L3 containers
- Per-project structural memory entries exceed 30 records within the first week of v2.0 deployment

**Phase to address:** Structural memory phase. Define the category exclusion rule and the preference extraction format before any structural data is written to memU. Validate by running a spawn after a correction and confirming the L3 SOUL file contains no topology JSON.

---

### Pitfall 5: Observability Overhead Degrades Execution Performance

**What goes wrong:**
Topology observability is implemented as comprehensive logging: every proposal, every score, every correction, every diff is written to the state file and/or emitted as events via `event_bridge`. The structural diff visualization requires computing diffs at render time (dashboard fetches full proposal history, computes visual diff in the browser). Confidence evolution is tracked by storing every score for every rubric dimension on every proposal cycle.

The state file (`workspace-state.json`) grows rapidly: each topology proposal adds ~5KB of JSON. After 10 tasks with 2 correction cycles each, the state file is 150KB larger than baseline. The JarvisState lock contention increases because structural write operations hold `LOCK_EX` while writing large topology blobs. L3 containers, which write task updates every 30-60 seconds, experience increased lock wait times.

The dashboard fetching proposal history on every page load causes the metrics API to read the full state file repeatedly. The state cache (`CACHE_TTL_SECONDS = 5.0`) provides limited protection because structural proposal updates invalidate the cache frequently during active proposal sessions.

**Why it happens:**
Observability is added after the core feature works. The full topology data is stored "just in case" it's needed for analysis. The incremental cost of each stored proposal is not felt until 20+ proposals have accumulated. The state file's lock contention is not measured during development because tests use a single process, not the concurrent multi-container production scenario.

**How to avoid:**
Do not store full topology proposals in the JarvisState file. The state file is for task execution state. Structural observability data belongs in a separate file: `.openclaw/<project_id>/topology-history.json` or equivalent. This file is never locked by L3 containers — it is only written by the proposal engine (L2/L1) and read by the dashboard.

Store only what is needed for the dashboard visualization. The "structural diff timeline" needs: proposal ID, archetype, overall confidence score, timestamp, and correction action (approved/rejected/edited). Not all rubric dimension scores on every proposal. Rubric details are stored on the final approved proposal only.

Precompute diffs server-side. The dashboard API endpoint for structural history should return precomputed diff summaries, not raw proposals that the client must diff. This moves CPU from the browser to the API server and reduces payload size.

**Warning signs:**
- JarvisState lock wait time (`lock_wait_ms` in logs) increases from <1ms baseline to >50ms after 10 topology proposals
- `workspace-state.json` grows by more than 10KB per task lifecycle
- Dashboard metrics API response time increases proportionally with the number of proposal history entries
- L3 container activity log shows lock acquisition timeouts (`TimeoutError: Lock acquisition timeout`) during active proposal sessions

**Phase to address:** Topology observability phase. Define the storage location (separate file, not state.json) and the data model (minimal precomputed summaries) before implementing any observability writes. Add a lock contention benchmark test: spawn 3 concurrent L3 containers while running proposal sessions; verify lock wait stays <10ms.

---

### Pitfall 6: Backwards Compatibility Break — v1.x SOUL Templates and Spawn Configs Fail on v2.0 Topology

**What goes wrong:**
The topology proposal engine generates a proposed agent structure. When approved, this structure must be translated into spawn parameters — `skill_hint`, `task_description`, and eventually the `environment` dict injected into L3 containers. The v2.0 implementation adds new spawn parameters (`TOPOLOGY_ARCHETYPE`, `TOPOLOGY_ROLE`, `PROPOSAL_ID`) to the container environment.

The existing `soul_renderer.py` uses `string.Template.safe_substitute()` — it ignores unknown `$variable` references silently. But the L3 SOUL template in `agents/_templates/soul-default.md` may not include the new topology variables, causing the rendered SOUL to have literal `$TOPOLOGY_ARCHETYPE` strings rather than substituted values. Worse: v1.x agent configs that specify custom SOUL templates (via `soul_ref`) do not have topology sections, so the augmented SOUL is assembled incorrectly.

Project configs (`projects/<id>/project.json`) validated against `PROJECT_JSON_SCHEMA` now fail validation if a new required field (e.g., `topology`) is added to the schema without a migration path. Every existing project.json silently loses validation until updated.

**Why it happens:**
Adding new fields to existing schemas is the most common source of backwards compatibility breaks in incrementally developed systems. The existing validation is strict (`additionalProperties: False` in `OPENCLAW_JSON_SCHEMA`). Any new field added to proposals or spawn configs must also be added to the validation schemas, but existing data doesn't have those fields — causing validation failures on load.

**How to avoid:**
All topology-related fields in schemas must be optional with defaults. Never add a required field to `OPENCLAW_JSON_SCHEMA`, `PROJECT_JSON_SCHEMA`, or the SOUL template variables without providing a default value that preserves existing behavior. Add a schema version bump process: when v2.0 changes any schema, the config validator must accept both the old (v1.x) and new (v2.0) forms during a transition period.

Test backwards compatibility explicitly: load every existing `project.json` in the repository through the new validator before merging any schema change. This is a 30-second automated test that catches 100% of schema breaks against known real configs.

The SOUL template must be updated before the spawn parameters are added. If `TOPOLOGY_ARCHETYPE` is injected as an environment variable but the SOUL template doesn't reference it, it's harmless. The reverse (SOUL references `$TOPOLOGY_ARCHETYPE` but spawn doesn't set it) produces visible template pollution in the rendered SOUL.

**Warning signs:**
- `safe_substitute()` output contains literal `$TOPOLOGY_ARCHETYPE` strings in the rendered SOUL
- `openclaw-project list` fails with `ConfigValidationError` for any existing project after v2.0 schema update
- A project that worked in v1.6 fails to spawn L3 containers after v2.0 deployment without any change to its config
- The config validator passes for new projects but fails for the projects in `projects/` that were created before v2.0

**Phase to address:** Topology-as-data phase (first). Schema changes must be made with optional fields and tested against all existing project configs before any new spawn parameters are added.

---

### Pitfall 7: Correction-as-Training Creates a Positive Feedback Loop That Locks In Early Mistakes

**What goes wrong:**
The structural memory stores correction patterns: "User approved Lean for tasks tagged 'bugfix'." After 10 approved Lean proposals for bugfixes, the proposal engine has high confidence that Lean is preferred for bugfixes. Future bugfix proposals present Lean as the top-ranked option with high confidence.

The user made a poor choice on the first 3 bugfixes — they approved Lean because it was the first option, not because it was optimal. The system learns this non-preference as a preference. Over time, the high-confidence Lean recommendation discourages the user from even reading the Balanced or Robust options, because Lean appears with a high "preference fit" score. The system converges on a locally-optimal preference that was established by path dependence, not genuine preference.

This is the classic cold-start / feedback loop problem in recommendation systems. It is particularly acute here because there are only 3 archetype options — the system converges on a single archetype very quickly, and the correction signal needed to escape the local optimum requires the user to actively override a "high confidence" recommendation.

**Why it happens:**
Correction-as-training with a simple frequency-based preference model always amplifies whatever pattern appears first. There is no mechanism to distinguish "approved because optimal" from "approved because it was the default." The preference profile grows monotonically — there is no forgetting, no decay, and no uncertainty quantification.

**How to avoid:**
Apply preference confidence decay over time. A preference signal from 30 days ago should have lower weight than one from yesterday, because task patterns change. Implement a half-life on preference records: each correction's contribution to the preference score is multiplied by `exp(-λ * days_since)` where λ is tuned to a 14-day half-life.

Implement epsilon-greedy exploration. On a random 20% of proposals (configurable), present the archetypes in random order rather than preference-ranked order. This ensures the user sees all options occasionally, preventing the recommendation from locking into the first-approved archetype permanently.

Surface the confidence basis. When the proposal engine presents a high-confidence Lean recommendation, show why: "Lean recommended based on 10 prior approvals for bugfix tasks." This makes the feedback loop visible and allows the user to consciously override it.

**Warning signs:**
- A single archetype achieves >80% preference score within the first 5 corrections
- The second and third archetype proposals are never read by the user (proposal session duration collapses to <10 seconds — they approve immediately)
- After 20 corrections, the preference profile is essentially deterministic: one archetype always scores >0.9 regardless of task description
- A user requests "show me something different" — this is a direct signal that exploration has been suppressed

**Phase to address:** Structural memory phase. Build the decay function and epsilon-greedy exploration into the preference scoring system before it processes its first correction. Validate with a simulation: inject 10 identical correction signals and verify the resulting preference score is bounded, not at 1.0.

---

### Pitfall 8: Topology Proposal Pre-empts the Autonomy Framework's Confidence-Based Escalation

**What goes wrong:**
v1.6 introduced the autonomy framework: tasks have a confidence score, and tasks below the escalation threshold (`confidence_threshold: 0.4`) are escalated rather than executed autonomously. v2.0 adds topology proposals with their own confidence scores (the rubric's "overall confidence" dimension).

These two confidence systems are independent but will inevitably interact. A topology proposal with overall confidence 0.35 is below the escalation threshold — should the system escalate before even proposing, or propose and let the user decide? If the proposal engine's confidence is below threshold, the autonomy hooks in `hooks.py` may trigger ESCALATING state before the proposal is presented to the user. The user never sees the proposal. The task is escalated based on structural uncertainty, not execution uncertainty.

The reverse failure: a topology proposal with overall confidence 0.9 bypasses the autonomy escalation check because the structural confidence is high. But the underlying task (the code the agents will write) may be ambiguous and low-confidence for execution. The two systems use different inputs for confidence calculation.

**Why it happens:**
Two independent subsystems with overlapping scope are added in different milestones without an explicit interaction contract. The autonomy framework was designed for execution confidence. The proposal engine's confidence measures structural fit. They are semantically distinct but share the same escalation vocabulary and threshold configuration.

**How to avoid:**
Define the interaction contract explicitly before either feature ships in v2.0. The structural proposal confidence is pre-execution, architectural confidence. The autonomy execution confidence is runtime, task-complexity confidence. They must not share the same `confidence_threshold` config value or the same escalation trigger.

Rule: structural proposal confidence below threshold → present proposal with a low-confidence warning, but proceed normally to user review. Never trigger autonomy ESCALATING state from structural confidence alone. The user seeing a low-confidence proposal is the correct response — they can provide corrections.

Rule: autonomy execution confidence (computed at task spawn time in `autonomy/confidence.py`) operates independently of the approved topology. The approved topology is an input to execution confidence (more complex topology → lower execution confidence), but the calculation is separate.

Add a config field: `topology.proposal_confidence_warning_threshold: 0.5` — separate from `autonomy.confidence_threshold: 0.4`. These should never be the same key.

**Warning signs:**
- A task is escalated to L1 before the user ever sees a topology proposal — the pre-execution confidence check fires before proposal presentation
- The `autonomy.confidence_threshold` setting in `openclaw.json` affects how many topology proposals are presented rather than how many tasks are autonomously executed
- `hooks.py` `on_task_spawn()` is called with `AutonomyState.ESCALATING` for a task that hasn't been proposed yet

**Phase to address:** Structure proposal engine phase. Document the two confidence systems and their interaction contract before implementing the proposal engine. The autonomy hooks must not be triggered by proposal-phase events.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store full topology proposals in workspace-state.json | Single storage location, no new files | JarvisState lock contention increases for all L3 containers; state file grows unboundedly | Never — topology history must be a separate file not locked by L3 containers |
| Reuse the same memU category for structural and execution memories | No new memU category fields needed | Structural topology JSON is injected into L3 SOUL context; MEMORY_CONTEXT_BUDGET exhausted by topology diffs | Never — explicitly set `category: "structural_topology"` and exclude from L3 SOUL injection |
| Use a generic graph library for the topology model | Topology feels like a graph problem | 300-line graph traversal for properties trivially computable on a domain-specific dataclass; impedance mismatch at spawn time | Never — use a concrete domain dataclass first; only generalize if a 4th archetype is proven necessary |
| Let the LLM compute rubric scores as part of proposal generation | One LLM call does everything | LLM produces self-consistent but incorrect scores; no external validation of constraint satisfaction | Never for constraint-checkable properties (pool_size bounds, role existence) — LLM scores are only valid for qualitative dimensions (complexity estimate, preference fit) |
| Single confidence threshold for both structural proposals and execution autonomy | Simpler config | Structural uncertainty triggers execution escalation or vice versa; the two systems interfere with each other | Never — use separate config keys with separate threshold values |
| Store raw correction rationale strings in structural memory | Simple to implement | Memory accumulates contradictory natural language that the proposal engine cannot reason about; preference extraction never happens | MVP-acceptable for the first 10 corrections while the extraction logic is built; must be replaced before structural memory influences >5 proposals |
| Skip proposal cycle limits in the correction loop | More user flexibility | Oscillation between incompatible preferences; correction session never converges; structural memory fills with contradictory signals | Never — maximum 3 re-propose cycles per session must be enforced from day one |

---

## Integration Gotchas

Common mistakes when layering structural intelligence on top of the existing Docker isolation, memory service, and autonomy framework.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Topology proposals → spawn.py | Adding topology fields to `spawn_l3_specialist()` signature that break the existing skill pool interface in `pool.py` | Add topology fields as optional kwargs with defaults; pool.py calls spawn with keyword args — adding required positional args breaks all existing callers |
| Structural memory → memU `_format_memory_context()` | Not adding `structural_topology` to the exclusion list in `_format_memory_context()`, so topology diffs appear in L3 SOUL | Add the exclusion before any structural data is written to memU; write a test that confirms L3 SOUL contains no topology category content after a proposal |
| Proposal confidence → autonomy hooks.py | Calling `on_task_spawn()` before the proposal is approved; the task's AutonomyContext is created before topology is confirmed | `on_task_spawn()` must only be called after topology approval, not at proposal generation time |
| Structural diff visualization → dashboard types.ts | Adding topology types to `types.ts` without updating all API routes that return `Task` or `MetricsResponse` — TypeScript type errors surface only at build time, not at runtime | Add topology types as separate interfaces in a new `topology.ts` file; keep existing `Task` and `MetricsResponse` unchanged in the initial integration |
| SOUL template → topology variables | Adding `$TOPOLOGY_ARCHETYPE` to SOUL template before `build_variables()` in `soul_renderer.py` provides the value — renders as literal `$TOPOLOGY_ARCHETYPE` in SOUL output | Update `build_variables()` first; test that `safe_substitute()` replaces the variable; only then add it to the SOUL template |
| Correction analysis → JarvisState locking | Running async correction analysis in a background thread that also reads/writes state — overlaps with L3 container lock acquisition | Correction analysis must be read-only relative to workspace-state.json; all correction writes go to topology-history.json (separate file, no JarvisState) |
| Project config validation → new topology fields | Adding `topology` key to `openclaw.json` schema with `additionalProperties: False` breaks existing configs that don't have the field | Add `topology` as an optional property with a complete default; validate that all existing project configs in `projects/` pass the new schema before merging |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Storing full 3-archetype proposals (all rubric scores) per task in memU | memU database size doubles within first month of v2.0; retrieval latency increases | Store preference extractions (~50 chars each) not full proposals (~2KB each); enforce 20-record structural memory limit per project | At 50+ tasks with 2 correction cycles each (~100 structural records) |
| Computing structural diffs client-side in the dashboard | Browser freezes when viewing proposal history for tasks with >5 correction cycles; large JSON payloads | Precompute diff summaries server-side in the topology API endpoint; return only summary objects to the client | When a task has >3 correction cycles or proposal JSON exceeds 10KB |
| Retrieving all structural memory entries during pre-spawn assembly | spawn.py pre-spawn retrieval adds 200ms+ per task as structural memory grows | Filter by `category != "structural_topology"` in the memU retrieval query passed to `_retrieve_memories_sync()` | Immediately on first structural memory entry — L3 containers should never receive structural topology memories |
| Generating all 3 archetype proposals in a single LLM call | Single LLM call for 3 proposals fails with partial output if token limit exceeded; one bad archetype contaminates the retry | Generate each archetype proposal independently (3 calls); allows independent retry of a failed archetype without regenerating the others | When the combined 3-archetype prompt exceeds 8K output tokens (typical at high rubric detail) |
| Confidence evolution tracking storing per-dimension scores for every proposal | Confidence history table grows at 7 dimensions × N proposals × M tasks; queries over this table are slow | Store only the overall confidence score and top/bottom 2 dimension scores per proposal; derive full history on-demand from structural memory | At 20+ tasks per project with 3+ proposal cycles each |

---

## Security Mistakes

Domain-specific security issues for v2.0 structural intelligence features.

| Mistake | Risk | Prevention |
|---------|------|------------|
| LLM proposal output is injected into SOUL template without sanitization | A prompt injection in the task description could cause the LLM to generate malicious topology rationale that, when injected into SOUL via `safe_substitute()`, alters the agent's behavior | Run proposal output through a sanitizer that strips `$variable` references and markdown code blocks before SOUL injection; `safe_substitute()` is safe for unresolved variables but rationale text should be treated as untrusted |
| Topology correction rationale stored in memU without content filtering | User-provided correction text ("reject because...") is stored verbatim in memU and injected into future SOUL contexts; a crafted correction could inject instructions into future agent contexts | Treat all user-provided correction rationale as untrusted text; store it in a separate field that is never injected into SOUL context; only extracted preference signals (system-generated) go into the memU fields that feed SOUL injection |
| Proposal ID is user-controlled and used as a file path component | If proposal IDs are derived from user input (task description slug), path traversal is possible when proposal data is stored in `.openclaw/<project_id>/topology-history.json` | Generate proposal IDs as UUIDs (`uuid.uuid4()`) server-side; never derive IDs from user-provided input; validate that any ID used in a file path matches `^[a-f0-9-]{36}$` |
| Structural diff output contains full task descriptions | Topology observability exports (for debugging) include task descriptions that may contain sensitive business information; exported diffs leak this information | Implement a `--redact-tasks` flag on any observability export CLI; store task descriptions separately from structural scores in the topology history |

---

## UX Pitfalls

Common user experience mistakes in the structural intelligence domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Presenting all 3 archetypes at equal prominence | User reads all 3 in depth for every task; cognitive overload; proposal session takes 5+ minutes | Present the top-ranked archetype prominently with a short rationale; show the other 2 as collapsed alternatives with one-line summaries; expand on request |
| Showing all 7 rubric scores for every archetype | 21 numbers per proposal session; user cannot quickly identify the relevant trade-off | Highlight only the dimensions where archetypes differ significantly (delta > 0.2); collapse identical scores into "similar across options" |
| Requiring approval before observing correction analysis | User approves a direct edit but must wait for async diff analysis to complete before proceeding; the non-blocking analysis feels blocking if the UI shows a spinner | Show the correction analysis as a post-hoc notification ("Analysis complete: your edit shifted from Balanced to Lean — preference recorded"), not as a blocking step |
| Confidence evolution timeline shown as a raw score graph | Score graph without context is uninterpretable; 0.73 on iteration 1 vs 0.81 on iteration 3 means nothing without knowing what changed | Show the confidence delta alongside the structural change: "+0.08 confidence after removing the reviewer role" — connect the score change to the specific edit |
| No differentiation between "low confidence due to task ambiguity" vs "low confidence due to preference mismatch" | User doesn't know whether to clarify the task description or adjust the topology | Surface the top-contributing factor to low confidence: "Low confidence: task description is ambiguous (complexity: 0.3)" vs "Low confidence: no prior preference for this task type (preference fit: 0.2)" |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Topology schema:** All three archetypes serialize to valid spawn configs and back — verify by calling `spawn_l3_specialist()` with topology-derived parameters for a test task without a real LLM call
- [ ] **Proposal engine:** Constraint linter validates `l3_roles ⊆ skill_registry` and `estimated_pool_size ≤ max_concurrent` before any proposal is presented — verify by injecting an invalid role name and confirming the linter rejects the proposal
- [ ] **Structural memory isolation:** L3 container SOUL files contain no `structural_topology` category content — verify by running `grep -i "topology\|archetype\|rubric" /run/openclaw/soul.md` inside a running L3 container after a proposal has been approved
- [ ] **Correction loop limit:** A session with contradictory feedback terminates after 3 re-proposal cycles — verify by injecting oscillating feedback signals in a unit test and confirming the loop exits with a "manual override required" state
- [ ] **JarvisState lock contention:** Lock wait time remains <10ms with 3 concurrent L3 containers during an active proposal session — verify with the `lock_wait_ms` metric in JarvisState log output during a concurrent test
- [ ] **Backwards compatibility:** All existing `projects/*/project.json` files pass the v2.0 schema validator — verify with `python3 -c "from openclaw.config_validator import validate_project; [validate_project(p) for p in Path('projects').glob('*/project.json')]"`
- [ ] **Autonomy hooks not triggered pre-approval:** `on_task_spawn()` is not called until after topology approval — verify with a trace: grep for `on_task_spawn` in logs for a proposal session; it must not appear before the approval event
- [ ] **Preference decay:** After injecting 10 identical correction signals (all approving Lean), the Lean preference score is <0.9 — verify that the decay function is applied and score is bounded
- [ ] **Observability storage location:** No topology data written to `workspace-state.json` — verify with `diff` on the state file before and after a complete proposal session; topology fields must not appear in the state file diff

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Topology data bloated workspace-state.json | MEDIUM | Write a one-off migration script to move `topology_*` keys from workspace-state.json to topology-history.json for each project; run during a maintenance window with L3 containers stopped |
| Structural memory contaminated L3 SOUL contexts | LOW | Add `structural_topology` exclusion to `_format_memory_context()` immediately; existing structural memories in memU are harmlessly ignored going forward; no data deletion needed |
| Correction loop oscillated — contradictory preferences in memory | MEDIUM | Reset structural memory for the affected project: delete all `structural_topology` category records from memU for that project_id; implement the cycle limit before re-enabling corrections |
| LLM proposals degraded — roles don't match skill registry | LOW | Enable the constraint linter (if not already running) to reject invalid proposals at generation time; the linter is a pure validation step that can be added without restarting the system |
| Proposal confidence interfered with autonomy escalation | MEDIUM | Separate the config keys (`topology.proposal_confidence_warning_threshold` vs `autonomy.confidence_threshold`); remove any code in hooks.py that reads proposal confidence; the state machine in `autonomy/state.py` is unaffected — only the trigger condition needs fixing |
| Preference model locked into first-approved archetype | LOW | Reset the preference profile for the project (delete structural_topology preference records in memU); implement epsilon-greedy exploration before re-enabling structural memory influence on proposals |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Over-abstraction of topology model | Topology-as-data (Phase 1) — schema defined as concrete dataclass first | All 3 archetypes serialize to spawn config with no translation layer; no graph library imported |
| LLM proposal quality degrades silently | Structure proposal engine — constraint linter built before LLM integration | Linter catches invalid roles and out-of-bounds pool sizes; proposal ID is stored in every correction record |
| Correction loop instability | Dual correction system — cycle limit built before structural memory integration | Oscillating feedback test terminates in ≤3 cycles; contradictory feedback produces a trade-off surface, not a cycling proposal |
| Structural memory bloat | Structural memory — category exclusion and preference extraction format defined first | L3 SOUL contains no topology content; per-project structural memory count stays below 20 |
| Observability overhead on execution | Topology observability — storage location (separate file) defined before any writes | JarvisState lock wait stays <10ms with concurrent L3 containers; state file size delta per task lifecycle is <1KB |
| Backwards compatibility break | Topology-as-data (Phase 1) — all new schema fields are optional with defaults | All existing project.json files pass v2.0 validator before merge |
| Feedback loop locking in early mistakes | Structural memory — decay function and epsilon-greedy built before preference scoring influences proposals | 10 identical signals produce preference score <0.9; random 20% of sessions see randomized archetype ordering |
| Autonomy framework conflict | Structure proposal engine — interaction contract documented before implementation | `on_task_spawn()` not triggered during proposal phase; `topology.proposal_confidence_warning_threshold` is a separate config key from `autonomy.confidence_threshold` |

---

## Sources

- Direct codebase inspection: `packages/orchestration/src/openclaw/state_engine.py`, `skills/spawn/spawn.py`, `packages/orchestration/src/openclaw/autonomy/hooks.py`, `autonomy/types.py`, `autonomy/state.py`, `config.py`, `soul_renderer.py`, `project_config.py`, `packages/dashboard/src/lib/types.ts` — HIGH confidence
- v1.0–v1.6 architectural patterns from `CLAUDE.md`, `PROJECT.md`, `ROADMAP.md`, previous `PITFALLS.md` (v1.5) — HIGH confidence
- LLM structured output quality degradation: general knowledge of LLM-based structured generation failure modes; validation through constraint linting is the industry-standard mitigation — MEDIUM confidence (no external source; derived from known patterns in LLM integration)
- Feedback loop / recommendation system convergence failures: cold-start problem, preference reinforcement bias — well-documented in recommendation systems literature; epsilon-greedy exploration is the standard mitigation — MEDIUM confidence
- Correction system instability: oscillation in multi-round feedback systems is a known failure mode in interactive ML; termination conditions and cycle limits are the standard prevention — MEDIUM confidence
- Memory category isolation: derived from the existing `CATEGORY_SECTION_MAP` and `_format_memory_context()` pattern in `spawn.py` — HIGH confidence (codebase-derived)
- Autonomy framework confidence interaction: derived from `autonomy/types.py` (AutonomyState), `autonomy/hooks.py` (on_task_spawn), `config.py` (confidence_threshold) — HIGH confidence (codebase-derived)
- JarvisState lock contention analysis: derived from `fcntl.LOCK_EX` usage in `state_engine.py`, lock timeout constants in `config.py` — HIGH confidence (codebase-derived)
- Backwards compatibility schema validation: derived from `OPENCLAW_JSON_SCHEMA` and `PROJECT_JSON_SCHEMA` in `config.py` with `additionalProperties: False` — HIGH confidence (codebase-derived)

---
*Pitfalls research for: OpenClaw v2.0 Structural Intelligence — topology modeling, LLM-driven structure proposal, correction-as-training, structural observability*
*Researched: 2026-03-03*
