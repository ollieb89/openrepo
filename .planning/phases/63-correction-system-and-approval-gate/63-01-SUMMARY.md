---
phase: 63-correction-system-and-approval-gate
plan: 01
subsystem: topology
tags: [correction, approval, storage, tdd, fcntl]
dependency_graph:
  requires:
    - packages/orchestration/src/openclaw/topology/proposer.py
    - packages/orchestration/src/openclaw/topology/linter.py
    - packages/orchestration/src/openclaw/topology/rubric.py
    - packages/orchestration/src/openclaw/topology/diff.py
    - packages/orchestration/src/openclaw/topology/storage.py
  provides:
    - packages/orchestration/src/openclaw/topology/correction.py
    - packages/orchestration/src/openclaw/topology/approval.py
    - packages/orchestration/src/openclaw/topology/storage.py (extended)
  affects:
    - Phase 63 CLI and router plans (depend on correction.py, approval.py)
tech_stack:
  added:
    - correction.py with CorrectionSession dataclass
    - approval.py with approve_topology, compute_pushback_note, check_approval_gate
  patterns:
    - TDD (red-green): tests written before implementation, all pass
    - fcntl LOCK_EX/LOCK_SH for atomic pending-proposals persistence
    - @dataclass (not Pydantic) consistent with existing topology models
    - Soft correction: LLM re-proposal with feedback injected into clarifications
    - Hard correction: annotated JSON export/import with __comment__ key stripping
key_files:
  created:
    - packages/orchestration/src/openclaw/topology/correction.py
    - packages/orchestration/src/openclaw/topology/approval.py
    - packages/orchestration/tests/test_correction.py
    - packages/orchestration/tests/test_approval.py
  modified:
    - packages/orchestration/src/openclaw/topology/storage.py
decisions:
  - "CorrectionSession uses @dataclass consistent with AgentSpec/TopologyGraph patterns (not Pydantic)"
  - "cycle_limit_reached is a property (not a method) for clean boolean semantics"
  - "apply_soft_correction raises ValueError before LLM call when limit reached (no wasted API call)"
  - "import_draft re-raises ValueError with all valid EdgeType values listed for user clarity"
  - "compute_pushback_note never raises — catches all exceptions and returns empty string"
  - "approve_topology calls delete_pending_proposals after save+changelog for atomic cleanup"
  - "Pending proposals use same tmp+rename+fcntl pattern as save_topology"
metrics:
  duration: 4min
  completed_date: "2026-03-03"
  tasks_completed: 1
  files_created: 4
  files_modified: 1
  tests_added: 42
  tests_passing: 42
---

# Phase 63 Plan 01: Correction and Approval Foundation Summary

**One-liner:** CorrectionSession with cycle limit, soft/hard correction logic, approval gate with changelog diff and pushback scoring, and fcntl-safe pending proposal storage.

## What Was Built

### correction.py

Three core functions plus one dataclass:

- **`CorrectionSession`** — `@dataclass` tracking `cycle_count`, `max_cycles`, `proposal_set`, `best_proposal_set`, `correction_history`, and `clarifications`. `cycle_limit_reached` property returns `True` when `cycle_count >= max_cycles` (default 3).

- **`apply_soft_correction(session, feedback, weights)`** — Guards against cycle limit before LLM call (raises `ValueError`). Increments `cycle_count`, builds augmented clarifications with `user_feedback`, calls `generate_proposals_sync`, builds/lints/scores all 3 archetype proposals, updates `best_proposal_set` if new top confidence exceeds current best, appends to `correction_history`.

- **`export_draft(proposal, project_id)`** — Writes `proposal-draft.json` with the topology dict plus `__comment__nodes` and `__comment__edges` annotation keys. Returns path.

- **`import_draft(project_id, registry, max_concurrent)`** — Loads `proposal-draft.json`, strips `__comment__` keys, calls `TopologyGraph.from_dict()` with clear `ValueError` on invalid `edge_type` (lists all valid values), runs `ConstraintLinter.lint("hard_correction", ...)`. Returns `(TopologyGraph, LintResult)`.

### approval.py

Three functions:

- **`approve_topology(project_id, approved_graph, correction_type, pushback_note="")`** — Loads previous topology, computes `topology_diff` (or `None` on first approval), builds changelog entry with timestamp + correction_type + diff + annotations, calls `save_topology` then `append_changelog`, calls `delete_pending_proposals`. Returns entry dict.

- **`compute_pushback_note(original_score, approved_graph, weights, pushback_threshold=8)`** — Returns empty string if `original_score.overall_confidence < pushback_threshold`. Scores approved graph, compares each of 5 dimensions (complexity, coordination_overhead, risk_containment, time_to_first_output, cost_estimate). Returns informational string if any drop >= 2 points. Never raises.

- **`check_approval_gate(project_id, auto_approve_l1=False)`** — Returns `{"approved": True}` immediately if `auto_approve_l1`. Otherwise loads topology: exists → `{"approved": True}`, absent → `{"approved": False, "reason": "...run 'openclaw-propose'..."}`.

### storage.py (extended)

Three new functions using the existing fcntl/tmp+rename pattern:

- **`save_pending_proposals(project_id, data)`** — Atomic write with `LOCK_EX` + `.tmp` rename to `pending-proposals.json`.
- **`load_pending_proposals(project_id)`** — Returns `None` if file missing; reads with `LOCK_SH`.
- **`delete_pending_proposals(project_id)`** — Silently unlinks `pending-proposals.json` if it exists.

## Tests (42 total, all passing)

**test_correction.py** (534 lines, 23 tests):
- `TestCorrectionSession` (7 tests): cycle_count defaults, cycle_limit_reached at/below/above limit, max_cycles default, history/clarifications defaults
- `TestSoftCorrection` (6 tests): cycle increment, feedback in clarifications, ProposalSet return type, history recording, best_proposal_set update, existing clarifications preserved
- `TestCycleLimit` (2 tests): ValueError raised, LLM not called when at limit
- `TestHardCorrection` (8 tests): file created, valid JSON, comment keys present, topology keys present, TopologyGraph returned, comment stripping, bad edge_type ValueError with valid types, LintResult returned

**test_approval.py** (425 lines, 19 tests):
- `TestApproveTopology` (9 tests): diff recorded, correction_type in entry, first-approval diff=None, save_topology called, append_changelog called, timestamp present, pending deleted, pushback_note in annotations, diff JSON-serializable
- `TestPushbackNote` (5 tests): note on high confidence + dimension drops, no note on low confidence, no note on no significant drop, never raises, informational-only language
- `TestApprovalGate` (5 tests): blocks without topology, passes with topology, auto_approve bypass, reason mentions project ID, reason mentions propose command

## Deviations from Plan

None — plan executed exactly as written.

## Requirements Coverage

| Requirement | Coverage |
|-------------|----------|
| CORR-01 | CorrectionSession with cycle_count, cycle_limit_reached, max_cycles |
| CORR-02 | apply_soft_correction with feedback injection and best_proposal_set update |
| CORR-03 | ValueError raised before LLM call when cycle_limit_reached |
| CORR-04 | approve_topology with diff changelog and atomic save |
| CORR-05 | export_draft/__comment__ keys, import_draft/stripping/linting |
| CORR-06 | compute_pushback_note with dimension comparison and informational note |
| CORR-07 | check_approval_gate with auto_approve_l1 bypass |

## Self-Check: PASSED

- FOUND: packages/orchestration/src/openclaw/topology/correction.py
- FOUND: packages/orchestration/src/openclaw/topology/approval.py
- FOUND: packages/orchestration/src/openclaw/topology/storage.py (extended)
- FOUND: packages/orchestration/tests/test_correction.py (534 lines > 100 min)
- FOUND: packages/orchestration/tests/test_approval.py (425 lines > 80 min)
- FOUND commit: 783fac9 (test RED phase)
- FOUND commit: 4d6376f (feat GREEN phase)
- All exports importable: CorrectionSession, apply_soft_correction, export_draft, import_draft, approve_topology, compute_pushback_note, check_approval_gate, save_pending_proposals, load_pending_proposals, delete_pending_proposals
- 42/42 tests pass
