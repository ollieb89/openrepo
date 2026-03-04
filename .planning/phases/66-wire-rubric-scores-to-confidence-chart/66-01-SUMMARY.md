---
phase: 66-wire-rubric-scores-to-confidence-chart
plan: 01
subsystem: topology-approval
tags: [tdd, rubric-scores, changelog, confidence-chart, approval-workflow]
requirements: [TOBS-05]

dependency_graph:
  requires:
    - packages/orchestration/src/openclaw/topology/proposal_models.py (RubricScore.to_dict())
    - packages/orchestration/src/openclaw/topology/rubric.py (score_proposal())
  provides:
    - rubric_scores in changelog annotations (consumed by ConfidenceChart via transformChangelogToChartData)
  affects:
    - packages/dashboard/src/components/topology/ConfidenceChart.tsx (now receives real data points)

tech_stack:
  added: []
  patterns:
    - TDD (RED/GREEN/REFACTOR) with pytest and unittest.mock.patch
    - Optional dict parameter with conditional write (truthy guard prevents empty dict in annotations)
    - Graceful degradation on hard-correction re-scoring (bare except -> pass)

key_files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/topology/approval.py
    - packages/orchestration/src/openclaw/cli/propose.py
    - packages/orchestration/src/openclaw/cli/approve.py
    - packages/orchestration/tests/test_approval.py
    - packages/orchestration/tests/test_cli_approve.py

decisions:
  - "rubric_scores param added as Optional[dict] with default None — backward compatible, no callers broken"
  - "Truthy guard (if rubric_scores) ensures empty dict does not pollute annotations — matches anti-pattern in plan"
  - "Hard correction re-scores the imported (post-edit) graph, NOT the pre-edit proposal — user's structural edit is scored faithfully"
  - "score_proposal() called per-archetype without explore flag during hard-correction re-scoring — scoring for recording, not ranking"
  - "Bare except + pass in hard-correction re-scoring — graceful degradation keeps chart empty rather than blocking approval"

metrics:
  duration: 4min
  completed: 2026-03-04
  tasks_completed: 2
  files_modified: 5
---

# Phase 66 Plan 01: Wire Rubric Scores to Confidence Chart Summary

Plumbed rubric scores from the approval workflow into changelog entries so ConfidenceChart renders real data points — three Python files updated, four new tests, full backward compatibility maintained.

## What Was Built

**TOBS-05 gap closed.** The TypeScript `ConfidenceChart` already reads `annotations.rubric_scores` from changelog entries via `transformChangelogToChartData()`, but the Python backend never populated this field. This plan added the missing plumbing:

1. **`approve_topology()` new param** — `rubric_scores: Optional[dict] = None` added as the last parameter. When truthy (non-empty dict), writes to `annotations["rubric_scores"]`. When None or empty dict, key is omitted entirely. No existing callers broken.

2. **`approve.py` call site** — Builds `rubric_scores` dict from all proposals in `proposal_set` using `p.rubric_score.to_dict()`, converts empty result to `None` via `or None` pattern.

3. **`propose.py` normal approval call site** — Same pattern, built from `session.proposal_set.proposals`.

4. **`propose.py` hard correction call site** — Re-scores the imported (post-edit) graph under all 3 archetypes (`lean`, `balanced`, `robust`) using `score_proposal()`, with graceful degradation on any scoring failure.

## Tasks Completed

| Task | Name | Commit | Files Modified |
|------|------|--------|----------------|
| 1 | Add rubric_scores param to approve_topology() | 05d94f7 (RED), db89eca (GREEN) | test_approval.py, approval.py |
| 2 | Wire CLI callers to build and pass rubric_scores | 7f9eb37 (RED), 08d2cd6 (GREEN) | test_cli_approve.py, propose.py, approve.py |

## Test Results

- **New tests added:** 4 (3 in TestRubricScoresInAnnotations, 1 in TestApproveSuccess)
- **Tests passing after changes:** 33 (test_approval.py + test_cli_approve.py combined)
- **Full suite:** 678 pass, 5 pre-existing failures in test_proposer.py and test_state_engine_memory.py (unrelated to this plan)

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- `packages/orchestration/src/openclaw/topology/approval.py` — rubric_scores param present, conditional annotation write present
- `packages/orchestration/src/openclaw/cli/propose.py` — rubric_scores at both approval sites (lines 243, 325)
- `packages/orchestration/src/openclaw/cli/approve.py` — rubric_scores at approval site (line 167)
- `packages/orchestration/tests/test_approval.py` — TestRubricScoresInAnnotations with 3 tests
- `packages/orchestration/tests/test_cli_approve.py` — test_approve_passes_rubric_scores_kwarg added
- Commits 05d94f7, db89eca, 7f9eb37, 08d2cd6 all verified present in git log
