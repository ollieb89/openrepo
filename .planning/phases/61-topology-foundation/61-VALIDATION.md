---
phase: 61
slug: topology-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 61 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `uv run pytest`) |
| **Config file** | `packages/orchestration/pyproject.toml` |
| **Quick run command** | `uv run pytest packages/orchestration/tests/test_topology_models.py packages/orchestration/tests/test_topology_diff.py packages/orchestration/tests/test_topology_classifier.py -v` |
| **Full suite command** | `uv run pytest packages/orchestration/tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/orchestration/tests/test_topology_models.py packages/orchestration/tests/test_topology_diff.py packages/orchestration/tests/test_topology_classifier.py -v`
- **After every plan wave:** Run `uv run pytest packages/orchestration/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 61-01-01 | 01 | 1 | TOPO-01 | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "test_graph_with_all_edge_types" -x` | ✅ | ⬜ pending |
| 61-01-02 | 01 | 1 | TOPO-02 | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "roundtrip" -x` | ✅ | ⬜ pending |
| 61-01-03 | 01 | 1 | TOPO-03 | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "created_at or version" -x` | ✅ | ⬜ pending |
| 61-01-04 | 01 | 1 | TOPO-04 | unit | `uv run pytest packages/orchestration/tests/test_topology_diff.py -x` | ✅ | ⬜ pending |
| 61-01-05 | 01 | 1 | TOPO-05 | unit | `uv run pytest packages/orchestration/tests/test_topology_classifier.py -x` | ✅ | ⬜ pending |
| 61-01-06 | 01 | 1 | TOPO-06 | unit | `uv run pytest packages/orchestration/tests/test_topology_models.py -k "topology_dir" -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. 55 tests exist and pass as of 2026-03-04.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
