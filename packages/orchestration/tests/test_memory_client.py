"""
Tests for orchestration.memory_client — per-project and per-agent scoping.

All tests use respx to mock httpx transport at the network level.
No live memU service is required.

Run from project root:
    python3 -m pytest tests/test_memory_client.py -v
"""

import sys
import json
import pytest
import httpx
import respx

# Ensure orchestration package is importable when running from project root
sys.path.insert(0, "/home/ollie/.openclaw")

from orchestration.memory_client import MemoryClient, AgentType, MemorizeResult


MEMU_BASE = "http://memu-server:18791"

# ---------------------------------------------------------------------------
# Constructor enforcement tests (sync — no async needed)
# ---------------------------------------------------------------------------


def test_constructor_requires_project_id():
    """MemoryClient cannot be constructed without project_id — must get TypeError."""
    with pytest.raises(TypeError):
        # Only base_url provided; project_id and agent_type are missing
        MemoryClient(MEMU_BASE, agent_type=AgentType.L3_CODE)  # type: ignore[call-arg]


def test_constructor_requires_agent_type():
    """MemoryClient cannot be constructed without agent_type — must get TypeError."""
    with pytest.raises(TypeError):
        # base_url + project_id provided; agent_type is missing
        MemoryClient(MEMU_BASE, "my-project")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# health() tests
# ---------------------------------------------------------------------------


@respx.mock(base_url=MEMU_BASE)
async def test_health_returns_true_when_up(respx_mock):
    """health() returns True when service responds 200 with memu_initialized: true."""
    respx_mock.get("/health").mock(
        return_value=httpx.Response(
            200,
            json={"status": "ok", "service": "openclaw-memory", "memu_initialized": True},
        )
    )
    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L2_PM) as client:
        result = await client.health()
    assert result is True


@respx.mock(base_url=MEMU_BASE)
async def test_health_returns_false_when_down(respx_mock):
    """health() returns False (not an exception) when the service is unreachable."""
    respx_mock.get("/health").mock(side_effect=httpx.ConnectError("connection refused"))
    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L2_PM) as client:
        result = await client.health()
    assert result is False


# ---------------------------------------------------------------------------
# memorize() tests
# ---------------------------------------------------------------------------


@respx.mock(base_url=MEMU_BASE)
async def test_memorize_sends_scoped_payload(respx_mock):
    """memorize() auto-includes project_id and agent_type in the request body."""
    mock_route = respx_mock.post("/memorize").mock(
        return_value=httpx.Response(
            202,
            json={"status": "accepted", "message": "Memorization queued"},
        )
    )

    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L3_CODE) as client:
        result = await client.memorize("task completed")

    # Verify return value
    assert result == MemorizeResult(accepted=True, message="accepted")

    # Verify the request body contained correct scoping fields
    assert mock_route.called, "POST /memorize was not called"
    sent_body = json.loads(mock_route.calls.last.request.content)
    assert sent_body["user"]["user_id"] == "pumplai", "project_id must appear as user.user_id"
    assert sent_body["user"]["agent_type"] == "l3_code", "agent_type must appear as user.agent_type"


@respx.mock(base_url=MEMU_BASE)
async def test_memorize_returns_none_on_failure(respx_mock):
    """memorize() returns None (not an exception) when the service is unreachable."""
    respx_mock.post("/memorize").mock(side_effect=httpx.ConnectError("connection refused"))
    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L3_CODE) as client:
        result = await client.memorize("something important")
    assert result is None


@respx.mock(base_url=MEMU_BASE)
async def test_memorize_includes_category_in_payload(respx_mock):
    """memorize() sends category at the top level of the POST payload when provided."""
    mock_route = respx_mock.post("/memorize").mock(
        return_value=httpx.Response(
            202,
            json={"status": "accepted", "message": "Memorization queued"},
        )
    )

    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L2_PM) as client:
        result = await client.memorize("review decision made", category="review_decision")

    assert result == MemorizeResult(accepted=True, message="accepted")
    assert mock_route.called, "POST /memorize was not called"
    sent_body = json.loads(mock_route.calls.last.request.content)
    assert "category" in sent_body, "category must be present in payload when provided"
    assert sent_body["category"] == "review_decision", (
        f"Expected category='review_decision', got {sent_body.get('category')}"
    )


@respx.mock(base_url=MEMU_BASE)
async def test_memorize_omits_category_when_none(respx_mock):
    """memorize() does not include category in payload when not provided (default None)."""
    mock_route = respx_mock.post("/memorize").mock(
        return_value=httpx.Response(
            202,
            json={"status": "accepted", "message": "Memorization queued"},
        )
    )

    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L3_CODE) as client:
        result = await client.memorize("some content")

    assert result == MemorizeResult(accepted=True, message="accepted")
    assert mock_route.called, "POST /memorize was not called"
    sent_body = json.loads(mock_route.calls.last.request.content)
    assert "category" not in sent_body, (
        f"category must NOT be in payload when not provided, got keys: {list(sent_body.keys())}"
    )


# ---------------------------------------------------------------------------
# retrieve() tests
# ---------------------------------------------------------------------------


@respx.mock(base_url=MEMU_BASE)
async def test_retrieve_sends_project_scoped_where(respx_mock):
    """retrieve() always scopes the where clause to this client's project_id."""
    mock_route = respx_mock.post("/retrieve").mock(
        return_value=httpx.Response(200, json=[])
    )

    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L2_PM) as client:
        result = await client.retrieve("what happened?")

    assert result == []

    # Verify the where clause contains project_id — this is SCOPE-01
    assert mock_route.called, "POST /retrieve was not called"
    sent_body = json.loads(mock_route.calls.last.request.content)
    assert sent_body["where"]["user_id"] == "pumplai", "retrieve must scope where.user_id to project_id"


@respx.mock(base_url=MEMU_BASE)
async def test_retrieve_returns_empty_on_failure(respx_mock):
    """retrieve() returns [] (not an exception) when the service times out."""
    respx_mock.post("/retrieve").mock(side_effect=httpx.TimeoutException("timeout"))
    async with MemoryClient(MEMU_BASE, "pumplai", AgentType.L2_PM) as client:
        result = await client.retrieve("anything")
    assert result == []


# ---------------------------------------------------------------------------
# Project isolation test — KEY SUCCESS CRITERION
# ---------------------------------------------------------------------------


@respx.mock(base_url=MEMU_BASE)
async def test_project_isolation(respx_mock):
    """
    Two-project isolation: memories memorized under project-a are invisible to
    project-b's retrieve because the where clause is always scoped per client.

    This validates SCOPE-01: cross-project data is structurally invisible.
    """
    # Accept all memorize calls from project-a
    respx_mock.post("/memorize").mock(
        return_value=httpx.Response(
            202, json={"status": "accepted", "message": "Memorization queued"}
        )
    )
    # retrieve always returns [] (memU would filter by user_id on a real server)
    retrieve_route = respx_mock.post("/retrieve").mock(
        return_value=httpx.Response(200, json=[])
    )

    # client_a memorizes something
    async with MemoryClient(MEMU_BASE, "project-a", AgentType.L3_CODE) as client_a:
        await client_a.memorize("secret from project A")

    # client_b retrieves — must be scoped to project-b only
    async with MemoryClient(MEMU_BASE, "project-b", AgentType.L3_CODE) as client_b:
        results = await client_b.retrieve("what does project-a know?")

    # No results — isolation holds
    assert results == []

    # The retrieve request was scoped to project-b, not project-a
    assert retrieve_route.called, "POST /retrieve was not called"
    sent_body = json.loads(retrieve_route.calls.last.request.content)
    assert sent_body["where"]["user_id"] == "project-b", (
        "client_b's retrieve must scope to 'project-b', not 'project-a'"
    )


# ---------------------------------------------------------------------------
# Async context manager cleanup test
# ---------------------------------------------------------------------------


async def test_async_context_manager_cleanup():
    """Exiting the context manager closes and nulls the internal httpx client."""
    client = MemoryClient(MEMU_BASE, "pumplai", AgentType.L3_CODE)
    async with client:
        # Inside context — client should be active
        assert client._client is not None

    # After exit — client should be None (cleaned up)
    assert client._client is None
