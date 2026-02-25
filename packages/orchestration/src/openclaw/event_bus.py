"""
OpenClaw Event Bus — fire-and-forget pub/sub for orchestration events.

Handlers are invoked in daemon threads (one per handler per emit call).
Exceptions in handlers are logged but never re-raised to the caller.

Zero imports from the ``openclaw`` package at module level — this avoids
circular import issues since state_engine, pool, and project_cli all import
from openclaw and may also want to emit events.
"""

import logging
import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List

logger = logging.getLogger("openclaw.event_bus")

# Module-level handler registry: event_type -> list of callables
_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)


def subscribe(event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
    """
    Register a handler for the given event type.

    The handler will be called with the full event envelope dict every time
    ``emit()`` is called with a matching ``event_type``.

    Args:
        event_type: One of the canonical event type strings (e.g. "phase_started").
        handler: Callable accepting a single dict argument (the event envelope).
    """
    _handlers[event_type].append(handler)


def emit(envelope: Dict[str, Any]) -> None:
    """
    Emit an event envelope to all registered handlers for its event_type.

    Handlers are invoked in separate daemon threads (fire-and-forget). This
    method returns immediately — callers are never blocked by handler execution.

    Args:
        envelope: Event envelope dict containing at minimum ``event_type``.
    """
    event_type = envelope.get("event_type", "")
    if not event_type:
        logger.debug("emit() called with no event_type — skipping")
        return

    handlers = list(_handlers.get(event_type, []))
    for handler in handlers:
        t = threading.Thread(
            target=_call_handler,
            args=(handler, envelope),
            daemon=True,
        )
        t.start()


def _call_handler(handler: Callable[[Dict[str, Any]], None], envelope: Dict[str, Any]) -> None:
    """
    Invoke a single handler, catching and logging any exception.

    Never re-raises — handler failures must not affect the caller.

    Args:
        handler: The registered handler callable.
        envelope: Event envelope to pass to the handler.
    """
    try:
        handler(envelope)
    except Exception:
        logger.exception(
            "Event handler raised an exception (non-blocking)",
            extra={"event_type": envelope.get("event_type"), "handler": repr(handler)},
        )


def clear_handlers() -> None:
    """
    Reset the handler registry to empty.

    Intended for use in tests to isolate handler state between test cases.
    Do NOT call in production code.
    """
    global _handlers
    _handlers = defaultdict(list)
