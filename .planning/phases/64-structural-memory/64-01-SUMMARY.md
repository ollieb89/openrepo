---
phase: 64-structural-memory
plan: 01
subsystem: topology
tags: [structural-memory, exponential-decay, epsilon-greedy, pattern-extraction, archetype-affinity, llm]

# Dependency graph
requires:
  - phase: 62-structure-proposal-engine
    provides: TopologyGraph models, correction changelog, storage patterns
  - phase: 63-correction-interface
    provides: approval.py append_changelog with correction_type and approved_archetype annotations
provides:
  - MemoryProfiler class with exponential decay archetype affinity computation
  - PatternExtractor class with LLM-based structural pattern extraction
  - save_memory_profile, load_memory_profile, save_patterns, load_patterns storage functions
  - get_topology_config() extended with exploration_rate, decay_lambda, pattern_extraction_threshold
affects: [64-02, 64-03, rubric-scorer, preference-fit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Exponential decay weighting for temporal correction history (lambda=0.05, ~14-day half-life)
    - Epsilon-greedy exploration: caller draws single random per session, passes explore=True/False
    - Threshold gating: all affinities neutral (5.0) below min_threshold corrections
    - Graceful LLM failure: PatternExtractor returns existing patterns unchanged on any exception
    - Affinity normalization to [0,10] scale via fractional deviation from equal distribution

key-files:
  created:
    - packages/orchestration/src/openclaw/topology/memory.py
    - packages/orchestration/tests/test_structural_memory.py
  modified:
    - packages/orchestration/src/openclaw/config.py
    - packages/orchestration/src/openclaw/topology/storage.py

key-decisions:
  - "Affinity normalization uses fractional deviation from equal-share (1/3 each) mapped to [0,10] — equal corrections for all archetypes returns [5,5,5]"
  - "explore param is passed by caller (not drawn internally) — enforces session-level epsilon-greedy where one random draw covers all archetype fits in a scoring session"
  - "PatternExtractor.extract() uses asyncio.run() to call async LLM from sync context — consistent with correction.py pattern in Phase 63"
  - "active_pattern_ids in profile stores first 40 chars of pattern text as lightweight IDs — sufficient for deduplication hints"

patterns-established:
  - "Threshold-gated computation: return neutral defaults when data insufficient, mark status as below_threshold vs active"
  - "Graceful degradation: on any LLM failure return existing data unchanged, log warning, never raise"
  - "Storage follows Jarvis Protocol: tmp+rename+fcntl LOCK_EX writes for crash safety"

requirements-completed: [SMEM-01, SMEM-03, SMEM-04, SMEM-05]

# Metrics
duration: 3min
completed: 2026-03-04
---

# Phase 64 Plan 01: Structural Memory Foundation Summary

**Archetype affinity profiler with 14-day exponential decay, epsilon-greedy exploration, and LLM pattern extractor with threshold gating — core data layer for Phase 64 adaptive preference scoring**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-04T08:19:20Z
- **Completed:** 2026-03-04T08:22:30Z
- **Tasks:** 1 (TDD: test commit + implementation commit)
- **Files modified:** 4

## Accomplishments

- Extended `get_topology_config()` with 3 new keys: `exploration_rate` (0.20), `decay_lambda` (0.05), `pattern_extraction_threshold` (5)
- Added 4 atomic storage functions to storage.py: `save_memory_profile`, `load_memory_profile`, `save_patterns`, `load_patterns` — all using fcntl LOCK_EX + tmp/rename pattern
- `MemoryProfiler` computes archetype affinity via weighted signal accumulation with exponential decay; normalizes to [0,10]; returns neutral profile below threshold
- `PatternExtractor` calls LLM with correction diffs when threshold met; filters confidence < 0.4; prunes to top 10 by confidence when > 20; graceful LLM failure handling
- 22 unit tests — all pass; 0 regressions in full suite (8 pre-existing failures unchanged)

## Task Commits

TDD task had two commits:

1. **RED — failing tests** - `8cd23ef` (test)
2. **GREEN — implementation** - `e7ce400` (feat)

## Files Created/Modified

- `packages/orchestration/src/openclaw/topology/memory.py` — MemoryProfiler and PatternExtractor classes (203 lines)
- `packages/orchestration/tests/test_structural_memory.py` — 22 unit tests covering all behaviors (428 lines)
- `packages/orchestration/src/openclaw/config.py` — 3 new keys in get_topology_config() docstring and return dict
- `packages/orchestration/src/openclaw/topology/storage.py` — 4 new storage functions + _default_memory_profile() helper

## Decisions Made

- Affinity normalization uses fractional deviation from equal-share (1/3 each), mapped to [0,10] scale. Equal corrections for all archetypes → [5.0, 5.0, 5.0]. This is stable and interpretable.
- The `explore` parameter is passed by the caller rather than drawn internally, enforcing session-level epsilon-greedy (one random draw per scoring session, covering all archetypes simultaneously).
- `PatternExtractor.extract()` uses `asyncio.run()` to bridge sync → async for the LLM call, consistent with Phase 63's correction.py pattern.
- `active_pattern_ids` in the profile stores the first 40 chars of each pattern's text string — lightweight enough for storage, sufficient for human inspection and deduplication hints.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `MemoryProfiler` and `PatternExtractor` are ready for Plan 02 integration into the rubric scorer's `preference_fit` dimension
- `get_preference_fit()` API is stable: returns int in [0,10], neutral at 5 when below threshold or exploring
- Storage functions tested and atomic — safe for concurrent L3 access

---
*Phase: 64-structural-memory*
*Completed: 2026-03-04*

## Self-Check: PASSED

- FOUND: packages/orchestration/src/openclaw/topology/memory.py
- FOUND: packages/orchestration/tests/test_structural_memory.py
- FOUND: .planning/phases/64-structural-memory/64-01-SUMMARY.md
- FOUND commit e7ce400 (feat: implementation)
- FOUND commit 8cd23ef (test: RED tests)
