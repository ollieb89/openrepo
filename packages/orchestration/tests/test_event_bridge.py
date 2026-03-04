"""
Tests for openclaw.events.bridge — envelope mapping, auto-start, idempotency,
end-to-end wiring, socket path derivation, and graceful degradation.

Tests use OPENCLAW_EVENTS_SOCK env var (via monkeypatch) to redirect socket
paths to tmp directories, preventing interference with any running instance.

Run from project root:
    uv run pytest packages/orchestration/tests/test_event_bridge.py -v
"""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

from openclaw.event_bus import clear_handlers, emit, subscribe
from openclaw.events.protocol import EventDomain, EventType, OrchestratorEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_handlers():
    """Reset event_bus handler registry and bridge state before each test."""
    clear_handlers()
    # Reset bridge singleton state so each test gets a fresh bridge
    import openclaw.events.bridge as _bridge_mod
    _bridge_mod._bridge_running = False
    _bridge_mod._loop = None
    yield
    clear_handlers()
    # Cleanup: stop the bridge loop if one was started
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
    # Also reset transport singleton so it picks up new path
    from openclaw.events.transport import event_bridge
    # Ensure any old server is not running (it's a singleton, but since we
    # reset bridge state above it won't be serving)
    yield socket_file


def _wait_for_event(flag: threading.Event, timeout: float = 2.0) -> bool:
    """Wait for a threading.Event. Returns True if set within timeout."""
    return flag.wait(timeout=timeout)


# ---------------------------------------------------------------------------
# Test 1: _envelope_to_event maps task.started correctly
# ---------------------------------------------------------------------------

class TestEnvelopeToEventTaskStarted:
    """_envelope_to_event correctly maps a task.started envelope to OrchestratorEvent."""

    def test_maps_task_started(self):
        from openclaw.events.bridge import _envelope_to_event

        envelope = {
            "event_type": "task.started",
            "project_id": "proj-1",
            "task_id": "t-42",
            "agent_id": "agent-a",
            "status": "in_progress",
        }
        event = _envelope_to_event(envelope)

        assert event is not None
        assert event.type == EventType.TASK_STARTED
        assert event.domain == EventDomain.TASK
        assert event.project_id == "proj-1"
        assert event.task_id == "t-42"
        assert event.agent_id == "agent-a"


# ---------------------------------------------------------------------------
# Test 2: _envelope_to_event returns None for unknown event_type
# ---------------------------------------------------------------------------

class TestEnvelopeToEventUnknown:
    """_envelope_to_event returns None for unknown event_type strings."""

    def test_returns_none_for_unknown_event_type(self):
        from openclaw.events.bridge import _envelope_to_event

        envelope = {
            "event_type": "some.unknown.event",
            "project_id": "proj-1",
        }
        result = _envelope_to_event(envelope)
        assert result is None

    def test_returns_none_for_empty_event_type(self):
        from openclaw.events.bridge import _envelope_to_event

        result = _envelope_to_event({"project_id": "proj-1"})
        assert result is None

    def test_returns_none_for_legacy_phase_event(self):
        """Legacy phase_started events (not in EventType) should be skipped."""
        from openclaw.events.bridge import _envelope_to_event

        result = _envelope_to_event({"event_type": "phase_started", "project_id": "p"})
        assert result is None


# ---------------------------------------------------------------------------
# Test 3: _envelope_to_event extracts top-level fields and remaining as payload
# ---------------------------------------------------------------------------

class TestEnvelopeToEventFieldExtraction:
    """_envelope_to_event extracts project_id, task_id, agent_id as top-level fields."""

    def test_extracts_top_level_fields(self):
        from openclaw.events.bridge import _envelope_to_event

        envelope = {
            "event_type": "task.completed",
            "project_id": "proj-x",
            "task_id": "t-99",
            "agent_id": "agent-b",
            "correlation_id": "corr-1",
            "status": "completed",
            "result": "success",
        }
        event = _envelope_to_event(envelope)

        assert event is not None
        assert event.project_id == "proj-x"
        assert event.task_id == "t-99"
        assert event.agent_id == "agent-b"
        assert event.correlation_id == "corr-1"
        # status and result should be in payload, not top-level
        assert event.payload is not None
        assert event.payload.get("status") == "completed"
        assert event.payload.get("result") == "success"
        # top-level fields should NOT appear in payload
        assert "event_type" not in event.payload
        assert "project_id" not in event.payload
        assert "task_id" not in event.payload

    def test_empty_payload_when_no_extra_keys(self):
        from openclaw.events.bridge import _envelope_to_event

        envelope = {
            "event_type": "memory.stored",
            "project_id": "proj-y",
            "task_id": "t-1",
        }
        event = _envelope_to_event(envelope)
        assert event is not None
        # No extra keys beyond top-level → payload should be None or empty
        assert event.payload is None or event.payload == {}


# ---------------------------------------------------------------------------
# Test 4: ensure_event_bridge starts server and returns True
# ---------------------------------------------------------------------------

class TestEnsureEventBridgeStarts:
    """ensure_event_bridge() starts the server and returns True."""

    def test_starts_server_and_returns_true(self, sock_path):
        from openclaw.events.bridge import ensure_event_bridge

        result = ensure_event_bridge()
        assert result is True

        # Socket file should exist (server is listening)
        time.sleep(0.2)  # Brief wait for server startup
        assert os.path.exists(sock_path), f"Socket file not created at {sock_path}"


# ---------------------------------------------------------------------------
# Test 5: ensure_event_bridge is idempotent
# ---------------------------------------------------------------------------

class TestEnsureEventBridgeIdempotent:
    """ensure_event_bridge() is idempotent — second call returns True without starting another server."""

    def test_idempotent(self, sock_path):
        from openclaw.events.bridge import ensure_event_bridge
        import openclaw.events.bridge as _bridge_mod

        result1 = ensure_event_bridge()
        loop_after_first = _bridge_mod._loop

        result2 = ensure_event_bridge()
        loop_after_second = _bridge_mod._loop

        assert result1 is True
        assert result2 is True
        # Same loop object — no new loop was created
        assert loop_after_first is loop_after_second


# ---------------------------------------------------------------------------
# Test 6: End-to-end wiring — event_bus.emit -> bridge -> socket client
# ---------------------------------------------------------------------------

class TestEndToEndWiring:
    """Emitting via event_bus.emit() after ensure_event_bridge() delivers events to socket clients."""

    def test_event_flows_to_socket_client(self, sock_path):
        from openclaw.events.bridge import ensure_event_bridge

        # Start the bridge
        started = ensure_event_bridge()
        assert started is True

        time.sleep(0.3)  # Wait for server to fully bind

        received: List[str] = []
        done = threading.Event()

        async def _read_one_event():
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_unix_connection(sock_path), timeout=2.0
                )
                line = await asyncio.wait_for(reader.readline(), timeout=3.0)
                received.append(line.decode("utf-8").strip())
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
            except Exception as e:
                received.append(f"ERROR: {e}")
            finally:
                done.set()

        # Start async client in a background thread
        def _run_client():
            asyncio.run(_read_one_event())

        client_thread = threading.Thread(target=_run_client, daemon=True)
        client_thread.start()

        time.sleep(0.2)  # Let client connect

        # Emit a known event
        emit({
            "event_type": EventType.TASK_STARTED.value,
            "project_id": "test-project",
            "task_id": "t-e2e",
        })

        # Wait for the client to receive the event
        assert done.wait(timeout=5.0), "Timed out waiting for event to arrive at socket client"
        assert len(received) == 1, f"Expected 1 event, got: {received}"
        assert "ERROR" not in received[0], f"Client error: {received[0]}"

        # Verify it's a valid OrchestratorEvent JSON
        event = OrchestratorEvent.from_json(received[0])
        assert event.type == EventType.TASK_STARTED
        assert event.project_id == "test-project"
        assert event.task_id == "t-e2e"


# ---------------------------------------------------------------------------
# Test 7: get_socket_path returns OPENCLAW_EVENTS_SOCK when set
# ---------------------------------------------------------------------------

class TestGetSocketPathEnvOverride:
    """get_socket_path() returns OPENCLAW_EVENTS_SOCK value when env var is set."""

    def test_returns_env_var_value(self, monkeypatch, tmp_path):
        custom_path = str(tmp_path / "custom.sock")
        monkeypatch.setenv("OPENCLAW_EVENTS_SOCK", custom_path)

        from openclaw.events.transport import get_socket_path
        assert get_socket_path() == custom_path


# ---------------------------------------------------------------------------
# Test 8: get_socket_path returns $OPENCLAW_ROOT/run/events.sock by default
# ---------------------------------------------------------------------------

class TestGetSocketPathDefault:
    """get_socket_path() returns $OPENCLAW_ROOT/run/events.sock when OPENCLAW_EVENTS_SOCK is not set."""

    def test_returns_root_derived_path(self, monkeypatch, tmp_path):
        # Ensure OPENCLAW_EVENTS_SOCK is absent
        monkeypatch.delenv("OPENCLAW_EVENTS_SOCK", raising=False)
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

        from openclaw.events.transport import get_socket_path
        result = get_socket_path()

        expected = str(tmp_path / "run" / "events.sock")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_returns_home_derived_path_when_no_root(self, monkeypatch):
        monkeypatch.delenv("OPENCLAW_EVENTS_SOCK", raising=False)
        monkeypatch.delenv("OPENCLAW_ROOT", raising=False)

        from openclaw.events.transport import get_socket_path
        result = get_socket_path()

        # Should end with run/events.sock
        assert result.endswith(os.path.join("run", "events.sock")), (
            f"Expected path ending with run/events.sock, got: {result}"
        )


# ---------------------------------------------------------------------------
# Test 9: Regression — full test suite compatibility (handled by running full suite externally)
# Minimal smoke test: known event types all map successfully
# ---------------------------------------------------------------------------

class TestAllEventTypesMap:
    """All EventType values map to valid OrchestratorEvent objects."""

    def test_all_event_types_map(self):
        from openclaw.events.bridge import _envelope_to_event

        for et in EventType:
            envelope = {
                "event_type": et.value,
                "project_id": "regression-test",
                "task_id": "t-1",
            }
            event = _envelope_to_event(envelope)
            assert event is not None, f"Failed to map EventType: {et.value}"
            assert event.type == et
            assert event.domain is not None
