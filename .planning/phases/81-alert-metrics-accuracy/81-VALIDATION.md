---
phase: 81
slug: alert-metrics-accuracy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 81 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run) |
| **Config file** | `packages/orchestration/pyproject.toml` |
| **Quick run command** | `uv run pytest packages/orchestration/tests/autonomy/ packages/orchestration/tests/test_python_metrics_snapshot.py -x -q` |
| **Full suite command** | `uv run pytest packages/orchestration/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/orchestration/tests/autonomy/ packages/orchestration/tests/test_python_metrics_snapshot.py -x -q`
- **After every plan wave:** Run `uv run pytest packages/orchestration/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 81-01-01 | 01 | 1 | GAP-03a | unit | `uv run pytest packages/orchestration/tests/autonomy/ -k "project_id" -x` | ❌ W0 | ⬜ pending |
| 81-01-02 | 01 | 1 | GAP-03b | unit | `uv run pytest packages/orchestration/tests/autonomy/test_integration.py -x` | ✅ extend | ⬜ pending |
| 81-01-03 | 01 | 1 | GAP-03c | unit | `uv run pytest packages/orchestration/tests/autonomy/test_integration.py -k "escalat" -x` | ✅ extend | ⬜ pending |
| 81-01-04 | 01 | 1 | GAP-04a | unit | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -x` | ✅ extend | ⬜ pending |
| 81-01-05 | 01 | 1 | GAP-04b | unit | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -x` | ✅ extend | ⬜ pending |
| 81-01-06 | 01 | 1 | GAP-04c | unit | `uv run pytest packages/orchestration/tests/test_python_metrics_snapshot.py -k "override" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/orchestration/tests/autonomy/test_integration.py` — add `test_to_dict_includes_project_id` and update existing `on_task_spawn` fixtures to pass `project_id` in task_spec
- [ ] `packages/orchestration/tests/test_python_metrics_snapshot.py` — add `test_collect_metrics_returns_project_max_concurrent` with tmp_path project.json fixture
- [ ] `packages/orchestration/tests/autonomy/test_integration.py` — add `test_on_task_failed_emits_autonomy_escalation_event` verifying `"autonomy.escalation"` event type is emitted

*All tests are extensions to existing files — no new test files needed, no new framework to install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Alert appears in dashboard alert feed | GAP-03 (success criterion 2) | Requires live bridge + dashboard | 1. Start dashboard (`make dashboard`); 2. Call `hooks.on_task_spawn("task-x", {"project_id": "pumplai", "max_retries": 0})`; 3. Confirm alert in per-project feed |
| `/api/metrics` returns correct `max_concurrent` | GAP-04 (success criterion 3) | Requires live API | 1. `GET /api/metrics?project=pumplai`; 2. Confirm `python.pool.max_concurrent` matches `projects/pumplai/project.json` → `l3_overrides.max_concurrent` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
