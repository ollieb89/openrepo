"""
Structured JSON logging for all OpenClaw orchestration components.

Provides a shared get_logger() factory that emits single-line JSON objects
to stderr. All fields are consistent across components to enable log aggregation
and structured querying.

Usage:
    from orchestration.logging import get_logger
    logger = get_logger("my_component")
    logger.info("Task started", extra={"task_id": "T-001", "project_id": "pumplai"})
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from .config import LOG_LEVEL

# Standard LogRecord attributes to exclude from extra fields
_STANDARD_ATTRS = frozenset({
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
    'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
    'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
    'processName', 'process', 'message', 'taskName',
})

# Track loggers already configured to avoid duplicate handler attachment
_configured_loggers: set = set()


class StructuredFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects for structured log ingestion.

    Each JSON line contains at minimum:
        - timestamp: ISO 8601 with microseconds (UTC)
        - level: log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - component: the component name passed to get_logger()
        - message: the formatted log message

    Optional fields (if present in record.extra):
        - task_id: L3 task identifier
        - project_id: active project identifier

    Any additional extra keys are included verbatim.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Build the base structured log entry
        entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
                         .isoformat(timespec='microseconds').replace('+00:00', ''),
            "level": record.levelname,
            "component": record.name.removeprefix("openclaw."),
            "message": record.getMessage(),
        }

        # Promote well-known extra fields to top-level
        if hasattr(record, 'task_id'):
            entry['task_id'] = record.task_id
        if hasattr(record, 'project_id'):
            entry['project_id'] = record.project_id

        # Include any additional non-standard extra fields
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and not key.startswith('_') and key not in entry:
                entry[key] = value

        # Append exception info if present
        if record.exc_info:
            entry['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False, default=str)


def get_logger(component: str) -> logging.Logger:
    """
    Return a structured JSON logger for the given component name.

    The logger is named `openclaw.{component}` and emits JSON to stderr.
    Log level is controlled by the OPENCLAW_LOG_LEVEL environment variable
    (defaults to INFO if not set).

    Repeated calls with the same component name return the same logger
    without attaching duplicate handlers.

    Args:
        component: Short identifier for the component (e.g., "state_engine",
                   "snapshot", "spawn_specialist"). Used as the `component`
                   field in every log line.

    Returns:
        A configured logging.Logger instance.
    """
    logger_name = f"openclaw.{component}"

    if logger_name in _configured_loggers:
        return logging.getLogger(logger_name)

    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.propagate = False

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)

    _configured_loggers.add(logger_name)
    return logger
