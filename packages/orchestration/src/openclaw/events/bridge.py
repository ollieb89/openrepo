"""Bus-to-socket bridge: wires event_bus to the Unix socket transport.

This module is the activation layer for the event pipeline:

    event_bus.emit() -> _bridge_handler -> event_bridge.publish() -> Unix socket -> clients

Usage (called once from long-running orchestration commands):

    from openclaw.events.bridge import ensure_event_bridge
    ensure_event_bridge()   # idempotent, safe to call multiple times
"""

import asyncio
import logging
import threading
from typing import Any, Dict, Optional

from .protocol import OrchestratorEvent, EventDomain, EventType
from .transport import event_bridge, get_socket_path

logger = logging.getLogger("openclaw.events.bridge")

# Module-level singleton state
_bridge_running: bool = False
_loop: Optional[asyncio.AbstractEventLoop] = None

# Domain prefix -> EventDomain mapping for envelope-to-event conversion
_DOMAIN_MAP = {
    "task": EventDomain.TASK,
    "agent": EventDomain.AGENT,
    "autonomy": EventDomain.AUTONOMY,
    "memory": EventDomain.MEMORY,
    "pool": EventDomain.POOL,
}

# Build a lookup from string value -> EventType enum for fast mapping
_EVENT_TYPE_MAP: Dict[str, EventType] = {et.value: et for et in EventType}


def _envelope_to_event(envelope: Dict[str, Any]) -> Optional[OrchestratorEvent]:
    """Convert an event_bus envelope dict to an OrchestratorEvent.

    Args:
        envelope: Dict emitted via event_bus.emit(). Must contain at minimum
            ``event_type`` (e.g. "task.started") and ``project_id``.

    Returns:
        OrchestratorEvent on success, None if the event_type is unknown or
        project_id is missing (caller should skip None events).
    """
    event_type_str = envelope.get("event_type", "")
    project_id = envelope.get("project_id", "")

    # Map to EventType enum — return None for unknown types
    event_type = _EVENT_TYPE_MAP.get(event_type_str)
    if event_type is None:
        logger.debug("Unknown event_type in envelope — skipping: %s", event_type_str)
        return None

    # Derive domain from the prefix before the first dot
    prefix = event_type_str.split(".")[0] if "." in event_type_str else ""
    domain = _DOMAIN_MAP.get(prefix)
    if domain is None:
        logger.debug("Cannot determine domain for event_type: %s", event_type_str)
        return None

    # Extract well-known top-level fields; remaining keys go into payload
    _TOP_LEVEL = frozenset(
        {"event_type", "project_id", "task_id", "agent_id", "correlation_id", "timestamp"}
    )
    payload = {k: v for k, v in envelope.items() if k not in _TOP_LEVEL}

    return OrchestratorEvent(
        type=event_type,
        domain=domain,
        project_id=project_id or "unknown",
        task_id=envelope.get("task_id"),
        agent_id=envelope.get("agent_id"),
        correlation_id=envelope.get("correlation_id"),
        timestamp=envelope.get("timestamp"),
        payload=payload if payload else None,
    )


def _bridge_handler(envelope: Dict[str, Any]) -> None:
    """event_bus subscriber that forwards events to the Unix socket transport.

    Invoked in a daemon thread by event_bus. Converts the envelope to an
    OrchestratorEvent and schedules a publish on the bridge's asyncio loop.
    All failures are logged as warnings — never raised (fire-and-forget).
    """
    global _loop
    try:
        event = _envelope_to_event(envelope)
        if event is None:
            return

        if _loop is None or _loop.is_closed():
            logger.debug("Bridge loop not available — event dropped: %s", envelope.get("event_type"))
            return

        asyncio.run_coroutine_threadsafe(event_bridge.publish(event), _loop)
    except Exception:
        logger.warning(
            "Bridge handler failed — event dropped (fire-and-forget)",
            exc_info=True,
            extra={"event_type": envelope.get("event_type")},
        )


def ensure_event_bridge() -> bool:
    """Start the event bridge if not already running.

    Idempotent: safe to call multiple times. The second and subsequent calls
    return True immediately without creating additional threads or sockets.

    The bridge:
    1. Spawns a daemon thread with its own asyncio event loop.
    2. Starts the Unix socket server on that loop.
    3. Registers _bridge_handler for every known EventType in event_bus.

    Returns:
        True  — bridge is running (started now or was already running).
        False — bridge failed to start (orchestration continues with warning).
    """
    global _bridge_running, _loop

    if _bridge_running:
        return True

    try:
        # Create a dedicated event loop for the bridge
        loop = asyncio.new_event_loop()

        # Start daemon thread running the loop
        t = threading.Thread(
            target=loop.run_forever,
            name="openclaw-event-bridge",
            daemon=True,
        )
        t.start()

        # Start the socket server on the bridge loop (wait up to 5s)
        future = asyncio.run_coroutine_threadsafe(event_bridge.start_server(), loop)
        try:
            started = future.result(timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(
                "Event bridge timed out starting socket server — events will not be forwarded"
            )
            loop.call_soon_threadsafe(loop.stop)
            return False

        if started is False:
            # Another process already owns the socket — not a failure for the bridge
            logger.info("Event socket owned by another process — bridge operating in shared mode")

        # Store loop reference for _bridge_handler
        _loop = loop

        # Register handler for every known event type
        from openclaw import event_bus as _event_bus
        for et in EventType:
            _event_bus.subscribe(et.value, _bridge_handler)

        _bridge_running = True
        logger.info("Event bridge started — socket path: %s", get_socket_path())
        return True

    except Exception:
        logger.warning(
            "Event bridge failed to start — events will not be forwarded",
            exc_info=True,
        )
        _bridge_running = False
        return False
