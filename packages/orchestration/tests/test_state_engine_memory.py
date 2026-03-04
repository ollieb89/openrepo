import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path
from openclaw.state_engine import JarvisState


@pytest.fixture
def state_engine(tmp_path):
    state_file = tmp_path / "workspace-state.json"
    engine = JarvisState(state_file)
    engine.lock_retry_attempts = 1
    engine.lock_timeout = 1.0
    return engine


@patch("openclaw.state_engine.get_active_project_id", return_value="test_proj")
@patch("openclaw.state_engine.get_memu_config", return_value={"url": "http://test"})
@patch("openclaw.state_engine._run_memory_injector")
@patch("openclaw.state_engine._run_memory_extractor")
@patch("openclaw.state_engine.event_bridge")
@patch("openclaw.state_engine.asyncio")
def test_state_transition_triggers_memory(
    mock_asyncio, mock_event_bridge, mock_extractor, mock_injector, mock_memu_cfg, mock_proj_id,
    state_engine
):
    # Mock event_bridge.publish to prevent real async execution
    mock_event_bridge.publish = AsyncMock(return_value=None)

    # Mock asyncio so that:
    # - get_running_loop() returns a mock loop (preventing asyncio.run() from being called)
    # - create_task() on the mock loop is a no-op
    mock_loop = MagicMock()
    mock_loop.create_task = MagicMock()
    mock_asyncio.get_running_loop = MagicMock(return_value=mock_loop)
    mock_asyncio.run = MagicMock()

    task_id = "test-123"

    # Create task
    state_engine.create_task(task_id, skill_hint="code")

    # Transition to in_progress (should trigger injector)
    state_engine.update_task(task_id, "in_progress", "Started task")
    mock_injector.assert_called_once()
    args, _ = mock_injector.call_args
    assert args[0] == "test_proj"
    assert args[2] == "code"  # skill_hint determines agent_type

    # Transition to completed (should trigger extractor)
    state_engine.update_task(task_id, "completed", "Finished task")
    mock_extractor.assert_called_once()
    args, _ = mock_extractor.call_args
    assert args[0] == "test_proj"
    assert args[3] == "completed"
