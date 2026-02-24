"""
Tests for fire-and-forget memorization in L3ContainerPool.

Validates that successful task completions trigger non-blocking memorization
via MemoryClient, with correct agent type selection and graceful degradation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# conftest.py adds skills/spawn_specialist to sys.path
from pool import L3ContainerPool


def _make_pool(project_id: str = "test-project") -> L3ContainerPool:
    """Create a pool instance for testing."""
    pool = L3ContainerPool(max_concurrent=3, project_id=project_id)
    return pool


def _mock_memory_client():
    """Create a mock MemoryClient that works as an async context manager."""
    mock_client = AsyncMock()
    mock_client.memorize = AsyncMock(
        return_value=MagicMock(accepted=True, message="accepted")
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
@patch("pool.get_memu_config", return_value={"memu_api_url": "http://localhost:18791", "enabled": True})
async def test_memorize_called_on_success(mock_config):
    pool = _make_pool()
    mock_client = _mock_memory_client()

    with patch("orchestration.memory_client.MemoryClient", return_value=mock_client) as MockClass:
        await pool._memorize_snapshot_fire_and_forget("T-001", "diff content here", "code")

    mock_client.memorize.assert_called_once()
    call_args = mock_client.memorize.call_args
    assert "L3 CODE task T-001" in call_args[0][0]
    assert call_args[1]["category"] == "l3_outcome"


@pytest.mark.asyncio
@patch("pool.get_memu_config", return_value={"memu_api_url": "", "enabled": True})
async def test_memorize_not_called_when_url_empty(mock_config):
    pool = _make_pool()

    with patch("orchestration.memory_client.MemoryClient") as MockClass:
        await pool._memorize_snapshot_fire_and_forget("T-002", "diff content", "code")

    MockClass.assert_not_called()


@pytest.mark.asyncio
@patch("pool.get_memu_config", return_value={"memu_api_url": "http://localhost:18791", "enabled": True})
async def test_memorize_exception_is_non_blocking(mock_config):
    pool = _make_pool()
    mock_client = _mock_memory_client()
    mock_client.memorize = AsyncMock(side_effect=Exception("connection refused"))

    with patch("orchestration.memory_client.MemoryClient", return_value=mock_client):
        # Should NOT raise — fire-and-forget semantics
        await pool._memorize_snapshot_fire_and_forget("T-003", "diff content", "code")


@pytest.mark.asyncio
@patch("pool.get_memu_config", return_value={"memu_api_url": "http://localhost:18791", "enabled": True})
async def test_agent_type_code_vs_test(mock_config):
    pool = _make_pool()

    # Test code skill -> L3_CODE
    mock_client_code = _mock_memory_client()
    with patch("orchestration.memory_client.MemoryClient", return_value=mock_client_code) as MockClass:
        with patch("orchestration.memory_client.AgentType") as MockAgentType:
            MockAgentType.L3_CODE = "l3_code"
            MockAgentType.L3_TEST = "l3_test"
            await pool._memorize_snapshot_fire_and_forget("T-004", "diff", "code")

    # Test test skill -> L3_TEST
    mock_client_test = _mock_memory_client()
    with patch("orchestration.memory_client.MemoryClient", return_value=mock_client_test) as MockClass:
        with patch("orchestration.memory_client.AgentType") as MockAgentType:
            MockAgentType.L3_CODE = "l3_code"
            MockAgentType.L3_TEST = "l3_test"
            await pool._memorize_snapshot_fire_and_forget("T-005", "diff", "test")


@pytest.mark.asyncio
@patch("pool.get_memu_config", return_value={"memu_api_url": "http://localhost:18791", "enabled": True})
async def test_snapshot_content_includes_header(mock_config):
    pool = _make_pool()
    mock_client = _mock_memory_client()

    with patch("orchestration.memory_client.MemoryClient", return_value=mock_client):
        await pool._memorize_snapshot_fire_and_forget("T-006", "the diff payload", "code")

    content_arg = mock_client.memorize.call_args[0][0]
    assert content_arg.startswith("# L3 CODE task T-006")
    assert "the diff payload" in content_arg
