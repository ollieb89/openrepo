"""
Integration tests for the end-to-end event pipeline:

    event_bus.emit() -> bridge -> Unix socket -> client

These tests verify ordering, payload preservation, and multi-project tagging
without requiring Docker or any external services.

Run from project root:
    uv run pytest packages/orchestration/tests/test_pipeline_integration.py -v
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List

import pytest

from openclaw.event_bus import clear_handlers, emit
from openclaw.events.protocol import EventType


# ---------------------------------------------------------------------------
# Fixtures (mirrors test_event_bridge.py pattern)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_handlers():
    """Reset event_bus handler registry and bridge singleton before/after each test."""
    clear_handlers()
    import openclaw.events.bridge as _bridge_mod
    _bridge_mod._bridge_running = False
    _bridge_mod._loop = None
    yield
    clear_handlers()
    import openclaw.events.bridge as _bridge_mod
    if _bridge_mod._loop is not None and not _bridge_mod._loop.is_closed():
        _bridge_mod._loop.call_soon_threadsafe(_bridge_mod._loop.stop)
    _bridge_mod._bridge_running = False
    _bridge_mod._loop = None


@pytest.fixture
def sock_path(tmp_path, monkeypatch):
    """Provide a unique, isolated socket path for each test."""
    socket_file = str(tmp_path / "test-events.sock")
    monkeypatch.setenv("OPENCLAW_EVENTS_SOCK", socket_file)
    # Ensure transport singleton picks up the new path
    from openclaw.events.transport import event_bridge  # noqa: F401
    yield socket_file


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _collect_events(sock_path: str, n: int, timeout: float = 3.0) -> List[Dict[str, Any]]:
    """Connect to the Unix socket and collect n newline-delimited JSON events.

    Retries the connection until timeout, then reads exactly n lines.
    Returns a list of parsed dicts.
    """
    deadline = time.monotonic() + timeout
    reader = None
    writer = None

    # Retry loop — bridge may not have bound the socket yet
    while time.monotonic() < deadline:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(sock_path),
                timeout=0.5,
            )
            break
        except (OSError, asyncio.TimeoutError):
            await asyncio.sleep(0.05)

    if reader is None:
        raise RuntimeError(f"Could not connect to socket at {sock_path} within {timeout}s")

    results: List[Dict[str, Any]] = []
    try:
        remaining = deadline - time.monotonic()
        for _ in range(n):
            line = await asyncio.wait_for(reader.readline(), timeout=max(remaining, 0.5))
            text = line.decode("utf-8").strip()
            if text:
                results.append(json.loads(text))
            remaining = deadline - time.monotonic()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# Test 1: task lifecycle events arrive in order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_lifecycle_events_flow_in_order(sock_path):
    """TASK_CREATED -> TASK_STARTED -> TASK_OUTPUT -> TASK_COMPLETED arrive in order."""
    from openclaw.events.bridge import ensure_event_bridge

    started = ensure_event_bridge()
    assert started is True

    # Let the bridge start its server
    await asyncio.sleep(0.1)

    # Start collecting 4 events (heartbeats are filtered below)
    collect_task = asyncio.create_task(_collect_events(sock_path, 4, timeout=5.0))

    # Give the client time to connect before emitting
    await asyncio.sleep(0.05)

    project_id = "test-project-lifecycle"
    task_id = "t-lifecycle-1"

    envelope_base = {"project_id": project_id, "task_id": task_id}

    emit({**envelope_base, "event_type": EventType.TASK_CREATED.value})
    await asyncio.sleep(0.02)
    emit({**envelope_base, "event_type": EventType.TASK_STARTED.value})
    await asyncio.sleep(0.02)
    emit({**envelope_base, "event_type": EventType.TASK_OUTPUT.value, "payload": {"line": "running", "stream": "stdout"}})
    await asyncio.sleep(0.02)
    emit({**envelope_base, "event_type": EventType.TASK_COMPLETED.value})

    events = await collect_task

    # Filter out heartbeats (transport sends them independently)
    events = [e for e in events if e.get("type") != "heartbeat"]

    # We need exactly 4 task events — collect more if heartbeats consumed slots
    # (The helper reads exactly n lines so we may need to re-collect; but given
    # the short test window heartbeats are unlikely. Assert on what arrived.)
    assert len(events) == 4, f"Expected 4 events, got {len(events)}: {events}"

    expected_order = [
        EventType.TASK_CREATED.value,
        EventType.TASK_STARTED.value,
        EventType.TASK_OUTPUT.value,
        EventType.TASK_COMPLETED.value,
    ]
    actual_types = [e.get("type") for e in events]
    assert actual_types == expected_order, f"Wrong order: {actual_types}"

    for event in events:
        assert event.get("task_id") == task_id, f"task_id mismatch in {event}"


# ---------------------------------------------------------------------------
# Test 2: TASK_OUTPUT event carries line and stream in payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_output_event_carries_line_and_stream(sock_path):
    """TASK_OUTPUT payload.line and payload.stream are preserved end-to-end."""
    from openclaw.events.bridge import ensure_event_bridge

    started = ensure_event_bridge()
    assert started is True

    await asyncio.sleep(0.1)

    collect_task = asyncio.create_task(_collect_events(sock_path, 1, timeout=4.0))
    await asyncio.sleep(0.05)

    emit({
        "event_type": EventType.TASK_OUTPUT.value,
        "project_id": "test-project-output",
        "task_id": "t-output-2",
        "payload": {"line": "Installing dependencies...", "stream": "stdout"},
    })

    events = await collect_task
    events = [e for e in events if e.get("type") != "heartbeat"]

    # If we got a heartbeat instead of our event, collect one more
    if len(events) == 0:
        extra = await _collect_events(sock_path, 1, timeout=3.0)
        events = [e for e in extra if e.get("type") != "heartbeat"]

    assert len(events) == 1, f"Expected 1 event, got {len(events)}: {events}"
    event = events[0]

    assert event.get("type") == EventType.TASK_OUTPUT.value, f"Wrong type: {event.get('type')}"

    # payload is nested: envelope's "payload" key is not in _TOP_LEVEL,
    # so bridge puts it inside event.payload as {"payload": {...}}
    event_payload = event.get("payload") or {}
    inner = event_payload.get("payload", {})
    assert inner.get("line") == "Installing dependencies...", f"line mismatch: {event_payload}"
    assert inner.get("stream") == "stdout", f"stream mismatch: {event_payload}"


# ---------------------------------------------------------------------------
# Test 3: events from multiple projects are tagged with correct project_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_projects_events_tagged_with_project_id(sock_path):
    """Events from different projects carry the correct project_id."""
    from openclaw.events.bridge import ensure_event_bridge

    started = ensure_event_bridge()
    assert started is True

    await asyncio.sleep(0.1)

    collect_task = asyncio.create_task(_collect_events(sock_path, 2, timeout=5.0))
    await asyncio.sleep(0.05)

    emit({
        "event_type": EventType.TASK_CREATED.value,
        "project_id": "project-alpha",
        "task_id": "t-alpha-1",
    })
    await asyncio.sleep(0.02)
    emit({
        "event_type": EventType.TASK_CREATED.value,
        "project_id": "project-beta",
        "task_id": "t-beta-1",
    })

    events = await collect_task
    events = [e for e in events if e.get("type") != "heartbeat"]

    assert len(events) == 2, f"Expected 2 events, got {len(events)}: {events}"

    project_ids = {e.get("project_id") for e in events}
    assert "project-alpha" in project_ids, f"project-alpha missing from {project_ids}"
    assert "project-beta" in project_ids, f"project-beta missing from {project_ids}"
