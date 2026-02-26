"""
Unit tests for openclaw.event_bus — emit/subscribe/fire-and-forget isolation.

Tests verify the pub/sub contract:
- Subscribing a handler and emitting a matching event calls the handler
- Unsubscribed events are silently ignored
- Handler exceptions do not propagate to the caller
- Multiple handlers for the same event are all called
- clear_handlers() resets state between tests
- Emitting with no subscribers is a no-op

Run from project root:
    uv run pytest packages/orchestration/tests/test_event_bus.py -v
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List

import pytest

from openclaw.event_bus import clear_handlers, emit, subscribe


@pytest.fixture(autouse=True)
def reset_handlers():
    """Reset handler registry before each test to ensure isolation."""
    clear_handlers()
    yield
    clear_handlers()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _wait_for_event(flag: threading.Event, timeout: float = 1.0) -> bool:
    """Wait for a threading.Event with a timeout. Returns True if set, False on timeout."""
    return flag.wait(timeout=timeout)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmitCallsHandler:
    """test_emit_calls_handler — subscribe a handler, emit matching event, verify called."""

    def test_emit_calls_handler(self):
        """Handler is called with the full event envelope when a matching event is emitted."""
        called_flag = threading.Event()
        received_envelopes: List[Dict[str, Any]] = []

        def handler(envelope: Dict[str, Any]) -> None:
            received_envelopes.append(envelope)
            called_flag.set()

        subscribe("phase_started", handler)

        envelope = {
            "event_type": "phase_started",
            "project_id": "pumplai",
            "phase_id": "45",
        }
        emit(envelope)

        assert _wait_for_event(called_flag), "Handler was not called within timeout"
        assert len(received_envelopes) == 1
        assert received_envelopes[0]["event_type"] == "phase_started"
        assert received_envelopes[0]["project_id"] == "pumplai"


class TestEmitIgnoresUnsubscribedEvents:
    """test_emit_ignores_unsubscribed_events — unsubscribed event types are silently ignored."""

    def test_emit_ignores_unsubscribed_events(self):
        """Handler subscribed to phase_started is NOT called when container_completed is emitted."""
        called_flag = threading.Event()

        def handler(envelope: Dict[str, Any]) -> None:
            called_flag.set()

        subscribe("phase_started", handler)

        emit({"event_type": "container_completed", "project_id": "pumplai"})

        # Wait briefly — handler should NOT be called
        called = _wait_for_event(called_flag, timeout=0.2)
        assert not called, "Handler was unexpectedly called for unsubscribed event type"


class TestHandlerExceptionDoesNotPropagate:
    """test_handler_exception_does_not_propagate — exceptions in handlers are swallowed."""

    def test_handler_exception_does_not_propagate(self):
        """emit() completes without raising even when a subscribed handler raises RuntimeError."""
        def broken_handler(envelope: Dict[str, Any]) -> None:
            raise RuntimeError("deliberate handler failure")

        subscribe("phase_completed", broken_handler)

        # Should not raise — exception is logged but not re-raised
        try:
            emit({"event_type": "phase_completed", "project_id": "pumplai"})
        except Exception as exc:
            pytest.fail(f"emit() raised unexpectedly: {exc}")

        # Brief wait to let daemon thread run (and swallow the exception)
        time.sleep(0.1)


class TestMultipleHandlersForSameEvent:
    """test_multiple_handlers_for_same_event — both handlers are called."""

    def test_multiple_handlers_for_same_event(self):
        """Two handlers subscribed to the same event type are both called."""
        flag1 = threading.Event()
        flag2 = threading.Event()

        def handler1(envelope: Dict[str, Any]) -> None:
            flag1.set()

        def handler2(envelope: Dict[str, Any]) -> None:
            flag2.set()

        subscribe("phase_blocked", handler1)
        subscribe("phase_blocked", handler2)

        emit({"event_type": "phase_blocked", "project_id": "smartai", "phase_id": "12"})

        assert _wait_for_event(flag1), "handler1 was not called"
        assert _wait_for_event(flag2), "handler2 was not called"


class TestClearHandlers:
    """test_clear_handlers — after clear, emitting does not call previously subscribed handler."""

    def test_clear_handlers(self):
        """clear_handlers() removes all registered handlers — subsequent emit is a no-op."""
        called_flag = threading.Event()

        def handler(envelope: Dict[str, Any]) -> None:
            called_flag.set()

        subscribe("project_registered", handler)
        clear_handlers()

        emit({"event_type": "project_registered", "project_id": "replyiq"})

        called = _wait_for_event(called_flag, timeout=0.2)
        assert not called, "Handler was called after clear_handlers()"


class TestEmitWithNoHandlers:
    """test_emit_with_no_handlers — emit on empty registry is a no-op (no error)."""

    def test_emit_with_no_handlers(self):
        """Emitting an event when no handlers are registered does not raise."""
        # clear_handlers() is called by the autouse fixture — registry is empty
        try:
            emit({"event_type": "container_failed", "project_id": "finai", "container_id": "l3-abc"})
        except Exception as exc:
            pytest.fail(f"emit() raised on empty registry: {exc}")
