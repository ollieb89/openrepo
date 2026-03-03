---
phase: 64
slug: structural-memory
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 64 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 7.0 |
| **Config file** | none — discovered automatically |
| **Quick run command** | `uv run pytest packages/orchestration/tests/test_structural_memory.py packages/orchestration/tests/test_spawn_isolation.py -x` |
| **Full suite command** | `uv run pytest packages/orchestration/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/orchestration/tests/test_structural_memory.py packages/orchestration/tests/test_spawn_isolation.py -x`
- **After every plan wave:** Run `uv run pytest packages/orchestration/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 64-01-01 | 01 | 0 | SMEM-01 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_correction_stored_with_metadata -x` | ❌ W0 | ⬜ pending |
| 64-01-02 | 01 | 0 | SMEM-01 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_corrections_retrievable_by_project -x` | ❌ W0 | ⬜ pending |
| 64-01-03 | 01 | 0 | SMEM-02 | unit | `uv run pytest packages/orchestration/tests/test_spawn_isolation.py::test_structural_categories_excluded_from_soul -x` | ❌ W0 | ⬜ pending |
| 64-01-04 | 01 | 0 | SMEM-02 | unit | `uv run pytest packages/orchestration/tests/test_spawn_isolation.py::test_augmented_soul_has_no_topology_content -x` | ❌ W0 | ⬜ pending |
| 64-01-05 | 01 | 0 | SMEM-03 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_pattern_extraction_above_threshold -x` | ❌ W0 | ⬜ pending |
| 64-01-06 | 01 | 0 | SMEM-03 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_pattern_extraction_below_threshold -x` | ❌ W0 | ⬜ pending |
| 64-01-07 | 01 | 0 | SMEM-04 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_preference_fit_uses_profile -x` | ❌ W0 | ⬜ pending |
| 64-01-08 | 01 | 0 | SMEM-04 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_preference_fit_neutral_below_threshold -x` | ❌ W0 | ⬜ pending |
| 64-01-09 | 01 | 0 | SMEM-05 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_decay_weights_older_corrections_less -x` | ❌ W0 | ⬜ pending |
| 64-01-10 | 01 | 0 | SMEM-05 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_epsilon_greedy_exploration -x` | ❌ W0 | ⬜ pending |
| 64-01-11 | 01 | 0 | SMEM-06 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_memory_report_correction_count -x` | ❌ W0 | ⬜ pending |
| 64-01-12 | 01 | 0 | SMEM-06 | unit | `uv run pytest packages/orchestration/tests/test_structural_memory.py::test_memory_report_threshold_status -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/orchestration/tests/test_structural_memory.py` — stubs for SMEM-01, SMEM-03, SMEM-04, SMEM-05, SMEM-06
- [ ] `packages/orchestration/tests/test_spawn_isolation.py` — stubs for SMEM-02

*Existing `test_spawn_memory.py` provides test structure patterns but does not cover Phase 64 requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| L3 SOUL visually clean of topology content | SMEM-02 | Confirms end-to-end in real Docker spawn | Spawn test L3 after writing structural data, inspect `/run/openclaw/soul.md` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
