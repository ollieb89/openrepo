---
phase: 64-structural-memory
plan: 02
subsystem: structural-memory
tags: [spawn, rubric, approval, cli, memory, isolation, tdd]
dependency_graph:
  requires: [64-01]
  provides: [SMEM-02, SMEM-06]
  affects: [spawn-l3, rubric-scoring, approval-flow, propose-cli]
tech_stack:
  added: []
  patterns:
    - dual-layer isolation (pre-filter + defense-in-depth)
    - epsilon-greedy session-level explore flag
    - non-blocking recompute after approval
    - CLI subcommand via early sys.argv detection
key_files:
  created:
    - packages/orchestration/tests/test_spawn_isolation.py
  modified:
    - skills/spawn/spawn.py
    - packages/orchestration/src/openclaw/topology/rubric.py
    - packages/orchestration/src/openclaw/topology/approval.py
    - packages/orchestration/src/openclaw/cli/propose.py
    - packages/orchestration/tests/test_spawn_memory.py
decisions:
  - "Dual-layer isolation: Layer 1 pre-filter uses metadata.category fallback to match both storage formats"
  - "explore flag drawn once per session at call site in propose.py — not per-archetype"
  - "ArchetypeClassifier enrichment and MemoryProfiler recompute are both non-blocking in approval.py"
  - "Memory subcommand detected via early sys.argv check before argparse to avoid conflicts"
  - "Fixed pre-existing test_spawn_memory.py signature mismatch (Rule 1 deviation)"
metrics:
  duration: 5min
  completed_date: "2026-03-04"
  tasks_completed: 2
  files_modified: 5
---

# Phase 64 Plan 02: Structural Memory Wiring Summary

Wired structural memory into the system: dual-layer L3 isolation in spawn.py (EXCLUDED_CATEGORIES frozenset + pre-filter + defense-in-depth), dynamic preference_fit from MemoryProfiler in rubric.py, approval-triggered profile recomputation, and `openclaw-propose memory` CLI subcommand.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Dual-layer L3 isolation in spawn.py + isolation tests | b8ffd3c | skills/spawn/spawn.py, tests/test_spawn_isolation.py, tests/test_spawn_memory.py |
| 2 | Dynamic preference_fit + approval recompute + CLI memory report | a4215b7 | topology/rubric.py, topology/approval.py, cli/propose.py |

## What Was Built

### Task 1: Dual-layer L3 isolation (TDD)

**spawn.py changes:**
- Added `EXCLUDED_CATEGORIES = frozenset({"structural_correction", "structural_preference", "structural_pattern"})` after `CATEGORY_SECTION_MAP`
- Layer 1 pre-filter in spawn flow: strips structural categories from memories list after `_retrieve_memories_sync()` before calling `_format_memory_context()`, with warning log counting dropped items
- Layer 2 defense-in-depth in `_format_memory_context()`: checks `EXCLUDED_CATEGORIES` at the top of the item loop and drops any stragglers with a warning
- Both layers use `m.get("metadata", {}).get("category", m.get("category", ""))` to handle both flat and metadata-wrapped category storage formats

**test_spawn_isolation.py (16 tests):**
- `test_excluded_categories_frozenset_exists` / `test_excluded_categories_contains_all_structural` / `test_excluded_categories_does_not_include_normal`
- `test_prefilter_removes_structural_memories` / `test_prefilter_handles_metadata_wrapped_categories` / `test_prefilter_empty_list_stays_empty` / `test_prefilter_all_normal_categories_pass_through`
- `test_structural_categories_excluded_in_format` / `test_format_returns_empty_for_structural_only_input` / `test_format_mixed_structural_and_normal_drops_structural`
- `test_augmented_soul_has_no_topology_content`
- `test_non_structural_categories_still_route_review_decision` / `test_non_structural_categories_still_route_task_outcome` / `test_non_structural_categories_work_after_prefilter`
- `test_category_section_map_unchanged_by_isolation` / `test_both_layers_combined_no_structural_leakage`

### Task 2: rubric.py, approval.py, propose.py

**rubric.py:**
- `RubricScorer.score_proposal()` now accepts `project_id=None`, `archetype=None`, `explore=None` kwargs
- Replaces hardcoded `preference_fit = 5` with dynamic `MemoryProfiler.get_preference_fit()` when both `project_id` and `archetype` are present
- Falls back to `5` (neutral) when context is insufficient — fully backward compatible
- Standalone `score_proposal()` wrapper updated to pass through new kwargs

**approval.py:**
- Before building the changelog entry dict, calls `ArchetypeClassifier().classify(approved_graph)` to enrich `annotations["approved_archetype"]` — this is the data `MemoryProfiler.compute_profile()` reads to build affinity scores
- After `delete_pending_proposals()`, calls `MemoryProfiler.compute_profile()` with config from `get_topology_config()` — wrapped in `try/except` so failures are non-blocking

**propose.py:**
- Added `import random` at module level
- Added `_run_memory_report(args: list) -> int` function with compact output (correction count, threshold status, archetype affinity bars, top patterns)
- Early subcommand detection: `if len(sys.argv) > 1 and sys.argv[1] == "memory": return _run_memory_report(sys.argv[2:])`
- Session-level epsilon-greedy flag: `explore = random.random() < topo_config.get("exploration_rate", 0.20)` drawn once before the scoring loop
- Scoring loop now passes `project_id=project_id, archetype=p.archetype, explore=explore` to `score_proposal()`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pre-existing test_spawn_memory.py signature mismatch**
- **Found during:** Task 1 regression check
- **Issue:** Three tests in `test_spawn_memory.py` called `_build_augmented_soul(tmp_path, memory_context)` with the old 2-arg signature. Plan 01 updated `_build_augmented_soul` to a 4-arg signature but didn't update these tests.
- **Fix:** Updated the three failing tests to mock `load_project_config`, `AgentRegistry`, `build_variables`, `build_dynamic_variables`, and `render_soul`, matching the production signature `_build_augmented_soul(project_root, memory_context, project_id, agent_id)`
- **Files modified:** `packages/orchestration/tests/test_spawn_memory.py`
- **Commit:** b8ffd3c

### Pre-existing Failures (Out of Scope)

5 pre-existing failures unrelated to Plan 02 changes (confirmed by git stash test):
- `test_proposer.py::TestGenerateProposals` (4 tests) — LLM call behavior in test context
- `test_state_engine_memory.py::test_state_transition_triggers_memory` — JarvisState missing `project_id` attribute

These are not caused by Plan 02 changes and are out of scope per deviation rules.

## Self-Check

### Files Exist
- `packages/orchestration/tests/test_spawn_isolation.py` — FOUND
- `skills/spawn/spawn.py` (EXCLUDED_CATEGORIES) — FOUND
- `packages/orchestration/src/openclaw/topology/rubric.py` (dynamic preference_fit) — FOUND
- `packages/orchestration/src/openclaw/topology/approval.py` (compute_profile call) — FOUND
- `packages/orchestration/src/openclaw/cli/propose.py` (_run_memory_report) — FOUND

### Commits Exist
- b8ffd3c: feat(64-02): dual-layer L3 isolation — FOUND
- a4215b7: feat(64-02): dynamic preference_fit, approval recompute, memory CLI report — FOUND

### Tests
- 38 Phase 64 tests pass (21 structural memory + 17 isolation)
- 670 total tests pass, 5 pre-existing failures unchanged

## Self-Check: PASSED
