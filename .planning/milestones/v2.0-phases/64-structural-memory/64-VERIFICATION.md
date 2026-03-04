---
phase: 64-structural-memory
verified: 2026-03-04T08:35:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 64: Structural Memory Verification Report

**Phase Goal:** The system accumulates correction history, extracts structural preferences, and uses them to improve future proposals — while keeping topology data completely isolated from L3 agent SOUL context.
**Verified:** 2026-03-04T08:35:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | After a correction, the system stores the diff with timestamp, project_id, correction_type, and approved_archetype | VERIFIED | `approval.py` calls `ArchetypeClassifier().classify(approved_graph)` to set `annotations["approved_archetype"]` before `append_changelog()`. `storage.py:append_changelog` is atomic with fcntl. |
| 2 | After 5+ corrections accumulate, the system extracts recurring structural patterns via LLM | VERIFIED | `PatternExtractor.extract()` in `memory.py:329-332` returns `[]` immediately when `len(changelog) < self.min_threshold`. Above threshold, calls `asyncio.run(call_llm(...))`. `test_pattern_extraction_above_threshold` passes. |
| 3 | Preference profile computes archetype affinity using exponential decay weighting | VERIFIED | `MemoryProfiler._decay_weight()` returns `math.exp(-self.decay_lambda * age_days)`. `compute_profile()` multiplies each signal by the decay weight before accumulation. `test_decay_weights_older_corrections_less` passes. |
| 4 | Epsilon-greedy exploration returns neutral preference_fit of 5 for all archetypes 20% of the time (session-level) | VERIFIED | `get_preference_fit(archetype, explore=True)` returns 5. In `propose.py:609`, `explore = random.random() < topo_config.get("exploration_rate", 0.20)` is drawn once per session, then passed to all `score_proposal()` calls. `test_epsilon_greedy_exploration` passes. |
| 5 | Older corrections contribute less weight than recent corrections | VERIFIED | Exponential decay with `decay_lambda=0.05` gives ~50% weight after 14 days (`math.exp(-0.05*14) ≈ 0.496`). `test_decay_weights_older_corrections_less` confirms a 14-day-old correction has approximately half the weight of today's. |
| 6 | L3 SOUL context never contains topology, archetype, rubric, or structural memory content | VERIFIED | Dual-layer isolation in `spawn.py`: Layer 1 pre-filter at line 587-597 strips structural categories after `_retrieve_memories_sync()`. Layer 2 in `_format_memory_context()` drops any stragglers at lines 282-290. `EXCLUDED_CATEGORIES = frozenset({"structural_correction", "structural_preference", "structural_pattern"})`. `test_both_layers_combined_no_structural_leakage` and `test_augmented_soul_has_no_topology_content` pass. |
| 7 | Dual-layer L3 isolation: pre-filter after retrieval (Layer 1) AND drop inside `_format_memory_context` via EXCLUDED_CATEGORIES (Layer 2) | VERIFIED | Both layers present in `spawn.py`. Layer 1 at lines 587-597. Layer 2 at lines 282-290. 16 isolation tests all pass. |
| 8 | preference_fit in rubric scoring is computed dynamically from memory profile when data is sufficient | VERIFIED | `rubric.py:111-127` replaces hardcoded `preference_fit = 5` with conditional `MemoryProfiler.get_preference_fit()` when both `project_id` and `archetype` are provided. Falls back to 5 otherwise. |
| 9 | User can run `openclaw-propose memory` and see correction count, threshold status, and top patterns | VERIFIED | `propose.py:370-467` defines `_run_memory_report()`. Early subcommand detection at lines 471-472. Displays correction count, threshold status, archetype affinity, and top patterns. |
| 10 | After approval, MemoryProfiler.compute_profile is called to keep profile current | VERIFIED | `approval.py:121-130` calls `profiler.compute_profile()` in a `try/except` block after `delete_pending_proposals()`. Non-blocking on failure. |

**Score:** 10/10 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/orchestration/src/openclaw/topology/memory.py` | MemoryProfiler and PatternExtractor classes | VERIFIED | 383 lines (min 150). Both classes present with full implementation. |
| `packages/orchestration/src/openclaw/topology/storage.py` | save_memory_profile, load_memory_profile, save_patterns, load_patterns | VERIFIED | All 4 functions present at lines 272-368. Uses fcntl LOCK_EX + tmp/rename pattern. |
| `packages/orchestration/src/openclaw/config.py` | New topology config keys: exploration_rate, decay_lambda, pattern_extraction_threshold | VERIFIED | All 3 keys present at lines 370-372 with correct defaults (0.20, 0.05, 5). |
| `packages/orchestration/tests/test_structural_memory.py` | Unit tests for memory module | VERIFIED | 428 lines (min 100). 22 tests, all pass. |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skills/spawn/spawn.py` | EXCLUDED_CATEGORIES frozenset and pre-filter | VERIFIED | EXCLUDED_CATEGORIES at lines 231-235. Pre-filter at lines 587-597. Layer 2 defense-in-depth at lines 282-290. |
| `packages/orchestration/src/openclaw/topology/rubric.py` | Dynamic preference_fit from memory profile | VERIFIED | `load_memory_profile` indirectly used via `MemoryProfiler.get_preference_fit()`. Dynamic branch at lines 111-127. |
| `packages/orchestration/src/openclaw/cli/propose.py` | memory subcommand with --detail flag | VERIFIED | `_run_memory_report()` at line 370. Early detection at lines 471-472. --detail flag handled at line 449. |
| `packages/orchestration/tests/test_spawn_isolation.py` | L3 isolation verification tests for both layers | VERIFIED | 373 lines (min 40). 16 tests, all pass. |

---

## Key Link Verification

### Plan 01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `topology/memory.py` | `topology/storage.py` | load_changelog, save_memory_profile, load_memory_profile, save_patterns, load_patterns | WIRED | `from openclaw.topology.storage import (load_changelog, save_memory_profile, load_memory_profile, save_patterns, load_patterns)` at lines 24-30 |
| `topology/memory.py` | `topology/llm_client.py` | call_llm for pattern extraction | WIRED | `from openclaw.topology.llm_client import call_llm, strip_markdown_fences` at line 23. Used in `PatternExtractor.extract()` at line 359. |
| `topology/memory.py` | `config.py` | get_topology_config for decay_lambda, exploration_rate | WIRED | `from openclaw.config import get_topology_config` at line 22. Used in `__init__` of both classes. |

### Plan 02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `topology/rubric.py` | `topology/storage.py` | load_memory_profile for preference_fit | WIRED | `load_memory_profile` accessed via `MemoryProfiler.get_preference_fit()`. Import inside function at line 114: `from openclaw.topology.memory import MemoryProfiler`. |
| `topology/approval.py` | `topology/memory.py` | MemoryProfiler.compute_profile() called after approval | WIRED | `from openclaw.topology.memory import MemoryProfiler` at line 121. `profiler.compute_profile()` at line 130. |
| `skills/spawn/spawn.py` | `EXCLUDED_CATEGORIES` | pre-filter after retrieval AND category check inside _format_memory_context | WIRED | Both layers present. `EXCLUDED_CATEGORIES` referenced in both Layer 1 pre-filter (line 592) and Layer 2 format loop (line 283). |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| SMEM-01 | 64-01 | System stores all topology correction diffs with timestamps, project context, and correction type | SATISFIED | `approval.py` builds entry with timestamp, correction_type, diff, annotations. `append_changelog()` persists atomically. |
| SMEM-02 | 64-02 | Structural memory is categorically isolated from L3 execution memory | SATISFIED | `EXCLUDED_CATEGORIES` frozenset + dual-layer isolation in `spawn.py`. 16 isolation tests pass. |
| SMEM-03 | 64-01 | System extracts recurring patterns from accumulated corrections | SATISFIED | `PatternExtractor.extract()` calls LLM when threshold met, saves patterns to `patterns.json`. |
| SMEM-04 | 64-01 | System builds user structural preference profile that influences the "preference fit" rubric score | SATISFIED | `MemoryProfiler.compute_profile()` builds and persists `memory-profile.json`. `rubric.py` reads it dynamically. |
| SMEM-05 | 64-01 | Preference profiling includes decay and epsilon-greedy exploration | SATISFIED | Exponential decay via `_decay_weight()`, epsilon-greedy via `explore` param drawn once per session in `propose.py`. |
| SMEM-06 | 64-02 | System can report correction count and whether profiling has reached minimum data threshold | SATISFIED | `openclaw-propose memory` subcommand shows counts, threshold_status ("active"/"below_threshold"), and patterns. |

**All 6 SMEM requirements satisfied. No orphaned requirements.**

---

## Anti-Patterns Found

None. Scanned `memory.py`, `storage.py`, `spawn.py`, `rubric.py`, `approval.py`, `propose.py`.

- `return []` instances in `storage.py` and `memory.py` are correct empty-list returns for missing files, not stubs.
- No TODO/FIXME/HACK/PLACEHOLDER comments in any modified file.
- No empty handlers or console.log-only implementations.

---

## Human Verification Required

### 1. Memory Report Visual Output

**Test:** Run `openclaw-propose memory --project <project_id>` in an environment where corrections exist.
**Expected:** Terminal shows formatted correction count, threshold status (green "active" or yellow "below_threshold"), archetype affinity bars, and top patterns.
**Why human:** Terminal color codes (Colors.GREEN, Colors.YELLOW, Colors.BOLD) and visual bar rendering cannot be asserted programmatically in unit tests.

### 2. Live L3 Spawn Isolation

**Test:** Run an actual L3 spawn where structural memories are present in memU. Inspect the generated `/run/openclaw/soul.md` inside the container.
**Expected:** No content from structural_correction, structural_preference, or structural_pattern categories appears anywhere in the SOUL context.
**Why human:** Unit tests mock `_retrieve_memories_sync` and `_format_memory_context`. Live integration requires an actual memU instance with structural data.

### 3. Approval-to-Profile Flow End-to-End

**Test:** Approve a topology 5+ times, then run `openclaw-propose memory`. Verify archetype affinity values reflect the approved archetypes.
**Expected:** If lean was consistently approved, `lean` affinity should be above 5.0; others below.
**Why human:** Requires a running system with real changelog data to validate the full decay-weighted computation produces observable behavioral change in scoring.

---

## Summary

Phase 64 goal is fully achieved. All 10 observable truths are verified against the actual codebase. The implementation is substantive, wired, and tested:

- **Structural memory data layer** (Plan 01): `memory.py` is 383 lines with complete MemoryProfiler and PatternExtractor implementations. Config, storage, and all key links are wired and tested with 22 unit tests.
- **System wiring** (Plan 02): Dual-layer L3 isolation in `spawn.py` uses both a pre-filter and defense-in-depth. `rubric.py` dynamic preference_fit replaces the hardcoded constant. `approval.py` recomputes the profile after every approval. `propose.py` exposes the memory subcommand with compact and detail modes.
- **Tests:** 38 Phase 64 tests pass (22 memory + 16 isolation). Full suite: 670 pass, 5 pre-existing failures unrelated to Phase 64.
- **Commits verified:** `8cd23ef`, `e7ce400` (Plan 01), `b8ffd3c`, `a4215b7` (Plan 02).
- **All 6 SMEM requirements satisfied with direct code evidence.**

Human verification is optional (3 items flagged for visual/integration validation).

---

_Verified: 2026-03-04T08:35:00Z_
_Verifier: Claude (gsd-verifier)_
