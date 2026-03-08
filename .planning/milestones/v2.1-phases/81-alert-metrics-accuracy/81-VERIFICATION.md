---
phase: 81-alert-metrics-accuracy
verified: 2026-03-08T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Open dashboard with a project selected, trigger a simulated escalation, observe alert feed"
    expected: "Autonomy escalation alert appears in the per-project alert feed without page reload"
    why_human: "SSE streaming, bridge routing, and React state updates are not unit-testable; requires live system"
  - test: "Call GET /api/metrics?project=<project-with-override> and compare pool.max_concurrent to project.json l3_overrides.max_concurrent"
    expected: "Returned max_concurrent matches the project's configured override value, not hardcoded 3"
    why_human: "Requires a running dashboard + orchestration stack and a project with a non-default override"
---

# Phase 81: Alert & Metrics Accuracy Verification Report

**Phase Goal:** Close integration gaps GAP-03 (autonomy alerts missing from per-project dashboard feed) and GAP-04 (metrics endpoint always reporting max_concurrent=3 regardless of project config).
**Verified:** 2026-03-08
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `AutonomyEvent.to_dict()` includes a `project_id` key when project_id is supplied | VERIFIED | Line 57: `"project_id": self.project_id` in `to_dict()` return dict; test `test_to_dict_includes_project_id` passes |
| 2 | All hooks.py emit call sites pass project_id sourced from `_context_store` (stored during on_task_spawn) | VERIFIED | `_task_project_map` populated at line 75 in `on_task_spawn`; all 5 lifecycle functions (`on_container_healthy`, `on_task_complete`, `on_task_failed`, `update_confidence`, `on_task_removed`) look up `_task_project_map.get(task_id)` and pass it to every emit |
| 3 | on_task_failed escalation path emits an event with event_type `autonomy.escalation` directly via event_bus so the bridge forwards it | VERIFIED | Lines 317-325: `_direct_bus.emit({"event_type": "autonomy.escalation", ...})` in the `ESCALATING` branch; test `test_on_task_failed_emits_autonomy_escalation_event` passes |
| 4 | `collect_metrics_from_state(state_dict, project_id)` returns max_concurrent from project's l3_overrides config, not hardcoded 3 | VERIFIED | Lines 54-55: `pool_cfg = get_pool_config(project_id) if project_id else {}; max_concurrent = pool_cfg.get("max_concurrent", DEFAULT_POOL_MAX_CONCURRENT)`; test `test_collect_metrics_returns_project_max_concurrent` passes (value 5) |
| 5 | `collect_metrics_from_state(state_dict)` with no project_id returns the default DEFAULT_POOL_MAX_CONCURRENT (3) | VERIFIED | Empty-string default triggers the `if project_id else {}` branch returning `DEFAULT_POOL_MAX_CONCURRENT`; test `test_collect_metrics_default_max_concurrent` passes |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/orchestration/src/openclaw/autonomy/events.py` | project_id field on AutonomyEvent base dataclass + to_dict() key | VERIFIED | Line 43: `project_id: Optional[str] = None`; line 57: `"project_id": self.project_id`; all 8 subclass `from_dict()` methods updated to pass `project_id=data.get("project_id")` |
| `packages/orchestration/src/openclaw/autonomy/hooks.py` | project_id threading via `_task_project_map` + direct `autonomy.escalation` emit | VERIFIED | Line 39: `_task_project_map: Dict[str, str] = {}`; lines 317-325: direct `_direct_bus.emit({"event_type": "autonomy.escalation", ...})` in escalation branch |
| `packages/orchestration/src/openclaw/metrics.py` | `collect_metrics_from_state` with project_id parameter | VERIFIED | Line 29: `def collect_metrics_from_state(state_dict: Dict[str, Any], project_id: str = "") -> Dict[str, Any]`; line 121: `collect_metrics_from_state(state_dict, project_id)` in `write_python_metrics_snapshot` |
| `packages/orchestration/tests/autonomy/test_integration.py` | GAP-03 unit tests | VERIFIED | `TestGap03ProjectId` class with 4 tests: `test_to_dict_includes_project_id`, `test_to_dict_project_id_none_by_default`, `test_on_task_spawn_emits_with_project_id`, `test_on_task_failed_emits_autonomy_escalation_event` — all pass |
| `packages/orchestration/tests/test_python_metrics_snapshot.py` | GAP-04 unit tests | VERIFIED | `test_collect_metrics_default_max_concurrent` and `test_collect_metrics_returns_project_max_concurrent` — both pass; fixture correctly includes required `workspace` and `tech_stack` fields |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `hooks.py:on_task_spawn` | `_task_project_map` | `_task_project_map[task_id] = task_spec.get("project_id", "")` | WIRED | Line 75 confirmed in source |
| `hooks.py:on_task_failed` (escalation branch) | `event_bus.emit` | direct emit with `event_type="autonomy.escalation"` | WIRED | Lines 317-325 confirmed; `import openclaw.event_bus as _direct_bus` and `_direct_bus.emit({...})` present |
| `metrics.py:collect_metrics_from_state` | `get_pool_config` | `get_pool_config(project_id)` call when project_id truthy | WIRED | Line 54: `pool_cfg = get_pool_config(project_id) if project_id else {}` confirmed |
| `metrics.py:write_python_metrics_snapshot` | `collect_metrics_from_state` | `collect_metrics_from_state(state_dict, project_id)` | WIRED | Line 121 confirmed; project_id argument threaded from function parameter |

---

### Requirements Coverage

No formal requirement IDs for this phase — it closes integration gaps GAP-03 and GAP-04 identified in the v2.1 milestone audit. The behavioral contracts from the success criteria are all satisfied:

| Success Criterion | Status | Evidence |
|-------------------|--------|----------|
| Full test suite exits 0 with no failures | SATISFIED | 785 passed in 9.45s (confirmed by live run) |
| `events.py` contains `project_id: Optional[str] = None` field and `"project_id": self.project_id` in `to_dict()` | SATISFIED | Lines 43 and 57 confirmed |
| `hooks.py` contains `_task_project_map` dict and direct `event_bus.emit({"event_type": "autonomy.escalation", ...})` call | SATISFIED | Lines 39 and 317-325 confirmed |
| `metrics.py` has `collect_metrics_from_state(state_dict, project_id: str = "")` signature and calls `get_pool_config(project_id)` | SATISFIED | Lines 29 and 54 confirmed |
| No regressions — existing test count preserved (only additions) | SATISFIED | 779 before → 785 after; 6 new tests added |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `hooks.py` | 317 | `import time as _time` inside function body (in escalation branch) | Info | Unconventional but harmless; avoids circular import concerns at module top |
| `hooks.py` | 318 | `import openclaw.event_bus as _direct_bus` inside function body | Info | Same pattern; acceptable for lazy import to avoid circular import at module level |
| `metrics.py` | 74-76 | `autonomy.active_contexts` and `escalations_24h` remain hardcoded 0 | Warning | Out of scope for this phase (confirmed deferred per RESEARCH.md); does not block GAP-03/GAP-04 goals |

No blockers found. The inline imports in the escalation branch are unconventional but functionally correct — the module-level import at line 322 imports `openclaw.event_bus` correctly for the direct emit path.

---

### Human Verification Required

#### 1. Live dashboard escalation alert

**Test:** With dashboard running (`make dashboard`), call `hooks.on_task_spawn("task-x", {"project_id": "pumplai", "max_retries": 0})` and then `hooks.on_task_failed("task-x", "test error")` from the Python REPL. Open the dashboard at `http://localhost:6987` with project `pumplai` selected.
**Expected:** An escalation alert appears in the per-project alert feed.
**Why human:** SSE streaming, bridge routing, and React component rendering are not exercised by unit tests. The chain (Python event_bus → bridge → SSE → TypeScript useAlerts → AlertFeed render) requires a live stack.

#### 2. Live metrics endpoint validation

**Test:** Ensure a project has `l3_overrides.max_concurrent` set to a non-default value (e.g., 5) in its `project.json`. Start orchestration, then call `GET /api/metrics?project=<that-project-id>`.
**Expected:** The `python.pool.max_concurrent` field in the response equals the configured value (e.g., 5), not 3.
**Why human:** The API endpoint wiring (Next.js route → Python metrics snapshot file read) requires a running stack to test end-to-end.

---

### Commit Evidence

| Commit | Description | Files |
|--------|-------------|-------|
| `ed1a8bb` | test(81-01): add failing tests for GAP-03 and GAP-04 | test_integration.py, test_python_metrics_snapshot.py |
| `333b03b` | feat(81-01): GAP-03 — add project_id to AutonomyEvent and thread through hooks | events.py, hooks.py |
| `ffa840b` | feat(81-01): GAP-04 — thread project_id through collect_metrics_from_state | metrics.py, test fixture fix |

All three commits confirmed present in git history.

---

### Test Results

```
785 passed in 9.45s
```

6 new tests (4 GAP-03 + 2 GAP-04) all pass. Zero regressions from the 779 pre-phase tests.

---

### Gaps Summary

No gaps. All five must-have truths are verified at all three levels (exists, substantive, wired). The phase goal is achieved: autonomy events now carry real `project_id` values that pass the dashboard's per-project filter, and the metrics endpoint reads `max_concurrent` from per-project config rather than using a hardcoded constant.

Two items are flagged for human verification (live system testing of SSE routing and API response) — these are behavioral validations that automated grep cannot substitute for. They do not indicate gaps in the implementation; the implementation is complete.

---

_Verified: 2026-03-08_
_Verifier: Claude (gsd-verifier)_
