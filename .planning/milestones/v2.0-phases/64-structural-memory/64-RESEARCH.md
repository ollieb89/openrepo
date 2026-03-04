# Phase 64: Structural Memory - Research

**Researched:** 2026-03-03
**Domain:** Structural preference learning, exponential decay scoring, epsilon-greedy exploration, JSON file persistence, LLM-based pattern extraction, L3 memory isolation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**L3 Isolation Mechanism**
- Dual-layer enforcement: filter at memU query level (topology memories never returned for L3 queries) AND exclusion in spawn.py's CATEGORY_SECTION_MAP as defense-in-depth
- Three sub-typed memory categories for granular control: `structural_correction`, `structural_preference`, `structural_pattern` — all excluded from L3 retrieval
- If a structural memory somehow slips through to spawn layer: silent drop + log warning. Non-disruptive — L3 still spawns normally
- Verification: unit test that mocks spawn and asserts `_build_augmented_soul()` output contains zero topology content when structural memories exist. Fast, CI-friendly, no Docker required

**Pattern Extraction**
- LLM-based analysis: feed correction diffs + context to LLM, extract recurring structural preferences
- Trigger: threshold-triggered (every 5 corrections) AND on-demand via CLI command
- Minimum data threshold: 5 corrections before pattern extraction is meaningful
- Storage: dedicated `topology/patterns.json` file per project (array of patterns with timestamps, confidence, source correction IDs). Also tag changelog annotations with pattern IDs for traceability

**Preference Profile & Scoring**
- preference_fit calculation: archetype affinity as base score + pattern match as modifier
- Decay: exponential decay with configurable lambda. Weight = e^(-λ * age_in_days). Phase 61's 14-day relevance window informs the default lambda
- Exploration: epsilon-greedy with configurable rate via `topology.exploration_rate` config key. Default 20%
- Below minimum threshold (< 5 corrections): preference_fit stays at 5/10 neutral baseline
- Profile stored in `topology/memory-profile.json` per project

**Correction Storage & Reporting**
- Storage architecture: topology files only — no memU REST API for structural data
- Enrich existing changelog.json annotations AND maintain summary files:
  - `topology/memory-profile.json` — current preference profile, stats, threshold status
  - `topology/patterns.json` — extracted patterns with confidence and source references
  - `topology/changelog.json` — enriched annotations with pattern IDs and preference signals
- CLI: `openclaw-propose memory [--detail]` subcommand

### Claude's Discretion
- LLM prompt design for pattern extraction
- Exact exponential decay lambda default value
- Pattern confidence scoring algorithm
- memory-profile.json and patterns.json schema details
- Error handling for LLM failures during pattern extraction
- How enriched changelog annotations are structured internally

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SMEM-01 | System stores all topology correction diffs with timestamps, project context, and correction type (soft/hard) | `approve_topology()` already writes changelog entries with timestamp and correction_type; Phase 64 enriches those entries with pattern IDs and preference signals via the existing `annotations` dict |
| SMEM-02 | Structural memory is categorically isolated from L3 execution memory — topology data never appears in L3 SOUL injection | Add `structural_correction`, `structural_preference`, `structural_pattern` to `CATEGORY_SECTION_MAP` exclusion list in spawn.py; unit test verifies zero topology content in SOUL output |
| SMEM-03 | System extracts recurring patterns from accumulated corrections | New `topology/memory.py` module: `PatternExtractor` class calls LLM with changelog diffs; writes `patterns.json`; trigger is 5-correction threshold or on-demand CLI |
| SMEM-04 | System builds a user structural preference profile from correction history that influences the "preference fit" rubric score | New `MemoryProfiler` class reads changelog, computes archetype affinity with exponential decay, writes `memory-profile.json`; `RubricScorer.score_proposal()` reads profile to replace hardcoded `preference_fit = 5` |
| SMEM-05 | Preference profiling includes decay (older corrections weighted less) and exploration (epsilon-greedy to prevent archetype lock-in) | `math.exp(-lambda * age_days)` decay; epsilon-greedy randomizes archetype ordering 20% of the time during scoring; both configurable via `topology.decay_lambda` and `topology.exploration_rate` config keys |
| SMEM-06 | System can report correction count per project and whether preference profiling has reached minimum data threshold | `openclaw-propose memory` subcommand reads `memory-profile.json` and reports correction count, threshold status (active / below threshold), top patterns, archetype distribution |
</phase_requirements>

## Summary

Phase 64 builds the structural learning layer on top of the correction infrastructure from Phases 61-63. The codebase is already well-prepared: `approve_topology()` in approval.py writes changelog entries with a mutable `annotations` dict designed explicitly for Phase 64 enrichment, `TopologyDiff` has the same mutable annotations field, and `RubricScorer` already has a clearly-documented `preference_fit = 5` placeholder at line 101 in rubric.py with a comment pointing to Phase 64.

The implementation has three orthogonal concerns. First, enrichment: when `approve_topology()` fires, the correction record must be stored with project context and the diff must be tagged with preference signals. This is purely additive — the existing storage.py `append_changelog()` mechanism handles it with no structural changes. Second, preference profiling: a new `topology/memory.py` module reads the changelog, computes archetype affinity with exponential decay (`math.exp(-λ * age)`), applies epsilon-greedy exploration (20% randomization), and writes `memory-profile.json`. The `RubricScorer.score_proposal()` method then loads this profile to replace the hardcoded `5`. Third, L3 isolation: adding three category strings to `CATEGORY_SECTION_MAP` in spawn.py blocks structural memory from ever appearing in L3 SOUL context — the existing category routing system was designed for exactly this purpose.

**Primary recommendation:** Implement in three sequential modules — (1) `topology/memory.py` with `MemoryProfiler` and `PatternExtractor` classes, (2) a `memory` subcommand in `cli/propose.py`, and (3) a targeted edit to `rubric.py` replacing the hardcoded `preference_fit = 5`. The spawn.py isolation change is a two-line edit. All four pieces are independently testable with mocks.

## Standard Stack

### Core (existing — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `math` (stdlib) | stdlib | `math.exp()` for exponential decay | Zero dependency — exact fit for `e^(-λt)` |
| `json` (stdlib) | stdlib | patterns.json and memory-profile.json persistence | Already used throughout topology/ |
| `fcntl` (stdlib) | stdlib | File locking for new topology JSON files | Established Jarvis Protocol pattern in storage.py |
| `datetime` (stdlib) | stdlib | Timestamp parsing for age-in-days calculation | Already used in approval.py |
| `asyncio` (stdlib) | stdlib | `asyncio.run()` for pattern extraction LLM calls | Used by existing proposer.py pattern |
| `httpx` | existing dep | LLM calls for pattern extraction | Same client as llm_client.py; already in pyproject.toml |

### No New Dependencies Required

The entire phase uses only libraries already present in the orchestration package. The exponential decay and epsilon-greedy math is pure Python. The LLM calls reuse `topology/llm_client.py` via `call_llm()`. The storage pattern reuses `storage.py` functions. No `pip install` step needed.

## Architecture Patterns

### Recommended Project Structure

New files (all within existing `topology/` module):

```
packages/orchestration/src/openclaw/topology/
├── memory.py               # NEW: MemoryProfiler + PatternExtractor
└── (existing files unchanged except rubric.py — 1 method edit)

packages/orchestration/tests/
├── test_structural_memory.py    # NEW: unit tests for memory.py
└── test_spawn_isolation.py      # NEW: L3 isolation unit test

packages/orchestration/src/openclaw/cli/
└── propose.py              # EDIT: add `memory` subcommand
```

New topology files (runtime, per-project):

```
workspace/.openclaw/{project_id}/topology/
├── changelog.json          # EXISTING — enriched with pattern_ids in annotations
├── memory-profile.json     # NEW — archetype affinity, correction count, threshold status
└── patterns.json           # NEW — extracted patterns with confidence and source refs
```

### Pattern 1: Exponential Decay Weighting

**What:** Weight each correction record by `e^(-λ * age_in_days)` before accumulating affinity scores. Older corrections contribute less. Lambda controls the half-life: `half_life = ln(2) / λ`.

**When to use:** Computing `archetype_affinity` in `MemoryProfiler.compute_profile()`.

**Recommended lambda default:** `0.05` gives a half-life of ~14 days (`ln(2) / 0.05 ≈ 13.9`), consistent with the 14-day relevance window decision recorded in STATE.md.

```python
import math
from datetime import datetime, timezone

def _decay_weight(timestamp_iso: str, decay_lambda: float) -> float:
    """Compute e^(-λ * age_in_days) for a correction timestamp."""
    try:
        ts = datetime.fromisoformat(timestamp_iso)
        now = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_days = (now - ts).total_seconds() / 86400.0
        return math.exp(-decay_lambda * age_days)
    except (ValueError, TypeError):
        return 1.0  # Unknown age: treat as current
```

### Pattern 2: Epsilon-Greedy Archetype Ordering

**What:** During `score_proposal()`, 20% of the time (epsilon = 0.2) randomize archetype ordering before returning preference_fit scores, preventing lock-in on early archetype preferences. 80% of the time use the learned affinity order.

**When to use:** In `RubricScorer.score_proposal()` after loading preference profile.

**Critical detail:** The epsilon-greedy must be applied at scoring time, not at storage time. This means `score_proposal()` needs access to `random.random()`, which makes the output non-deterministic. Tests must mock `random.random` or test the two branches separately.

```python
import random

def _apply_exploration(archetype: str, profile: dict, exploration_rate: float) -> float:
    """Return preference_fit for this archetype with epsilon-greedy exploration."""
    if random.random() < exploration_rate:
        # Exploration: random ordering — return midpoint (5) to flatten preferences
        return 5.0
    # Exploitation: return learned affinity score
    affinities = profile.get("archetype_affinity", {})
    return affinities.get(archetype, 5.0)
```

### Pattern 3: Archetype Affinity Calculation

**What:** For each correction in changelog, extract `correction_type` and the approved archetype (from the `current.json` topology's archetype classification). Hard corrections against an archetype reduce its affinity; approvals increase it.

**Signal mapping:**
- `initial` approval (no prior topology) → +1.0 × decay_weight to approved archetype
- `soft` approval → +0.5 × decay_weight to approved archetype (user accepted after feedback)
- `hard` approval → +1.0 × decay_weight to approved archetype, -0.5 × decay_weight to proposed archetypes that were rejected

**Base score normalization:** After summing signals, normalize to [0, 10] range. If all archetypes have zero signal, return 5.0 (neutral).

### Pattern 4: Pattern Extraction via LLM

**What:** Feed the last N correction diffs to the LLM with a structured prompt. LLM returns JSON array of extracted patterns. Merge with existing patterns.json (deduplicate by semantic similarity — LLM can flag duplicates in the prompt).

**Trigger condition:** Extract when `correction_count % 5 == 0` (every 5 corrections) or on-demand via CLI.

**Prompt structure (Claude's discretion area — recommended approach):**

```python
PATTERN_EXTRACTION_SYSTEM = """You are a structural preference analyst for an AI swarm orchestration system.
You analyze topology correction history to identify recurring human preferences about agent structure.

Return a JSON array of pattern objects. Each pattern has:
- "pattern": string describing the preference in plain English (e.g., "user flattens hierarchies for low-complexity tasks")
- "confidence": float 0.0-1.0 (how strongly supported by evidence)
- "source_correction_ids": list of correction timestamps that support this pattern
- "archetype_bias": "lean" | "balanced" | "robust" | null (if pattern favors an archetype)

Return only the JSON array. No prose."""

PATTERN_EXTRACTION_USER = """Analyze these {n} topology corrections for project '{project_id}'.

Existing patterns (avoid exact duplicates):
{existing_patterns}

Correction history:
{correction_diffs}

Extract 1-5 recurring structural preferences. Return empty array [] if patterns are unclear."""
```

**Error handling:** LLM failures must not block the approval flow. Pattern extraction runs synchronously in the CLI command path but is non-blocking for the correction storage path. On failure: log warning, keep existing patterns.json unchanged.

### Pattern 5: CLI Subcommand Structure

**What:** Add `memory` as a subcommand to `openclaw-propose` using `argparse` subparsers, consistent with the project's CLI pattern (single entry point, subcommands via argparse).

**How to integrate:** The existing `propose.py` main() uses `argparse.ArgumentParser`. Add a subparser for `memory` with an optional `--detail` flag. When invoked as `openclaw-propose memory`, skip the proposal generation entirely and print the memory report.

```python
# In propose.py main() — before existing argument parsing
if len(sys.argv) > 1 and sys.argv[1] == "memory":
    return _run_memory_report(sys.argv[2:])

# Or via subparsers:
subparsers = parser.add_subparsers(dest="subcommand")
memory_parser = subparsers.add_parser("memory", help="Show structural memory report")
memory_parser.add_argument("--detail", action="store_true", help="Full breakdown")
```

**Recommended approach:** Simple `sys.argv[1] == "memory"` check early in `main()` to avoid refactoring the full argparse structure — consistent with how `approve.py` duplicates minimal logic rather than sharing across CLIs.

### Pattern 6: Storage Extension (new files in storage.py)

**What:** Add `save_memory_profile()`, `load_memory_profile()`, `save_patterns()`, `load_patterns()` to `storage.py` following the exact same `fcntl` + `tmp/rename` atomic write pattern as `save_topology()` and `save_pending_proposals()`.

**Pattern to follow (from storage.py):**

```python
def save_memory_profile(project_id: str, profile: dict) -> None:
    """Persist memory profile to memory-profile.json using atomic write."""
    topo_dir = _topology_dir(project_id)
    profile_path = topo_dir / "memory-profile.json"
    tmp_path = topo_dir / "memory-profile.json.tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            json.dump(profile, f, indent=2)
            f.flush()
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    tmp_path.rename(profile_path)

def load_memory_profile(project_id: str) -> dict:
    """Load memory profile. Returns empty dict with defaults if not found."""
    topo_dir = _topology_dir(project_id)
    profile_path = topo_dir / "memory-profile.json"
    if not profile_path.exists():
        return _default_memory_profile()
    with open(profile_path, "r", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            return json.load(f)
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

### Anti-Patterns to Avoid

- **Using memU REST API for structural data:** Locked decision — all structural memory lives in topology/ files only. Never call `memory_client.store()` for structural categories.
- **Blocking approve_topology() on LLM calls:** Pattern extraction triggers async/on-demand. Never call LLM inside `approve_topology()` — it must remain fast and synchronous.
- **Hardcoding lambda in the decay function:** Must read from `get_topology_config()` using the `topology.decay_lambda` key (falling back to 0.05 default). Tests must be able to override via config mock.
- **Making preference_fit non-deterministic in tests without mocking:** `random.random()` in `score_proposal()` makes tests flaky. Always mock it in unit tests — test the exploration branch and exploitation branch separately.
- **Loading memory-profile.json on every `score_proposal()` call:** Cache the profile in the `RubricScorer` instance or pass it as an argument. Repeated disk reads inside a tight scoring loop (e.g., scoring 3 proposals) are unnecessary.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File locking | Custom lock class | `fcntl.flock()` pattern from storage.py | Already battle-tested with .tmp+rename atomic writes |
| Exponential decay | Custom decay framework | `math.exp(-λ * t)` one-liner | Standard formula, zero overhead, fully testable |
| LLM calls | New HTTP client | `topology.llm_client.call_llm()` | Already handles Anthropic + Gemini, timeout, key env vars |
| JSON schema validation | Custom validator | `@dataclass` with `to_dict()` / class method `_default_memory_profile()` | Consistent with all existing topology models |
| CLI subcommand | New entry point | Add subparser to existing `openclaw-propose` | Locked decision — `propose memory` not a new command |
| Atomic file writes | `open(path, 'w')` direct write | `tmp_path = path.with_suffix('.tmp')` + rename | Crash safety — established in storage.py lines 64-72 |

## Common Pitfalls

### Pitfall 1: Archetype Not Stored in Changelog

**What goes wrong:** The existing `approve_topology()` stores the diff and correction_type but does NOT store which archetype was approved. The `MemoryProfiler` needs the approved archetype to update affinity scores.

**Why it happens:** Archetype is a property of the proposal, not the topology graph. The `TopologyGraph` dataclass does not carry an archetype field.

**How to avoid:** Two options: (a) enrich the changelog entry in `approve_topology()` with `archetype` in `annotations`, requiring the caller to pass it; (b) re-classify the approved topology using `ArchetypeClassifier` during profile computation. Option (b) is cleaner — no API change to `approve_topology()` — and `ArchetypeClassifier.classify()` is already tested and fast (pure computation, no I/O).

**Warning signs:** If `memory-profile.json` shows all affinities stuck at 5/10, the archetype extraction is failing silently.

### Pitfall 2: Changelog Entries Before Phase 64 Have No Correction Context

**What goes wrong:** Existing changelog entries from Phases 61-63 have `annotations: {}` or minimal annotations. The `MemoryProfiler` must handle entries that lack enriched fields gracefully.

**How to avoid:** `load_changelog()` returns raw dicts. Treat missing fields as neutral signals — skip entries where the annotation enrichment is absent rather than crashing. Use `.get()` with safe defaults throughout profile computation.

### Pitfall 3: Epsilon-Greedy Breaks Proposal Comparison

**What goes wrong:** If epsilon-greedy randomizes preference_fit scores during `score_proposal()`, then the comparative rubric (which ranks proposals against each other) becomes inconsistent — the relative ordering of archetypes changes between calls in the same session.

**How to avoid:** Epsilon-greedy must randomize the archetype ordering uniformly within a single scoring session, not independently per proposal. The right approach: draw a single random number for the session. If `random.random() < epsilon`, return `preference_fit = 5` for ALL proposals (neutral — no differentiation). Otherwise, use the learned profile for ALL proposals.

This preserves the comparative integrity of the rubric while still implementing exploration.

### Pitfall 4: Pattern Extraction Prompt Costs Tokens on Sparse Data

**What goes wrong:** Calling LLM for pattern extraction when there are only 5 corrections (the minimum threshold) wastes tokens and may produce low-quality patterns from insufficient signal.

**How to avoid:** The threshold of 5 is already the minimum, but the prompt should explicitly communicate confidence expectations to the LLM. Include "Return empty array [] if patterns are unclear" in the prompt. On the Python side, discard patterns with `confidence < 0.4` to avoid polluting patterns.json with weak inferences.

### Pitfall 5: `get_topology_config()` Does Not Yet Return New Config Keys

**What goes wrong:** `get_topology_config()` in config.py currently returns only `proposal_confidence_warning_threshold`, `rubric_weights`, `auto_approve_l1`, and `pushback_threshold`. Phase 64 needs `exploration_rate`, `decay_lambda`, and `pattern_extraction_threshold` — but these keys don't exist in the function yet.

**How to avoid:** Must extend `get_topology_config()` to include:
```python
"exploration_rate": topology.get("exploration_rate", 0.20),
"decay_lambda": topology.get("decay_lambda", 0.05),
"pattern_extraction_threshold": topology.get("pattern_extraction_threshold", 5),
```
This is a small edit but is a prerequisite for all other work — tests that mock config will fail otherwise.

### Pitfall 6: `_build_augmented_soul()` Signature Differs Between Test and Production

**What goes wrong:** `test_spawn_memory.py` shows `_build_augmented_soul(tmp_path, memory_context)` with 2 args, but the production spawn.py shows `_build_augmented_soul(project_root, memory_context, project_id, agent_id)` with 4 args. The isolation test must use the correct production signature.

**How to avoid:** Review the actual spawn.py signature before writing the isolation test. Use `_build_augmented_soul(project_root, memory_context, project_id, "l3_specialist")` in the test.

## Code Examples

### memory-profile.json Schema

```json
{
  "project_id": "pumplai",
  "correction_count": 7,
  "soft_correction_count": 3,
  "hard_correction_count": 4,
  "threshold_status": "active",
  "archetype_affinity": {
    "lean": 6.8,
    "balanced": 5.2,
    "robust": 3.1
  },
  "last_computed": "2026-03-03T19:00:00Z",
  "active_pattern_ids": ["pat-20260301-001", "pat-20260303-002"]
}
```

### patterns.json Schema

```json
[
  {
    "id": "pat-20260301-001",
    "pattern": "user flattens hierarchies for low-complexity tasks",
    "confidence": 0.78,
    "archetype_bias": "lean",
    "source_correction_ids": [
      "2026-02-28T14:00:00+00:00",
      "2026-03-01T09:30:00+00:00",
      "2026-03-01T15:00:00+00:00"
    ],
    "extracted_at": "2026-03-01T20:00:00Z"
  }
]
```

### Enriched Changelog Annotation

```json
{
  "timestamp": "2026-03-03T19:00:00+00:00",
  "correction_type": "hard",
  "diff": { ... },
  "annotations": {
    "pushback_note": "",
    "approved_archetype": "lean",
    "preference_signal": "positive",
    "pattern_ids": ["pat-20260301-001"]
  }
}
```

### L3 Isolation: CATEGORY_SECTION_MAP Extension (spawn.py)

```python
# Existing:
CATEGORY_SECTION_MAP = {
    "review_decision": "Past Review Outcomes",
    "task_outcome": "Task Outcomes",
}

# Phase 64 addition — structural categories are excluded by NOT being in the map.
# The map only routes items INTO L3 SOUL sections.
# Items NOT in the map go to "Past Work Context" by default.
# Solution: add structural categories to an explicit EXCLUDED_CATEGORIES set:

EXCLUDED_CATEGORIES = frozenset({
    "structural_correction",
    "structural_preference",
    "structural_pattern",
})

# In _format_memory_context(), before the CATEGORY_SECTION_MAP routing:
if category in EXCLUDED_CATEGORIES:
    logger.warning("Structural memory item reached spawn layer — dropping (project=%s)", ...)
    continue
```

### Preference Fit Integration in rubric.py

```python
# Replace hardcoded preference_fit = 5 with:
def _get_preference_fit(
    archetype: str,
    project_id: str,
    exploration_rate: float,
    decay_lambda: float,
) -> int:
    """Load memory profile and compute preference_fit for archetype."""
    from openclaw.topology.storage import load_memory_profile
    profile = load_memory_profile(project_id)
    if profile.get("threshold_status") != "active":
        return 5  # Below threshold — neutral baseline
    if random.random() < exploration_rate:
        return 5  # Exploration — neutral to prevent lock-in
    affinities = profile.get("archetype_affinity", {})
    raw = affinities.get(archetype, 5.0)
    return _clamp(round(raw))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `preference_fit = 5` (hardcoded) | Computed from correction history with decay | Phase 64 | Proposals adapt to user structural preferences |
| No pattern extraction | LLM extracts recurring structural insights | Phase 64 | System "learns" and can report insights |
| L3 isolation not enforced | Dual-layer: EXCLUDED_CATEGORIES + spawn filter | Phase 64 | Topology data never contaminates L3 context |
| Changelog annotations empty | Enriched with archetype, pattern IDs, signals | Phase 64 | Full traceability from correction to pattern |

## Open Questions

1. **Where to call `MemoryProfiler.recompute()`?**
   - What we know: Profile must be recomputed after each correction to keep `preference_fit` current. But `approve_topology()` is the natural trigger point, and it currently has no knowledge of `MemoryProfiler`.
   - What's unclear: Whether to call recompute inside `approve_topology()` (tighter coupling) or have the CLI layer call it after approval returns (looser coupling, but requires CLI to always call it).
   - Recommendation: Call `MemoryProfiler.recompute(project_id)` at the end of `approve_topology()` — it's a pure file operation (no LLM), fast, and ensures profile is always current when the next `score_proposal()` runs.

2. **How does `score_proposal()` get `archetype` and `project_id`?**
   - What we know: `RubricScorer.score_proposal(topology, weights)` currently takes only topology and weights. Computing preference_fit dynamically requires knowing the archetype and project_id.
   - What's unclear: The `TopologyGraph` has `project_id` but not `archetype`. The archetype is determined by `ArchetypeClassifier` after scoring.
   - Recommendation: Extend `score_proposal()` signature to `score_proposal(topology, weights, project_id=None, archetype=None)`. When both are None, return neutral `5`. In `propose.py` and `approve.py`, the archetype is known from the proposal — pass it through.

3. **Pattern deduplication across extraction runs**
   - What we know: Pattern extraction runs every 5 corrections, producing new patterns. Without deduplication, patterns.json fills with near-duplicates over time.
   - What's unclear: Whether LLM-level deduplication (pass existing patterns in prompt) is reliable enough or if a Python-side deduplication pass is needed.
   - Recommendation: Use LLM-level deduplication as primary (include existing patterns in prompt). Add a Python-side guard: if `len(patterns.json) > 20`, prune to top-10 by confidence before extracting new patterns.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 7.0 |
| Config file | none — discovered automatically |
| Quick run command | `uv run pytest packages/orchestration/tests/test_structural_memory.py -x` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SMEM-01 | Correction diffs stored with timestamp, project_id, correction_type | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_correction_stored_with_metadata -x` | Wave 0 |
| SMEM-01 | Corrections retrievable by project | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_corrections_retrievable_by_project -x` | Wave 0 |
| SMEM-02 | structural_* categories excluded from L3 SOUL | unit | `uv run pytest packages/orchestration/tests/test_spawn_isolation.py::test_structural_categories_excluded_from_soul -x` | Wave 0 |
| SMEM-02 | Structural memory does not appear in `_build_augmented_soul()` output | unit | `uv run pytest packages/orchestration/tests/test_spawn_isolation.py::test_augmented_soul_has_no_topology_content -x` | Wave 0 |
| SMEM-03 | Pattern extraction returns patterns when threshold met | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_pattern_extraction_above_threshold -x` | Wave 0 |
| SMEM-03 | Pattern extraction returns empty below threshold | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_pattern_extraction_below_threshold -x` | Wave 0 |
| SMEM-04 | preference_fit reflects archetype affinity from profile | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_preference_fit_uses_profile -x` | Wave 0 |
| SMEM-04 | preference_fit returns 5 when below threshold | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_preference_fit_neutral_below_threshold -x` | Wave 0 |
| SMEM-05 | Older corrections weighted less than recent ones | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_decay_weights_older_corrections_less -x` | Wave 0 |
| SMEM-05 | Epsilon-greedy returns neutral 20% of the time (mocked random) | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_epsilon_greedy_exploration -x` | Wave 0 |
| SMEM-06 | Memory report shows correct correction count | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_memory_report_correction_count -x` | Wave 0 |
| SMEM-06 | Memory report shows threshold status | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_memory_report_threshold_status -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest packages/orchestration/tests/test_structural_memory.py packages/orchestration/tests/test_spawn_isolation.py -x`
- **Per wave merge:** `uv run pytest packages/orchestration/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `packages/orchestration/tests/test_structural_memory.py` — covers SMEM-01, SMEM-03, SMEM-04, SMEM-05, SMEM-06
- [ ] `packages/orchestration/tests/test_spawn_isolation.py` — covers SMEM-02

*(Existing `test_spawn_memory.py` and `test_correction.py` provide context for test structure patterns but do not cover Phase 64 requirements.)*

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `/home/ob/Development/Tools/openrepo/packages/orchestration/src/openclaw/topology/` — full module read including storage.py, rubric.py, diff.py, correction.py, approval.py, proposal_models.py, llm_client.py
- Direct code inspection: `/home/ob/Development/Tools/openrepo/skills/spawn/spawn.py` — CATEGORY_SECTION_MAP, `_format_memory_context()`, `_build_augmented_soul()` (lines 217-300)
- Direct code inspection: `/home/ob/Development/Tools/openrepo/packages/orchestration/tests/test_spawn_memory.py` — established test patterns for spawn isolation
- Project context: `.planning/phases/64-structural-memory/64-CONTEXT.md` — all locked decisions verified

### Secondary (MEDIUM confidence)

- Epsilon-greedy algorithm pattern: standard bandit algorithm; lambda decay formula is textbook exponential decay — both verified by implementation (math.exp is stdlib, random.random is stdlib)

### Tertiary (LOW confidence)

- LLM prompt structure for pattern extraction: recommended based on existing proposer.py prompt patterns; exact prompt wording is Claude's discretion

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing project dependencies, confirmed via pyproject.toml
- Architecture patterns: HIGH — directly derived from reading existing storage.py, rubric.py, spawn.py code
- Pitfalls: HIGH — identified from direct code inspection of actual integration points
- LLM prompt design: LOW — Claude's discretion area, no existing pattern to verify against

**Research date:** 2026-03-03
**Valid until:** 2026-04-03 (stable codebase — no external dependency churn risk)
