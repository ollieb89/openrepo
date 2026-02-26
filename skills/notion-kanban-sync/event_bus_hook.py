"""
Event bus subscription registration for the notion-kanban-sync skill.

This module must be imported before events are emitted. It registers
``notion_sync.handle_event_sync`` as a handler for all relevant OpenClaw
event types via the openclaw.event_bus.subscribe() interface.

Registration is conditional on NOTION_TOKEN being set in the environment.
If the token is absent, or if the event_bus module is unavailable (e.g.
running outside the openclaw package), registrations are silently skipped.

Hook sites in orchestration code should lazily import this module before
each emit() call:

    try:
        import skills.notion_kanban_sync.event_bus_hook  # noqa: F401
    except ImportError:
        pass  # Notion sync skill not installed
"""

import logging
import os
import sys

logger = logging.getLogger("openclaw.notion_hook")

# Only register handlers when the Notion integration token is available.
# This prevents the skill from activating silently in environments where
# Notion is not configured.
if os.environ.get("NOTION_TOKEN"):
    try:
        from openclaw.event_bus import subscribe

        def _handle_event(envelope: dict) -> None:
            """Route any OpenClaw event to the notion_sync event_sync handler.

            Fire-and-forget: called from a daemon thread by event_bus.emit().
            Exceptions are caught and logged — never re-raised.
            """
            try:
                # Ensure the skill directory is on sys.path so notion_sync
                # can be imported without package installation.
                skill_dir = os.path.dirname(os.path.abspath(__file__))
                if skill_dir not in sys.path:
                    sys.path.insert(0, skill_dir)
                from notion_sync import handle_event_sync
                handle_event_sync({"request_type": "event_sync", "event": envelope})
            except Exception:
                logger.exception(
                    "Notion sync handler raised an exception for event_type=%s",
                    envelope.get("event_type"),
                )

        _EVENT_TYPES = (
            "phase_started",
            "phase_completed",
            "phase_blocked",
            "container_completed",
            "container_failed",
            "project_registered",
            "project_removed",
        )

        for _evt in _EVENT_TYPES:
            subscribe(_evt, _handle_event)

        logger.info(
            "Notion sync handlers registered for %d event types: %s",
            len(_EVENT_TYPES),
            ", ".join(_EVENT_TYPES),
        )

    except ImportError:
        logger.debug(
            "openclaw.event_bus not available — Notion event hooks not registered. "
            "This is expected when the skill runs outside the openclaw package context."
        )
else:
    logger.debug(
        "NOTION_TOKEN not set in environment — Notion sync disabled. "
        "Set NOTION_TOKEN to enable automatic Notion synchronization."
    )
