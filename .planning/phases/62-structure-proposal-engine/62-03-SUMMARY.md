---
phase: 62-structure-proposal-engine
plan: 03
subsystem: topology
tags: [topology, rubric, linter, proposal-models, scoring, constraint-validation]

# Dependency graph
requires:
  - phase: 62-01
    provides: TopologyGraph, TopologyNode, TopologyEdge, EdgeType models
  - phase: 62-02
    provides: ArchetypeClassifier, ArchetypeResult for archetype detection

provides:
  - RubricScore dataclass with 7 scoring dimensions (0-10 integers)
  - TopologyProposal and ProposalSet dataclasses for LLM proposal output
  - RubricScorer with 6-dimension scoring + weighted overall_confidence
  - find_key_differentiators() for comparative proposal analysis
  - ConstraintLinter validating roles against AgentRegistry and pool limits
  - LintResult with full status (valid, adjusted, rejected_roles, adjustments)
  - topology key in OPENCLAW_JSON_SCHEMA (separate from autonomy config)
  - get_topology_config() returning threshold=5 and 6 default rubric weights

affects: [62-04-proposal-generation, 62-05-user-presentation, 63-preference-learning]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@dataclass for topology models (consistent with AgentSpec and TopologyGraph patterns)"
    - "Higher-is-always-better rubric scoring: all dimensions normalized so 10 = best"
    - "Removal cost ranking for auto-constrain: review-gate-connected roles preserved over coordination-only"
    - "Warning-before-adjustment: emit WARNING in adjustments list when safety nets are lost"

key-files:
  created:
    - packages/orchestration/src/openclaw/topology/proposal_models.py
    - packages/orchestration/src/openclaw/topology/rubric.py
    - packages/orchestration/src/openclaw/topology/linter.py
    - packages/orchestration/tests/test_proposal_rubric.py
    - packages/orchestration/tests/test_proposal_linter.py
  modified:
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/src/openclaw/topology/__init__.py

key-decisions:
  - "Rubric warning logic warns on ANY review gate loss (not just total loss) — partial safety reduction is still significant"
  - "preference_fit always returns 5 pre-Phase 64 (neutral baseline; Phase 64 adds adaptive preference scoring)"
  - "Removal cost model: +10 per review_gate edge, +1 per coordination edge, 0 for delegation — reviewers are expensive to remove"
  - "Auto-constrain preserves proposal validity (valid=True) while being transparent about adjustments"

patterns-established:
  - "Rubric scoring pattern: formula → clamp(0,10) → return int — all dimension scores are clamped integers"
  - "Linter two-pass pattern: reject unknown roles first (Stage 1), then adjust pool violations (Stage 2)"
  - "Adjustment transparency: every auto-modification is logged to LintResult.adjustments as human-readable string"

requirements-completed: [PROP-02, PROP-03, PROP-05, PROP-06]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 62 Plan 03: Proposal Scoring and Constraint Validation Summary

**7-dimension rubric scorer with weighted overall_confidence, review-gate-preserving constraint linter, and TopologyProposal/ProposalSet models for LLM output**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T18:20:51Z
- **Completed:** 2026-03-03T18:25:57Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- `proposal_models.py` — TopologyProposal, ProposalSet, RubricScore dataclasses with full to_dict/from_dict serialization
- `rubric.py` — RubricScorer scoring 6 dimensions (complexity, coordination_overhead, risk_containment, time_to_first_output, cost_estimate, preference_fit) plus weighted overall_confidence; find_key_differentiators() for >= 3 spread detection
- `linter.py` — ConstraintLinter with two-stage validation (unknown role rejection + pool auto-constrain), review-gate-preserving removal cost ranking, and transparent adjustment logging with WARNING when safety gates are lost
- Config schema extended with `topology` key (separate from `autonomy`) and `get_topology_config()` function

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1 RED: Proposal models and rubric tests** — `0f9446c` (test)
2. **Task 1 GREEN: proposal_models.py, rubric.py, config.py, __init__.py** — `3a613d9` (feat)
3. **Task 2 RED: Constraint linter tests** — `6a52a4a` (test)
4. **Task 2 GREEN: linter.py, __init__.py** — `bdcf952` (feat)

## Files Created/Modified

- `packages/orchestration/src/openclaw/topology/proposal_models.py` — RubricScore, TopologyProposal, ProposalSet dataclasses (118 lines)
- `packages/orchestration/src/openclaw/topology/rubric.py` — RubricScorer, find_key_differentiators, DEFAULT_WEIGHTS, DIMENSIONS (155 lines)
- `packages/orchestration/src/openclaw/topology/linter.py` — ConstraintLinter, LintResult, MAX_RETRIES (185 lines)
- `packages/orchestration/src/openclaw/topology/__init__.py` — Updated to export all new types
- `packages/orchestration/src/openclaw/config.py` — Added topology schema key and get_topology_config()
- `packages/orchestration/tests/test_proposal_rubric.py` — 15 tests for models and rubric
- `packages/orchestration/tests/test_proposal_linter.py` — 12 tests for constraint linter

## Decisions Made

- **Rubric warning logic warns on ANY review gate loss** — The plan specified "warn if removing would eliminate ALL review gate edges." During testing it was clear that partial loss (e.g., 4→1 review gates) is equally important. Updated to warn whenever any review gate edges are removed, distinguishing "all lost" vs "reduced" in the message text.
- **preference_fit always 5** — Hardcoded neutral baseline until Phase 64 adds preference learning. Not configurable.
- **Removal cost model: +10 per review_gate edge, +1 per coordination** — Review gate roles are 10x more expensive to remove than coordination-only roles, ensuring they survive auto-constraining wherever possible.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test threshold for time_to_first_output corrected**
- **Found during:** Task 1 GREEN phase (running tests)
- **Issue:** Test asserted `time_to_first_output >= 7` for lean graph (2 nodes, depth=2). Formula `10 - depth*2 = 10 - 4 = 6` correctly gives 6, not 7. Test assumption was wrong (assumed depth=1 for 2-node graph).
- **Fix:** Changed test to assert `>= 6` and added comparative assertion (lean scores higher than robust on this dimension), which tests the right behavior.
- **Files modified:** packages/orchestration/tests/test_proposal_rubric.py
- **Committed in:** 3a613d9 (Task 1 feat commit)

**2. [Rule 1 - Bug] Linter warning logic extended to partial review gate loss**
- **Found during:** Task 2 GREEN phase (running tests)
- **Issue:** Original implementation only warned when ALL review gates are eliminated. The test scenario (4 L3s all with review gates, max_concurrent=1 → keeps 1, loses 3) correctly requires a warning since 75% of review gates are lost.
- **Fix:** Updated `_auto_constrain` to warn whenever `removed_review_count > 0`, emitting distinct messages for "all lost" vs "reduced" cases.
- **Files modified:** packages/orchestration/src/openclaw/topology/linter.py
- **Committed in:** bdcf952 (Task 2 feat commit)

---

**Total deviations:** 2 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Both fixes improve correctness — test now validates actual behavior, warning logic now catches all safety-net degradation.

## Issues Encountered

None — implementation proceeded cleanly after test threshold adjustments.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Proposal models are the data contract for Plan 04 (LLM generation pipeline)
- RubricScorer is ready to score proposals as they are generated
- ConstraintLinter is ready to validate proposals before they reach the user
- Config schema is ready for `topology.rubric_weights` customization

---
*Phase: 62-structure-proposal-engine*
*Completed: 2026-03-03*

## Self-Check: PASSED

All 6 files present. All 4 task commits verified (0f9446c, 3a613d9, 6a52a4a, bdcf952).
