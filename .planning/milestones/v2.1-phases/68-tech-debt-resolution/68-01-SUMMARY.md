---
phase: 68-tech-debt-resolution
plan: 01
subsystem: topology-proposal-models
tags: [tech-debt, consolidation, bug-fix, async]
depends_on: []
provides:
  - Canonical TopologyProposal class (proposal_models.py) with graph field, rubric_score, assumptions, to_dict/from_dict
  - Unified proposal pipeline: proposer.py returns canonical TopologyProposal directly
  - Non-fatal event publishing in state_engine.create_task()
affects:
  - packages/orchestration/src/openclaw/topology/proposal_models.py
  - packages/orchestration/src/openclaw/topology/proposer.py
  - packages/orchestration/src/openclaw/topology/correction.py
  - packages/orchestration/src/openclaw/topology/renderer.py
  - packages/orchestration/src/openclaw/cli/propose.py
  - packages/orchestration/src/openclaw/cli/approve.py
  - packages/orchestration/src/openclaw/state_engine.py
tech-stack:
  added: []
  patterns:
    - Single canonical TopologyProposal dataclass in proposal_models.py
    - proposer.build_proposals() returns proposal_models.TopologyProposal directly (no bridge needed)
    - Backward-compatible from_dict() accepts both graph and topology keys
key-files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/topology/proposal_models.py
    - packages/orchestration/src/openclaw/topology/proposer.py
    - packages/orchestration/src/openclaw/topology/correction.py
    - packages/orchestration/src/openclaw/topology/renderer.py
    - packages/orchestration/src/openclaw/cli/propose.py
    - packages/orchestration/src/openclaw/cli/approve.py
    - packages/orchestration/src/openclaw/state_engine.py
    - packages/orchestration/tests/test_state_engine_memory.py
    - packages/orchestration/tests/test_proposer.py
    - packages/orchestration/tests/test_correction.py
    - packages/orchestration/tests/test_renderer.py
    - packages/orchestration/tests/test_proposal_rubric.py
    - packages/orchestration/tests/test_cli_propose.py
decisions:
  - Renamed topology field to graph in proposal_models.TopologyProposal (matches proposer.py usage)
  - from_dict() accepts both graph (new) and topology (legacy) keys for backward compat
  - _to_pm_proposals() converted to identity pass-through (no conversion needed after consolidation)
  - Outer try/except wraps event publishing in state_engine so state operations never fail on event errors
  - Used asyncio.run() instead of deprecated get_event_loop().run_until_complete() in test_proposer
metrics:
  duration: ~20 minutes
  completed: 2026-03-04
  tasks_completed: 2
  files_modified: 13
  tests_before: 683 passing (11 failing)
  tests_after: 694 passing (0 failing)
requirements:
  - DEBT-01
  - DEBT-02
---

# Phase 68 Plan 01: Tech Debt Resolution — TopologyProposal Consolidation Summary

Single-sentence summary: Eliminated the dual TopologyProposal class split by canonicalizing on proposal_models.py with `graph` field and fixing the async event loop crash in state_engine.create_task().

## What Was Built

### Task 1: Consolidate TopologyProposal into proposal_models.py

The codebase had two incompatible `TopologyProposal` classes:
- `proposer.py`: used `.graph` field, no rubric_score, no to_dict/from_dict
- `proposal_models.py`: used `.topology` field, had rubric_score, to_dict/from_dict

This fragile dual-class setup required a conversion bridge in `cli/propose.py` (`_to_pm_proposals`) and `correction.py` that manually mapped `.graph` to `.topology`.

**Changes made:**
1. **proposal_models.py**: Renamed `topology` field to `graph`, added `assumptions: List[str]` field, updated `to_dict()` to serialize as `graph` key, updated `from_dict()` to accept both `graph` (new) and `topology` (legacy) for backward compat.

2. **proposer.py**: Removed the duplicate `TopologyProposal` dataclass and all its imports (`dataclass`, `field`). Added `from openclaw.topology.proposal_models import TopologyProposal`. The `build_proposals()` function already used `graph=` kwarg so it works directly with the renamed field.

3. **correction.py**: Removed the conversion block (lines 172-181) that was creating `pm_proposal` with `topology=prop.graph`. Now simply attaches rubric_score to the unified proposal (`prop.rubric_score = rubric`).

4. **renderer.py**: Updated `proposal.topology` -> `proposal.graph` in `render_diff_summary` and `render_full_output`.

5. **cli/propose.py**: Simplified `_to_pm_proposals()` to be an identity pass-through. Updated all `.topology` field accesses to `.graph` (`score_proposal`, `classifier.classify`, pushback computation, `approve_topology` calls, `imported_proposal` construction).

6. **cli/approve.py**: Updated two `.topology` field accesses to `.graph`.

7. **Test files**: Updated all `topology=` constructor kwargs to `graph=` in test_correction.py, test_proposal_rubric.py, test_renderer.py, test_cli_propose.py. Updated serialization assertion from `"topology" in data` to `"graph" in data`. Updated `TestToPmProposals` test to use real TopologyProposal instead of MagicMock (since pass-through returns same object).

### Task 2: Fix state_engine event publishing and test_state_engine_memory

Three issues fixed:

1. **`self.project_id` AttributeError in create_task()**: The event publishing block used `self.project_id` but `JarvisState` has no such attribute. Fixed to call `project_id = get_active_project_id()` locally (matching the pattern used in `update_task()`).

2. **Non-fatal event publishing**: Wrapped the entire event publishing block in an outer `try/except Exception` that logs a warning. State operations can never fail due to event publishing errors.

3. **test_state_engine_memory.py**: Added mocks for `event_bridge` (with `AsyncMock publish`) and `asyncio` module (with mock `get_running_loop` returning a mock loop). This prevents `asyncio.run()` from being called, which would close the event loop and break subsequent async tests.

4. **Pre-existing async issue in test_proposer.py**: The `TestGenerateProposals._run()` method used the deprecated `asyncio.get_event_loop().run_until_complete()`. This fails when `test_structural_memory.py` runs first (closes the event loop). Fixed to use `asyncio.run()` instead — which creates its own independent event loop per call.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] cli/approve.py also referenced .topology field**
- **Found during:** Task 1 verification (test_cli_approve.py failures)
- **Issue:** `cli/approve.py` was not in the plan's file list but had two `.topology` field accesses that broke after renaming
- **Fix:** Updated both `selected.topology` -> `selected.graph` in compute_pushback_note call and approve_topology call
- **Files modified:** packages/orchestration/src/openclaw/cli/approve.py
- **Commit:** d9b4ef8

**2. [Rule 1 - Bug] TestGenerateProposals used deprecated event loop API**
- **Found during:** Task 2 verification (4 tests failing in full suite)
- **Issue:** `asyncio.get_event_loop().run_until_complete()` is deprecated in Python 3.10+ and fails when another test closes the default event loop
- **Fix:** Changed to `asyncio.run()` which creates independent event loops per call
- **Files modified:** packages/orchestration/tests/test_proposer.py
- **Commit:** d9b4ef8

**3. [Rule 2 - Missing critical functionality] test_cli_propose.py TestToPmProposals needed updating**
- **Found during:** Task 1 (_to_pm_proposals conversion)
- **Issue:** The test used a MagicMock proposer proposal expecting conversion; after making it a pass-through, the test checked `result[0].rubric_score is None` against a MagicMock object
- **Fix:** Updated test to use a real TopologyProposal object (matching the new reality that build_proposals() returns canonical objects)
- **Files modified:** packages/orchestration/tests/test_cli_propose.py
- **Commit:** f1bc23b

## Self-Check

### Files exist
- [x] `./packages/orchestration/src/openclaw/topology/proposal_models.py` — canonical TopologyProposal with graph field
- [x] `./packages/orchestration/src/openclaw/topology/proposer.py` — imports TopologyProposal from proposal_models
- [x] `./packages/orchestration/src/openclaw/state_engine.py` — uses get_active_project_id() in create_task

### Only one TopologyProposal class
```
grep -rn "class TopologyProposal" packages/orchestration/src/openclaw/
# Result: only proposal_models.py:73
```

### proposer.py imports from proposal_models
```
grep "from.*proposal_models import.*TopologyProposal" packages/orchestration/src/openclaw/topology/proposer.py
# Result: from openclaw.topology.proposal_models import TopologyProposal
```

### Tests pass
- 694 tests pass, 0 failures across full orchestration test suite

## Self-Check: PASSED
