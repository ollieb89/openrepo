"""
Integration tests for metrics lifecycle via collect_metrics_from_state().

These tests verify that metrics reflect real JarvisState task transitions:
- completed task increments completed count
- in_progress task appears in active count
- full lifecycle (pending -> in_progress -> completed) produces correct final metrics

Run from project root:
    uv run pytest packages/orchestration/tests/test_metrics_lifecycle.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

from openclaw.metrics import collect_metrics_from_state
from openclaw.state_engine import JarvisState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state_file(tmp_path: Path) -> Path:
    state_file = tmp_path / "workspace-state.json"
    state_file.write_text(
        json.dumps({"version": "1.0.0", "tasks": {}, "metadata": {}})
    )
    return state_file


def _load_state_dict(state_file: Path) -> dict:
    return json.loads(state_file.read_text())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMetricsLifecycle:
    def test_completed_task_increments_metrics_count(self, tmp_path):
        """Creating and completing a task raises completed count to >= 1."""
        state_file = _make_state_file(tmp_path)

        js = JarvisState(state_file_path=state_file)
        js.create_task("task-001", skill_hint="test-skill")
        js.update_task("task-001", status="completed", activity_entry="done")

        state_dict = _load_state_dict(state_file)
        metrics = collect_metrics_from_state(state_dict)

        assert metrics["tasks"]["completed"] >= 1, (
            f"Expected completed >= 1, got {metrics['tasks']['completed']}"
        )

    def test_in_progress_task_shows_in_active_count(self, tmp_path):
        """Updating a task to in_progress raises active count to >= 1."""
        state_file = _make_state_file(tmp_path)

        js = JarvisState(state_file_path=state_file)
        js.create_task("task-002", skill_hint="test-skill")
        js.update_task("task-002", status="in_progress", activity_entry="started")

        state_dict = _load_state_dict(state_file)
        metrics = collect_metrics_from_state(state_dict)

        assert metrics["tasks"]["in_progress"] >= 1, (
            f"Expected in_progress >= 1, got {metrics['tasks']['in_progress']}"
        )
        # pool.active_containers mirrors in_progress count
        assert metrics["pool"]["active_containers"] >= 1

    def test_full_lifecycle_metrics_progression(self, tmp_path):
        """Metrics at each stage reflect pending -> in_progress -> completed transitions."""
        state_file = _make_state_file(tmp_path)
        js = JarvisState(state_file_path=state_file)

        js.create_task("task-003", skill_hint="test-skill")

        # Stage 1: pending
        metrics_pending = collect_metrics_from_state(_load_state_dict(state_file))
        assert metrics_pending["tasks"]["total"] >= 1
        assert metrics_pending["tasks"]["pending"] >= 1

        js.update_task("task-003", status="in_progress", activity_entry="started")

        # Stage 2: in_progress
        metrics_active = collect_metrics_from_state(_load_state_dict(state_file))
        assert metrics_active["tasks"]["in_progress"] >= 1

        js.update_task("task-003", status="completed", activity_entry="done")

        # Stage 3: completed — final assertions
        metrics_final = collect_metrics_from_state(_load_state_dict(state_file))
        assert metrics_final["tasks"]["total"] >= 1, (
            f"Expected total_tasks >= 1, got {metrics_final['tasks']['total']}"
        )
        assert metrics_final["tasks"]["completed"] >= 1, (
            f"Expected completed_tasks >= 1, got {metrics_final['tasks']['completed']}"
        )
        assert metrics_final["tasks"]["in_progress"] == 0
