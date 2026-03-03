---
phase: 62-structure-proposal-engine
plan: 05
subsystem: topology/renderer, cli/propose, routing
tags: [cli, renderer, ascii-dag, matrix, routing, l1-dispatch]
dependency_graph:
  requires: [62-03, 62-04]
  provides: [openclaw-propose CLI, ASCII DAG renderer, comparative matrix, L1 routing for propose]
  affects: [skills/router/index.js, agents/main/skills/route_directive/router.py]
tech_stack:
  added: []
  patterns:
    - ASCII box-drawing matrix with wide/stacked terminal layout detection
    - DFS-based ASCII DAG rendering with edge type labels
    - proposer.TopologyProposal -> proposal_models.TopologyProposal conversion layer
    - L1 __propose__ sentinel routing pattern
key_files:
  created:
    - packages/orchestration/src/openclaw/topology/renderer.py
    - packages/orchestration/src/openclaw/cli/propose.py
    - packages/orchestration/tests/test_renderer.py
    - packages/orchestration/tests/test_cli_propose.py
  modified:
    - packages/orchestration/src/openclaw/topology/__init__.py
    - packages/orchestration/src/openclaw/topology/rubric.py
    - packages/orchestration/pyproject.toml
    - openclaw.json
    - skills/router/index.js
    - agents/main/skills/route_directive/router.py
decisions:
  - proposer.TopologyProposal (.graph) converted to proposal_models.TopologyProposal (.topology) in CLI via _to_pm_proposals() helper rather than modifying proposer.py (preserves existing tests)
  - score_proposal() standalone function added to rubric.py as wrapper around RubricScorer class
  - shutil.get_terminal_size mock in tests uses MagicMock with .columns attribute (plain tuple doesn't have .columns)
metrics:
  duration: 5min
  completed_date: "2026-03-03T18:34:29Z"
  tasks_completed: 3
  files_changed: 10
---

# Phase 62 Plan 05: CLI Entry Point and Terminal Renderer Summary

**One-liner:** openclaw-propose CLI wiring full pipeline (generate → lint → score → render) with ASCII DAG and comparative matrix formatter, plus L1 directive routing via __propose__ sentinel.

## What Was Built

### renderer.py (130 lines)
- `render_dag(topology)`: DFS topological sort, root nodes identified by no-incoming-edge, children indented with `-(edge_type)-> [node_id]` format, cycle-safe via visited set
- `render_matrix(proposals, key_diffs)`: terminal width detection via `shutil.get_terminal_size`, side-by-side (>= 100 cols) with box-drawing chars, stacked (< 100 cols) with per-archetype sections; key differentiators marked with `*`, preference fit with `~`
- `render_assumptions`, `render_justifications`, `render_low_confidence_warning`, `render_full_output` combining all sections

### cli/propose.py (200+ lines)
- Full pipeline: outcome resolution (positional, interactive prompt, or stdin) → clarifying questions → generate_proposals_sync → ConstraintLinter loop (MAX_RETRIES attempts) → score_proposal → find_key_differentiators → ArchetypeClassifier verification → sort by confidence → render_full_output or JSON
- _to_pm_proposals() conversion: maps proposer.TopologyProposal.graph -> proposal_models.TopologyProposal.topology
- Flags: --fresh, --json, --project; Colors class consistent with project.py/monitor.py

### L1 routing
- skills/router/index.js: propose keyword detection block before gateway dispatch, calls `execFileSync('openclaw-propose', [...args])` with 5min timeout
- agents/main/skills/route_directive/router.py: `_resolve_target()` returns `'__propose__'` sentinel for directives containing 'propose' or 'topology'

### Supporting changes
- rubric.py: `score_proposal()` standalone function (wrapper around RubricScorer)
- topology/__init__.py: exports all renderer functions
- pyproject.toml: `openclaw-propose = "openclaw.cli.propose:main"` entry point
- openclaw.json: `topology.proposal_confidence_warning_threshold = 5` and `rubric_weights` dict

## Tests

- `test_renderer.py`: 20 tests — render_dag (5), render_matrix (7), render_assumptions (3), proposal ordering (1), low confidence warning (2), render_full_output (2)
- `test_cli_propose.py`: 16 tests — importability (4), argparse (8), error handling (2), conversion helper (2)
- All 36 tests pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Added score_proposal() standalone function to rubric.py**
- **Found during:** Task 2
- **Issue:** Plan's CLI imports `score_proposal` directly from rubric, but only `RubricScorer.score_proposal()` method existed
- **Fix:** Added module-level `score_proposal(topology, weights)` function as thin wrapper
- **Files modified:** packages/orchestration/src/openclaw/topology/rubric.py
- **Commit:** 0040d1c

**2. [Rule 1 - Bug] Fixed terminal size mock in test to use MagicMock with .columns attribute**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test patched `shutil.get_terminal_size` to return plain tuple `(80, 24)` but code called `.columns` on result — tuple has no `.columns`
- **Fix:** Changed mock to `MagicMock()` with `mock_size.columns = 80`
- **Files modified:** packages/orchestration/tests/test_renderer.py
- **Commit:** ee9dca5

**3. [Rule 3 - Integration] Added _to_pm_proposals() conversion layer in CLI**
- **Found during:** Task 2
- **Issue:** `build_proposals()` in proposer.py returns `proposer.TopologyProposal` with `.graph` field; plan's CLI expects `proposal_models.TopologyProposal` with `.topology` field. Direct use would fail.
- **Fix:** Added `_to_pm_proposals()` helper that converts after `build_proposals()`. Avoids modifying proposer.py (which would break existing tests).
- **Files modified:** packages/orchestration/src/openclaw/cli/propose.py
- **Commit:** 0040d1c

### Deferred (Out of Scope)

- `openclaw.json` 'skills' field unknown to OPENCLAW_JSON_SCHEMA — pre-existing schema gap, not caused by plan-05 changes
- `agents/main/skills/route_directive/__init__.py` imports `RouteDecision` and `RouteType` that don't exist in router.py — pre-existing broken import, not caused by plan-05 changes

## Self-Check: PASSED
