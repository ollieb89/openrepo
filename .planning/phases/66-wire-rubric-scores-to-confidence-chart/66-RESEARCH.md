# Phase 66: Wire Rubric Scores to Confidence Chart — Research

**Researched:** 2026-03-04
**Domain:** Python backend wiring (approval.py, propose.py, approve.py) + existing TypeScript frontend (ConfidenceChart)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Include rubric scores for ALL 3 archetypes (lean/balanced/robust) in each changelog entry — not just the approved one
- CLI callers extract a pre-built `{archetype: RubricScore}` dict from the ProposalSet and pass it to `approve_topology()` — keeps approve_topology decoupled from ProposalSet
- Omit archetypes that have no rubric_score (don't include zeros) — ConfidenceChart already handles sparse data gracefully
- Auto re-score edited topologies using `score_proposal()` before writing to changelog on hard correction
- Score the edited graph under all 3 archetypes on hard correction
- No migration / backfill needed — ConfidenceChart graceful empty state already handled

### Claude's Discretion

- Exact parameter name and type for rubric_scores on approve_topology()
- Whether to store scoring weights in changelog entries for reproducibility
- How to handle edge cases (e.g., score_proposal failure during hard correction — likely skip gracefully)
- Test structure and coverage approach

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TOBS-05 | Dashboard shows confidence evolution — how proposal confidence scores changed across correction cycles | All three success criteria combine to produce populated `annotations.rubric_scores` in changelog entries, which ConfidenceChart already reads via `transformChangelogToChartData()` |
</phase_requirements>

---

## Summary

Phase 66 is a pure backend wiring task — no frontend changes required. The TypeScript contract (`ChangelogAnnotations.rubric_scores`, `transformChangelogToChartData()`, `ConfidenceChart`) is already fully implemented and tested. The gap is entirely in the Python approval pathway: `approve_topology()` does not accept rubric scores, and its two CLI callers (`propose.py` and `approve.py`) never pass them.

The fix spans three Python files and their tests. `approve_topology()` needs one new optional parameter (`rubric_scores: Optional[dict] = None`) that gets written into `annotations["rubric_scores"]` before the changelog entry is built. `propose.py` needs to extract scores from the `ProposalSet` (all 3 archetypes, omitting `None`) and pass them at both approval sites (normal approval and hard-correction approval). `approve.py` needs to do the same at its single approval site. The hard-correction path additionally needs to re-score the edited graph under all 3 archetypes using `score_proposal()` before building the scores dict.

**Primary recommendation:** Add `rubric_scores: Optional[dict] = None` to `approve_topology()`, write it to annotations conditionally, then update both CLI callers to build and pass the dict. Hard correction in `propose.py` gets additional re-scoring logic.

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| `approve_topology()` | `topology/approval.py` | Entry point for changelog writes | Needs rubric_scores param |
| `score_proposal()` | `topology/rubric.py` | Standalone scorer function | Already used in propose.py |
| `RubricScore.to_dict()` | `topology/proposal_models.py` | Serialization to JSON-safe dict | Already exists |
| `ProposalSet.proposals` | `topology/proposal_models.py` | Source of rubric_scores at approval time | Available at both call sites |
| `DEFAULT_WEIGHTS` | `topology/rubric.py` | Fallback weights when config unavailable | Available |
| `ConfidenceChart` | `dashboard/src/components/topology/ConfidenceChart.tsx` | Renders rubric_scores from changelog | Already wired — no changes |
| `transformChangelogToChartData()` | Same file | Transforms changelog to chart data points | Already wired — no changes |

**No new packages to install.**

---

## Architecture Patterns

### Recommended Project Structure (no changes to structure)

All changes are within existing files:

```
packages/orchestration/src/openclaw/
├── topology/
│   └── approval.py          # Add rubric_scores param + annotations write
├── cli/
│   ├── propose.py           # Build scores dict, pass at 2 approval sites
│   └── approve.py           # Build scores dict, pass at 1 approval site
packages/orchestration/tests/
├── test_approval.py         # Add rubric_scores tests
├── test_cli_propose.py      # Add rubric_scores passing tests
└── test_cli_approve.py      # Add rubric_scores passing tests
```

### Pattern 1: approve_topology() Signature Extension

**What:** Add one optional kwarg following the existing `pushback_note` pattern.
**When to use:** Every call site passes it; the function conditionally writes it to annotations.

```python
# Source: packages/orchestration/src/openclaw/topology/approval.py
def approve_topology(
    project_id: str,
    approved_graph: TopologyGraph,
    correction_type: str,
    pushback_note: str = "",
    rubric_scores: Optional[dict] = None,   # NEW — {archetype: RubricScore.to_dict()}
) -> dict:
    ...
    annotations: dict = {}
    if pushback_note:
        annotations["pushback_note"] = pushback_note
    if rubric_scores:                        # NEW — only write when present
        annotations["rubric_scores"] = rubric_scores
    # approved_archetype enrichment already below
```

### Pattern 2: Scores Dict Construction at Call Sites

**What:** Build `{archetype: score.to_dict()}` from ProposalSet, omitting None scores.
**When to use:** At every `approve_topology()` call in propose.py and approve.py.

```python
# Source: packages/orchestration/src/openclaw/cli/propose.py
# Build rubric_scores dict from current proposal_set
rubric_scores = {
    p.archetype: p.rubric_score.to_dict()
    for p in session.proposal_set.proposals
    if p.rubric_score is not None
}
entry = approve_topology(
    session.project_id,
    selected.topology,
    correction_type,
    pushback,
    rubric_scores,      # NEW positional or keyword arg
)
```

In `approve.py` the ProposalSet is loaded from `load_pending_proposals()` and reconstructed via `ProposalSet.from_dict()` — `rubric_score` fields survive deserialization because `TopologyProposal.from_dict()` already handles them.

### Pattern 3: Hard Correction Re-scoring

**What:** After import_draft() succeeds, score the edited graph under all 3 archetypes before approving.
**When to use:** Hard correction path in `_run_session()`, lines ~306-320 in propose.py.

```python
# Source: packages/orchestration/src/openclaw/cli/propose.py (hard correction block)
# After import_draft succeeds:
rubric_scores = {}
try:
    archetypes = ["lean", "balanced", "robust"]
    for arch in archetypes:
        score = score_proposal(
            graph, weights,
            project_id=session.project_id,
            archetype=arch,
        )
        rubric_scores[arch] = score.to_dict()
except Exception:
    pass  # Graceful degradation — chart stays empty for this entry

entry = approve_topology(
    session.project_id,
    graph,
    "hard",
    pushback,
    rubric_scores or None,  # Pass None if scoring failed entirely
)
```

Note: `explore` flag is not passed during re-scoring on approval — use default (no exploration) since we are scoring for recording, not ranking.

### Anti-Patterns to Avoid

- **Passing `{}` (empty dict) instead of `None`:** The `if rubric_scores:` guard in `approve_topology()` must treat both empty dict and None identically — pass `rubric_scores or None` at call sites so the annotations key is simply omitted when no scores are available.
- **Importing from ProposalSet inside approve_topology():** The context CONTEXT.md explicitly requires decoupling. `approve_topology()` accepts a plain `dict`, never a ProposalSet.
- **Re-scoring using `selected.rubric_score` on hard correction:** The edited graph may differ structurally from the selected proposal — always re-score the imported graph, not the pre-edit proposal's existing score.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scores serialization | Custom dict walk | `RubricScore.to_dict()` | Already exists, handles all 7 fields + key_differentiators |
| Scores deserialization | Custom parsing | `RubricScore.from_dict()` | Already exists, round-trips cleanly |
| Hard-correction scoring | Inline scoring logic | `score_proposal()` standalone wrapper | Already used in propose.py, handles DEFAULT_WEIGHTS, project_id, archetype, explore params |
| Frontend chart rendering | Any TS changes | None — ConfidenceChart already reads `annotations.rubric_scores` | `transformChangelogToChartData()` and all chart tests already pass with rubric_scores data |

**Key insight:** The frontend contract is completely implemented. Zero TypeScript changes are needed. This phase closes the gap purely by populating data the frontend already knows how to consume.

---

## Common Pitfalls

### Pitfall 1: Hard Correction Scores the Pre-Edit Graph

**What goes wrong:** Developer calls `score_proposal(selected.topology, ...)` instead of `score_proposal(graph, ...)` after import.
**Why it happens:** `selected` is the pre-edit proposal — it's already in scope and has a `rubric_score`. Tempting to reuse.
**How to avoid:** Always score `graph` (the imported result), not `selected.topology`.
**Warning signs:** Tests passing locally but chart showing identical scores before/after hard edit.

### Pitfall 2: rubric_scores Written as `{}` to Changelog

**What goes wrong:** `annotations["rubric_scores"] = {}` when all proposals lacked scores — ConfidenceChart skips entries with `!rubricScores` but `{}` is truthy.
**Why it happens:** Building the scores dict might produce an empty dict if all rubric_scores were None.
**How to avoid:** Use `rubric_scores or None` at call sites; the guard in approve_topology is `if rubric_scores:` which skips both `None` and `{}`.
**Warning signs:** Chart showing data points with undefined/zero archetype values.

### Pitfall 3: explore Flag During Hard-Correction Re-scoring

**What goes wrong:** Passing `explore=True` draws from epsilon-greedy when re-scoring — could produce neutral preference_fit (5) rather than learned preference.
**Why it happens:** Session has an `explore` flag drawn at session start; developer reuses it for re-scoring.
**How to avoid:** Do not pass `explore` (defaults to None/False) when scoring for recording purposes. The explore flag is for proposal ranking, not archetype scoring for storage.
**Warning signs:** preference_fit always = 5 in chart even after sufficient corrections.

### Pitfall 4: approve.py Correction Type

**What goes wrong:** `approve.py` passes `correction_type="soft"` when it should be the correction type from the saved ProposalSet or a default.
**Why it happens:** The ProposalSet loaded from pending-proposals doesn't carry a correction_type hint.
**How to avoid:** The existing code already uses `"initial"` as the hardcoded correction_type for `approve.py` (line 167). Keep this unchanged — it's correct for the resume-approval flow.
**Warning signs:** Chart entries from `openclaw-approve` showing `correction_type: "soft"`.

---

## Code Examples

Verified patterns from the actual codebase:

### Current approve_topology() Call Sites (before change)

```python
# Source: packages/orchestration/src/openclaw/cli/propose.py line 242-247
# Normal approval:
entry = approve_topology(
    session.project_id,
    selected.topology,
    correction_type,
    pushback,
)

# Source: packages/orchestration/src/openclaw/cli/propose.py line 316-321
# Hard correction:
entry = approve_topology(
    session.project_id,
    graph,
    "hard",
    pushback,
)

# Source: packages/orchestration/src/openclaw/cli/approve.py line 167-172
approve_topology(
    project_id,
    selected.topology,
    "initial",
    pushback,
)
```

### RubricScore Serialization (verified from proposal_models.py)

```python
# Source: packages/orchestration/src/openclaw/topology/proposal_models.py
score = RubricScore(complexity=7, coordination_overhead=8, ...)
score.to_dict()
# Returns: {"complexity": 7, "coordination_overhead": 8, "risk_containment": ...,
#           "time_to_first_output": ..., "cost_estimate": ...,
#           "preference_fit": ..., "overall_confidence": ..., "key_differentiators": []}
```

### ProposalSet Scores Dict Construction Pattern

```python
# Produces: {"lean": {...}, "balanced": {...}, "robust": {...}}
# Omits archetypes with no rubric_score
rubric_scores = {
    p.archetype: p.rubric_score.to_dict()
    for p in proposal_set.proposals
    if p.rubric_score is not None
} or None
```

### TypeScript Contract (already implemented — no changes needed)

```typescript
// Source: packages/dashboard/src/lib/types/topology.ts
export interface ChangelogAnnotations {
  approved_archetype?: string;
  pushback_note?: string;
  rubric_scores?: Record<string, RubricScore>;  // Already typed
  [key: string]: unknown;
}

// Source: packages/dashboard/src/components/topology/ConfidenceChart.tsx
// transformChangelogToChartData() already reads annotations.rubric_scores
// Tests in packages/dashboard/tests/topology/confidence.test.ts — all passing
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pushback_note as only annotation | annotations dict with multiple keys | Phase 63 | Pattern to follow — rubric_scores is another annotations key |
| preference_fit = 5 always | Dynamic preference_fit from MemoryProfiler | Phase 64 | Must pass project_id + archetype to score_proposal() for dynamic scores |
| No rubric_scores in changelog | rubric_scores in annotations (phase 66) | Phase 66 | Closes TOBS-05 |

**Deprecated/outdated:**

- None — all patterns are current.

---

## Open Questions

1. **Whether to store weights alongside scores in changelog entries**
   - What we know: `score_proposal()` uses `DEFAULT_WEIGHTS` when `{}` is passed; topo_config carries configurable `rubric_weights`; no current mechanism stores weights in changelog
   - What's unclear: Whether a future change to rubric weights would make historical scores uninterpretable without stored weights (reproducibility)
   - Recommendation (Claude's discretion): Skip weights storage for now. The planner can include a `_scoring_weights` key in annotations as an optional addition if the planner judges it low-cost. The benefit is marginal — weights are global defaults and rarely changed.

2. **Score context: project_id and archetype for hard correction re-scoring**
   - What we know: `score_proposal()` accepts `project_id` and `archetype` kwargs for dynamic preference_fit; the session knows project_id; after hard correction the archetype is the selected proposal's archetype (though the graph may differ structurally)
   - What's unclear: Whether to pass all 3 archetypes' names when re-scoring all 3 (lean/balanced/robust) or use the edited graph's classified archetype
   - Recommendation: Pass the archetype name as the label when scoring each variant (e.g., score under "lean" weights means passing `archetype="lean"`). This gives the MemoryProfiler the correct signal per archetype. Keep `explore=False` (no exploration on recording).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest 9.0.2 (from pyc cache evidence) |
| Python config | `packages/orchestration/` with `uv run pytest` |
| Quick run command | `uv run pytest packages/orchestration/tests/test_approval.py packages/orchestration/tests/test_cli_propose.py packages/orchestration/tests/test_cli_approve.py -x` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |
| TypeScript framework | vitest (packages/dashboard/vitest.config.ts) |
| TS test location | `packages/dashboard/tests/**/*.test.ts` |
| TS quick run | `cd packages/dashboard && pnpm vitest run tests/topology/confidence.test.ts` |
| TS full run | `cd packages/dashboard && pnpm vitest run` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOBS-05-A | `approve_topology()` accepts rubric_scores param and writes to annotations | unit | `uv run pytest packages/orchestration/tests/test_approval.py -x` | Yes (extend existing) |
| TOBS-05-B | propose.py normal approval passes rubric_scores dict | unit | `uv run pytest packages/orchestration/tests/test_cli_propose.py -x` | Yes (extend existing) |
| TOBS-05-C | propose.py hard correction re-scores and passes rubric_scores | unit | `uv run pytest packages/orchestration/tests/test_cli_propose.py -x` | Yes (extend existing) |
| TOBS-05-D | approve.py passes rubric_scores from loaded pending proposals | unit | `uv run pytest packages/orchestration/tests/test_cli_approve.py -x` | Yes (extend existing) |
| TOBS-05-E | transformChangelogToChartData renders non-zero points with rubric_scores | unit | `cd packages/dashboard && pnpm vitest run tests/topology/confidence.test.ts` | Yes (already passes with fixture data) |

### Sampling Rate

- **Per task commit:** `uv run pytest packages/orchestration/tests/test_approval.py packages/orchestration/tests/test_cli_propose.py packages/orchestration/tests/test_cli_approve.py -x`
- **Per wave merge:** `uv run pytest packages/orchestration/tests/ -v`
- **Phase gate:** Full Python suite green + TS confidence test green before `/gsd:verify-work`

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. The TS confidence tests (`confidence.test.ts`) already exist and pass. The Python test files exist and are the correct extension points.

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `packages/orchestration/src/openclaw/topology/approval.py` — full approve_topology() implementation
- Direct code inspection: `packages/orchestration/src/openclaw/topology/proposal_models.py` — RubricScore, TopologyProposal, ProposalSet structures
- Direct code inspection: `packages/orchestration/src/openclaw/topology/rubric.py` — score_proposal() standalone wrapper, DEFAULT_WEIGHTS
- Direct code inspection: `packages/orchestration/src/openclaw/cli/propose.py` — both approval call sites, hard correction path, explore flag pattern
- Direct code inspection: `packages/orchestration/src/openclaw/cli/approve.py` — single approval call site, ProposalSet.from_dict() usage
- Direct code inspection: `packages/dashboard/src/components/topology/ConfidenceChart.tsx` — transformChangelogToChartData(), full chart implementation
- Direct code inspection: `packages/dashboard/src/lib/types/topology.ts` — ChangelogAnnotations.rubric_scores type
- Direct code inspection: `packages/dashboard/tests/topology/confidence.test.ts` — existing TS tests, all passing
- Direct code inspection: `packages/orchestration/tests/test_approval.py` — existing test patterns, helper functions
- Direct code inspection: `packages/orchestration/tests/test_cli_approve.py` — existing test patterns, mock structure

### Secondary (MEDIUM confidence)

None needed — all findings derived from direct source inspection.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all components exist, read directly from source
- Architecture: HIGH — existing patterns are explicit and consistent
- Pitfalls: HIGH — derived from reading actual implementation, not speculation
- Test gaps: HIGH — all test files verified to exist

**Research date:** 2026-03-04
**Valid until:** Stable — no external dependencies; valid until source files change
