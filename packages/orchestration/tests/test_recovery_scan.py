"""
Tests for pool startup recovery scan (REL-06, REL-07).

Validates that:
- run_recovery_scan() detects orphaned tasks in in_progress/interrupted/starting states
- mark_failed policy: updates task to failed with RECOVERED message
- manual policy: leaves state unchanged, counts for summary
- auto_retry policy: checks git for partial commits, respects retry limit of 1
- Missing spawn_requested_at treated as expired (not silently skipped)
- Tasks within timeout window are skipped (not recovered)
- Empty state produces scanned=0 and zero counts
- Startup summary always logged
- get_pool_config() validates recovery_policy correctly

All tests are pure async/mock — no Docker daemon needed.
"""

import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, call

import pytest

# conftest.py adds skills/spawn_specialist to sys.path
from pool import L3ContainerPool


def _make_pool(project_id: str = "test-project", recovery_policy: str = "mark_failed") -> L3ContainerPool:
    """Create a pool instance for testing with the given recovery policy."""
    pool = L3ContainerPool(max_concurrent=3, project_id=project_id)
    pool._pool_config = {
        "max_concurrent": 3,
        "pool_mode": "shared",
        "overflow_policy": "wait",
        "queue_timeout_s": 300,
        "recovery_policy": recovery_policy,
    }
    return pool


def _make_task(
    status: str,
    skill_hint: str = "code",
    age_s: float = 700.0,
    timeout_s: int = 600,
    retry_count: int = 0,
    spawn_requested_at: object = "auto",  # "auto" = time.time() - age_s
) -> dict:
    """Create a mock task dict for testing."""
    if spawn_requested_at == "auto":
        _spawn_requested_at = time.time() - age_s
    else:
        _spawn_requested_at = spawn_requested_at

    return {
        "status": status,
        "skill_hint": skill_hint,
        "metadata": {
            "spawn_requested_at": _spawn_requested_at,
            "retry_count": retry_count,
        },
    }


@pytest.mark.asyncio
async def test_recovery_policy_default_mark_failed():
    """Default mark_failed policy marks an orphaned interrupted task as failed."""
    pool = _make_pool(recovery_policy="mark_failed")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = ["task-001"]
    mock_jarvis.read_task.return_value = _make_task("interrupted", age_s=700, timeout_s=600)

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.get_skill_timeout", return_value=600):

        result = await pool.run_recovery_scan()

    assert result["scanned"] == 1
    assert result["mark_failed"] == 1
    assert result["retried"] == 0
    assert result["manual"] == 0

    # Assert update_task was called with "failed" and message containing "RECOVERED"
    mock_jarvis.update_task.assert_called_once()
    call_kwargs = mock_jarvis.update_task.call_args
    assert call_kwargs[1]["status"] == "failed"
    assert "RECOVERED" in call_kwargs[1]["activity_entry"]
    assert "mark_failed" in call_kwargs[1]["activity_entry"]


@pytest.mark.asyncio
async def test_recovery_policy_manual_leaves_state():
    """manual policy leaves task state unchanged and counts for summary."""
    pool = _make_pool(recovery_policy="manual")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = ["task-002"]
    mock_jarvis.read_task.return_value = _make_task("interrupted", age_s=700, timeout_s=600)

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.get_skill_timeout", return_value=600):

        result = await pool.run_recovery_scan()

    assert result["scanned"] == 1
    assert result["manual"] == 1
    assert result["mark_failed"] == 0
    assert result["retried"] == 0

    # update_task must NOT be called for manual policy
    mock_jarvis.update_task.assert_not_called()


@pytest.mark.asyncio
async def test_recovery_policy_auto_retry_no_commits():
    """auto_retry policy with no existing commits flags task for retry."""
    pool = _make_pool(recovery_policy="auto_retry")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = ["task-003"]
    mock_jarvis.read_task.return_value = _make_task("in_progress", age_s=700, timeout_s=600, retry_count=0)

    # Mock subprocess.run to return empty stdout (no commits on branch)
    mock_subprocess = MagicMock()
    mock_subprocess.stdout = ""  # no commits

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.get_skill_timeout", return_value=600), \
         patch("pool.get_workspace_path", return_value="/fake/workspace"), \
         patch("pool.subprocess.run", return_value=mock_subprocess):

        result = await pool.run_recovery_scan()

    assert result["scanned"] == 1
    assert result["retried"] == 1
    assert result["mark_failed"] == 0

    # update_task was called (flagged for retry)
    mock_jarvis.update_task.assert_called_once()
    call_kwargs = mock_jarvis.update_task.call_args
    assert "auto_retry" in call_kwargs[1]["activity_entry"]


@pytest.mark.asyncio
async def test_recovery_policy_auto_retry_has_commits_fallback():
    """auto_retry falls back to mark_failed when partial commits exist on staging branch."""
    pool = _make_pool(recovery_policy="auto_retry")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = ["task-004"]
    mock_jarvis.read_task.return_value = _make_task("in_progress", age_s=700, timeout_s=600, retry_count=0)

    # Mock subprocess.run to return commit output (commits exist on branch)
    mock_subprocess = MagicMock()
    mock_subprocess.stdout = "abc1234 add feature X\n"

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.get_skill_timeout", return_value=600), \
         patch("pool.get_workspace_path", return_value="/fake/workspace"), \
         patch("pool.subprocess.run", return_value=mock_subprocess):

        result = await pool.run_recovery_scan()

    assert result["scanned"] == 1
    assert result["mark_failed"] == 1
    assert result["retried"] == 0

    call_kwargs = mock_jarvis.update_task.call_args
    assert call_kwargs[1]["status"] == "failed"
    assert "partial commits" in call_kwargs[1]["activity_entry"]


@pytest.mark.asyncio
async def test_recovery_policy_auto_retry_limit_reached():
    """auto_retry falls back to mark_failed when retry_count >= 1."""
    pool = _make_pool(recovery_policy="auto_retry")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = ["task-005"]
    mock_jarvis.read_task.return_value = _make_task("interrupted", age_s=700, timeout_s=600, retry_count=1)

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.get_skill_timeout", return_value=600):

        result = await pool.run_recovery_scan()

    assert result["scanned"] == 1
    assert result["mark_failed"] == 1
    assert result["retried"] == 0

    call_kwargs = mock_jarvis.update_task.call_args
    assert call_kwargs[1]["status"] == "failed"
    assert "retry limit" in call_kwargs[1]["activity_entry"]


@pytest.mark.asyncio
async def test_recovery_scan_skips_tasks_within_timeout():
    """Tasks still within the skill timeout window are NOT recovered."""
    pool = _make_pool(recovery_policy="mark_failed")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = ["task-006"]
    # age_s=100 is less than timeout_s=600 — should be skipped
    mock_jarvis.read_task.return_value = _make_task("in_progress", age_s=100, timeout_s=600)

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.get_skill_timeout", return_value=600):

        result = await pool.run_recovery_scan()

    # Task is within timeout — should not be scanned/recovered
    assert result["scanned"] == 0
    assert result["mark_failed"] == 0

    # update_task must NOT be called
    mock_jarvis.update_task.assert_not_called()


@pytest.mark.asyncio
async def test_recovery_scan_handles_missing_timestamp():
    """Tasks with no spawn_requested_at are treated as expired and recovered."""
    pool = _make_pool(recovery_policy="mark_failed")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = ["task-007"]
    # spawn_requested_at=None — missing timestamp
    mock_jarvis.read_task.return_value = _make_task(
        "interrupted",
        spawn_requested_at=None,
    )

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.get_skill_timeout", return_value=600), \
         patch("pool.logger") as mock_logger:

        result = await pool.run_recovery_scan()

    # Should be scanned and marked failed
    assert result["scanned"] == 1
    assert result["mark_failed"] == 1

    # A warning should have been logged about missing timestamp
    warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
    assert any("spawn_requested_at" in c or "no spawn_requested_at" in c.lower() for c in warning_calls)


@pytest.mark.asyncio
async def test_recovery_scan_empty_state():
    """Empty active task list produces scanned=0 and zero action counts."""
    pool = _make_pool(recovery_policy="mark_failed")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = []

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis):

        result = await pool.run_recovery_scan()

    assert result["scanned"] == 0
    assert result["mark_failed"] == 0
    assert result["retried"] == 0
    assert result["manual"] == 0

    mock_jarvis.update_task.assert_not_called()


@pytest.mark.asyncio
async def test_recovery_scan_logs_startup_summary():
    """Startup summary is always logged even when nothing was recovered."""
    pool = _make_pool(recovery_policy="mark_failed")

    mock_jarvis = MagicMock()
    mock_jarvis.list_active_tasks.return_value = []

    with patch("pool.get_state_path", return_value=Path("/fake/state.json")), \
         patch("pool.JarvisState", return_value=mock_jarvis), \
         patch("pool.logger") as mock_logger:

        await pool.run_recovery_scan()

    # Verify logger.info was called with the startup summary message
    info_calls = [str(c) for c in mock_logger.info.call_args_list]
    assert any("recovery scan complete" in c.lower() or "Pool startup" in c for c in info_calls)


@pytest.mark.asyncio
async def test_spawn_task_calls_recovery_scan():
    """spawn_task() calls run_recovery_scan() once, before spawn_and_monitor()."""
    # conftest.py adds skills/spawn_specialist to sys.path
    from pool import spawn_task

    call_order = []

    async def mock_recovery_scan(self):
        call_order.append("run_recovery_scan")
        return {"scanned": 0, "mark_failed": 0, "retried": 0, "manual": 0}

    async def mock_spawn_and_monitor(self, **kwargs):
        call_order.append("spawn_and_monitor")
        return {"status": "success", "task_id": kwargs.get("task_id", "task-1")}

    mock_pool_config = {
        "max_concurrent": 3,
        "pool_mode": "shared",
        "overflow_policy": "wait",
        "queue_timeout_s": 300,
        "recovery_policy": "mark_failed",
    }

    with patch("pool.get_pool_config", return_value=mock_pool_config), \
         patch("pool.get_workspace_path", return_value="/tmp/test"), \
         patch("pool.get_active_project_id", return_value="test-project"), \
         patch.object(L3ContainerPool, "run_recovery_scan", mock_recovery_scan), \
         patch.object(L3ContainerPool, "spawn_and_monitor", mock_spawn_and_monitor):

        result = await spawn_task(
            task_id="task-1",
            skill_hint="code",
            task_description="test description",
            workspace_path="/tmp/test",
            project_id="test-project",
        )

    # run_recovery_scan must be called exactly once
    assert call_order.count("run_recovery_scan") == 1, \
        f"Expected run_recovery_scan called once, got: {call_order}"

    # run_recovery_scan must be called BEFORE spawn_and_monitor
    assert call_order.index("run_recovery_scan") < call_order.index("spawn_and_monitor"), \
        f"run_recovery_scan must precede spawn_and_monitor, got order: {call_order}"

    # spawn_and_monitor should also be called once
    assert call_order.count("spawn_and_monitor") == 1


def test_project_config_recovery_policy_validation():
    """get_pool_config() correctly validates and falls back for recovery_policy."""
    import json
    import os
    import tempfile
    from pathlib import Path as _Path

    from openclaw.project_config import get_pool_config

    # Build a minimal project.json with l3_overrides
    def _make_project_json(overrides: dict) -> dict:
        return {
            "id": "test-proj",
            "name": "Test Project",
            "workspace": "/tmp/test-workspace",
            "tech_stack": {},
            "agents": {},
            "l3_overrides": overrides,
        }

    # Case 1: valid "auto_retry"
    with patch("orchestration.project_config.load_project_config") as mock_load:
        mock_load.return_value = _make_project_json({"recovery_policy": "auto_retry"})
        cfg = get_pool_config("test-proj")
    assert cfg["recovery_policy"] == "auto_retry", f"Expected auto_retry, got {cfg['recovery_policy']}"

    # Case 2: invalid value falls back to default
    with patch("orchestration.project_config.load_project_config") as mock_load:
        mock_load.return_value = _make_project_json({"recovery_policy": "invalid"})
        cfg = get_pool_config("test-proj")
    assert cfg["recovery_policy"] == "mark_failed", f"Expected mark_failed default, got {cfg['recovery_policy']}"

    # Case 3: no recovery_policy key — should return default
    with patch("orchestration.project_config.load_project_config") as mock_load:
        mock_load.return_value = _make_project_json({})
        cfg = get_pool_config("test-proj")
    assert cfg["recovery_policy"] == "mark_failed", f"Expected mark_failed default, got {cfg['recovery_policy']}"
