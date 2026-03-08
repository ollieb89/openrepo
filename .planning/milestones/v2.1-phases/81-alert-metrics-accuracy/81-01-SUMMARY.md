---
phase: 81-alert-metrics-accuracy
plan: 01
subsystem: autonomy-events, metrics
tags: [gap-fix, tdd, project-id-threading, metrics-accuracy, event-bus]
dependency_graph:
  requires: []
  provides:
    - project_id field on AutonomyEvent base dataclass
    - project_id threading via _task_project_map in hooks.py
    - direct autonomy.escalation emit for bridge routing
    - collect_metrics_from_state with project_id parameter
  affects:
    - packages/orchestration/src/openclaw/autonomy/events.py
    - packages/orchestration/src/openclaw/autonomy/hooks.py
    - packages/orchestration/src/openclaw/metrics.py
tech_stack:
  added: []
  patterns:
    - module-level dict for cross-call state threading (_task_project_map)
    - dual emit pattern (AutonomyEscalationTriggered + direct autonomy.escalation)
    - backward-compatible signature extension (project_id: str = "")
key_files:
  created: []
  modified:
    - packages/orchestration/src/openclaw/autonomy/events.py
    - packages/orchestration/src/openclaw/autonomy/hooks.py
    - packages/orchestration/src/openclaw/metrics.py
    - packages/orchestration/tests/autonomy/test_integration.py
    - packages/orchestration/tests/test_python_metrics_snapshot.py
decisions:
  - project_id uses Optional[str] = None on the dataclass field (not "") so to_dict() can
    distinguish "not supplied" (None) from "supplied empty string"
  - hooks.py stores project_id as str in _task_project_map but converts "" to None when
    passing to event constructors (or None for empty string)
  - dual emit in escalation: AutonomyEscalationTriggered (legacy) + direct autonomy.escalation
    dict (bridge routing) — keeps backward compat while satisfying bridge subscription
  - test fixture for GAP-04 requires workspace + tech_stack fields in project.json to pass
    validation (Rule 2 auto-fix applied to test)
metrics:
  duration: 5 min 21 sec
  completed: "2026-03-08"
  tasks_completed: 3
  files_modified: 5
  tests_before: 779
  tests_after: 785
  new_tests: 6
---

# Phase 81 Plan 01: Alert & Metrics Accuracy (GAP-03, GAP-04) Summary

**One-liner:** Surgically fixed two silent integration gaps — project_id threading into
AutonomyEvent envelopes (GAP-03) and per-project max_concurrent metric lookup (GAP-04).

## What Was Built

### GAP-03: project_id Threading (events.py + hooks.py)

**Problem:** AutonomyEventBus emitted envelopes with `project_id` absent, causing
`useLiveEvents.ts` to silently drop all autonomy alerts (it filters by project_id).
The escalation path also used `event_type='autonomy.escalation_triggered'` while the
bridge subscribed to `EventType.AUTONOMY_ESCALATION = 'autonomy.escalation'`.

**Fix:**
1. Added `project_id: Optional[str] = None` to `AutonomyEvent` base dataclass (between
   `timestamp` and `event_type` to satisfy Python dataclass ordering)
2. Added `"project_id": self.project_id` to `to_dict()` return dict
3. Updated all 8 subclass `from_dict()` methods to pass `project_id=data.get("project_id")`
4. Added `_task_project_map: Dict[str, str] = {}` to hooks.py for per-task project tracking
5. All 6 hook functions (`on_task_spawn`, `on_container_healthy`, `on_task_complete`,
   `on_task_failed`, `update_confidence`, `on_task_removed`) updated to thread project_id
6. Added direct `event_bus.emit({"event_type": "autonomy.escalation", ...})` in the
   escalation branch of `on_task_failed` so the bridge forwards it to the dashboard SSE stream

### GAP-04: Per-Project max_concurrent Metric (metrics.py)

**Problem:** `collect_metrics_from_state()` always returned `max_concurrent: 3` (hardcoded),
ignoring per-project `l3_overrides.max_concurrent` from project.json. The dashboard always
showed 3/3 capacity regardless of actual pool configuration.

**Fix:**
1. Changed signature to `collect_metrics_from_state(state_dict, project_id: str = "")`
   (default `""` preserves backward compatibility with all 5 existing callers)
2. Added `DEFAULT_POOL_MAX_CONCURRENT` import from `.config`
3. Replaced hardcoded `3` with `get_pool_config(project_id)` call when `project_id` truthy;
   falls back to `DEFAULT_POOL_MAX_CONCURRENT` (still 3) when not provided
4. Updated `write_python_metrics_snapshot` to pass `project_id` to `collect_metrics_from_state`

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing tests (TDD RED) | ed1a8bb | test_integration.py, test_python_metrics_snapshot.py |
| 2 | GAP-03 — events.py + hooks.py (TDD GREEN) | 333b03b | events.py, hooks.py |
| 3 | GAP-04 — metrics.py (TDD GREEN) | ffa840b | metrics.py, test fixture fix |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Validation] Test fixture for GAP-04 missing required project.json fields**

- **Found during:** Task 3 (first test run after metrics.py changes)
- **Issue:** The test's project.json only had `{"l3_overrides": {"max_concurrent": 5}}`,
  but `get_pool_config` calls `load_project_config` which validates `workspace` and
  `tech_stack` as required fields. Validation failure caused fallback to default (3),
  making the test assertion fail.
- **Fix:** Updated `test_collect_metrics_returns_project_max_concurrent` fixture to include
  all required fields: `workspace`, `tech_stack`, `l3_overrides`
- **Files modified:** `packages/orchestration/tests/test_python_metrics_snapshot.py`
- **Commit:** ffa840b (included in Task 3 commit)

## Verification Results

Final gate: `uv run pytest packages/orchestration/tests/ -v`

- **Before:** 779 tests
- **After:** 785 tests (6 new: 4 GAP-03 + 2 GAP-04)
- **Result:** 785 passed, 0 failed

Spot-check confirmations:
- `events.py` contains `project_id: Optional[str] = None` field and `"project_id": self.project_id` in `to_dict()`
- `hooks.py` contains `_task_project_map` dict and direct `event_bus.emit({"event_type": "autonomy.escalation", ...})` in escalation branch
- `metrics.py` has `collect_metrics_from_state(state_dict, project_id: str = "")` signature and calls `get_pool_config(project_id)` to set `max_concurrent`

## Self-Check: PASSED

Files exist:
- FOUND: packages/orchestration/src/openclaw/autonomy/events.py
- FOUND: packages/orchestration/src/openclaw/autonomy/hooks.py
- FOUND: packages/orchestration/src/openclaw/metrics.py
- FOUND: packages/orchestration/tests/autonomy/test_integration.py
- FOUND: packages/orchestration/tests/test_python_metrics_snapshot.py

Commits exist:
- FOUND: ed1a8bb (test RED)
- FOUND: 333b03b (GAP-03 GREEN)
- FOUND: ffa840b (GAP-04 GREEN)
