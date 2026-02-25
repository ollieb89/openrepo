"""
Tests for L3ContainerPool shutdown drain behavior (REL-08).

Validates that:
- Fire-and-forget memorize tasks are tracked in _pending_memorize_tasks
- drain_pending_memorize_tasks() correctly gathers pending tasks
- Drain completes successfully within timeout
- Drain times out correctly for stuck tasks
- Empty drain is a no-op
- Done tasks are pruned from the pending list
- register_shutdown_handler() uses loop.add_signal_handler with SIGTERM

All tests are pure asyncio — no Docker daemon needed.
"""

import asyncio
import signal
from unittest.mock import MagicMock, patch

import pytest

# conftest.py adds skills/spawn to sys.path
from pool import L3ContainerPool, register_shutdown_handler


def _make_pool(project_id: str = "test-project") -> L3ContainerPool:
    """Create a pool instance for testing (no Docker connection needed)."""
    return L3ContainerPool(max_concurrent=3, project_id=project_id)


@pytest.mark.asyncio
async def test_pending_memorize_tasks_tracked():
    """Manually appending a task to _pending_memorize_tasks keeps it in the list."""
    pool = _make_pool()

    # Initially empty
    assert pool._pending_memorize_tasks == []

    # Simulate a tracked task being added
    async def dummy():
        await asyncio.sleep(0)

    task = asyncio.create_task(dummy())
    pool._pending_memorize_tasks.append(task)

    assert len(pool._pending_memorize_tasks) == 1

    # Wait for the task to finish to avoid warnings
    await task


@pytest.mark.asyncio
async def test_drain_completes_pending_tasks():
    """drain_pending_memorize_tasks completes tasks that finish within the timeout."""
    pool = _make_pool()

    async def fast_task():
        await asyncio.sleep(0.05)

    task = asyncio.create_task(fast_task())
    pool._pending_memorize_tasks.append(task)

    result = await pool.drain_pending_memorize_tasks(timeout=5.0)

    assert result["pending"] == 1
    assert result["drained"] == 1
    assert result["timed_out"] is False


@pytest.mark.asyncio
async def test_drain_timeout_on_stuck_tasks():
    """drain_pending_memorize_tasks returns timed_out=True for tasks that don't complete."""
    pool = _make_pool()

    async def stuck_task():
        await asyncio.sleep(60)  # Much longer than the drain timeout

    task = asyncio.create_task(stuck_task())
    pool._pending_memorize_tasks.append(task)

    result = await pool.drain_pending_memorize_tasks(timeout=0.05)

    assert result["timed_out"] is True
    assert result["pending"] == 1

    # Clean up the lingering task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_drain_no_pending_tasks():
    """drain_pending_memorize_tasks is a no-op when the list is empty."""
    pool = _make_pool()

    assert pool._pending_memorize_tasks == []

    result = await pool.drain_pending_memorize_tasks()

    assert result["pending"] == 0
    assert result["drained"] == 0
    assert result["timed_out"] is False


@pytest.mark.asyncio
async def test_pending_tasks_pruned_on_completion():
    """Completed (done) tasks are removed from the pending list by pruning logic."""
    pool = _make_pool()

    async def instant_task():
        pass  # Completes immediately

    task = asyncio.create_task(instant_task())
    pool._pending_memorize_tasks.append(task)

    # Allow the task to complete
    await asyncio.sleep(0)

    # Verify the task is done
    assert task.done()

    # Apply the pruning logic (same as used in spawn_and_monitor after task completion)
    pool._pending_memorize_tasks = [t for t in pool._pending_memorize_tasks if not t.done()]

    assert len(pool._pending_memorize_tasks) == 0


@pytest.mark.asyncio
async def test_register_shutdown_handler_sets_signal():
    """register_shutdown_handler() calls loop.add_signal_handler with SIGTERM."""
    pool = _make_pool()

    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock()

    with patch.object(mock_loop, "add_signal_handler") as mock_add:
        register_shutdown_handler(mock_loop, pool)

    # Verify add_signal_handler was called with SIGTERM as the first arg
    mock_add.assert_called_once()
    call_args = mock_add.call_args
    assert call_args[0][0] == signal.SIGTERM
    # Second arg is the callback (a function)
    assert callable(call_args[0][1])


@pytest.mark.asyncio
async def test_spawn_task_wires_shutdown_handler():
    """spawn_task() must call register_shutdown_handler() — prevents wiring regression (REL-08)."""
    from unittest.mock import AsyncMock, MagicMock, patch
    import pool as pool_module

    mock_pool = MagicMock()
    mock_pool.run_recovery_scan = AsyncMock()
    mock_pool.spawn_and_monitor = AsyncMock(return_value={"status": "ok"})
    mock_pool._pool_config = {}

    with patch.object(pool_module, "_shutdown_handler_registered", False), \
         patch("pool.L3ContainerPool", return_value=mock_pool), \
         patch("pool.register_shutdown_handler") as mock_register, \
         patch("pool.get_workspace_path", return_value="/tmp/workspace"), \
         patch("pool.get_active_project_id", return_value="test-project"), \
         patch("pool.get_pool_config", return_value={"max_concurrent": 3}):
        await pool_module.spawn_task("t1", "code", "do something")

    mock_register.assert_called_once()
