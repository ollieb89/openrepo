"""Metrics collection for dashboard."""

import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_state_path, DEFAULT_POOL_MAX_CONCURRENT
from .project_config import get_pool_config
from .logging import get_logger

logger = get_logger("metrics")

# ---------------------------------------------------------------------------
# Snapshot throttle state (module-level, per project_id)
# ---------------------------------------------------------------------------

_last_snapshot_times: Dict[str, float] = {}
_SNAPSHOT_THROTTLE_S: float = 0.75


# ---------------------------------------------------------------------------
# collect_metrics_from_state: compute metrics from pre-loaded state dict
# (avoids re-entrant lock deadlock when called from _write_state_locked)
# ---------------------------------------------------------------------------


def collect_metrics_from_state(state_dict: Dict[str, Any], project_id: str = "") -> Dict[str, Any]:
    """Compute orchestration metrics from a pre-loaded state dict.

    This is a pure function that receives state as a parameter — it never
    instantiates JarvisState or calls read_state(), making it safe to call
    from inside _write_state_locked without causing a re-entrant lock deadlock.

    Args:
        state_dict: The full workspace-state dict (already loaded from disk).
        project_id: Optional project identifier. When provided, reads max_concurrent
                    from the project's l3_overrides config via get_pool_config().
                    Defaults to "" (returns DEFAULT_POOL_MAX_CONCURRENT).

    Returns:
        Dict with tasks, pool, memory, autonomy sections — same shape as collect_metrics().
    """
    tasks = state_dict.get("tasks", {})

    task_values = list(tasks.values())
    total = len(task_values)
    pending = sum(1 for t in task_values if t.get("status") == "pending")
    in_progress = sum(1 for t in task_values if t.get("status") == "in_progress")
    completed = sum(1 for t in task_values if t.get("status") == "completed")
    failed = sum(1 for t in task_values if t.get("status") == "failed")

    pool_cfg = get_pool_config(project_id) if project_id else {}
    max_concurrent = pool_cfg.get("max_concurrent", DEFAULT_POOL_MAX_CONCURRENT)

    return {
        "tasks": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "failed": failed,
        },
        "pool": {
            "active_containers": in_progress,
            "max_concurrent": max_concurrent,
        },
        "memory": {
            "healthy": True,
            "last_retrieval": None,
        },
        "autonomy": {
            "active_contexts": 0,
            "escalations_24h": 0,
        },
    }


# ---------------------------------------------------------------------------
# write_python_metrics_snapshot: atomic, throttled, failure-isolated writer
# ---------------------------------------------------------------------------


def write_python_metrics_snapshot(
    project_id: str,
    state_file: Path,
    state_dict: Dict[str, Any],
) -> None:
    """Write python-metrics.json alongside workspace-state.json, atomically.

    Design constraints:
    - NEVER calls JarvisState or read_state() internally — receives state_dict
      as a parameter to avoid re-entrant lock deadlock when called from inside
      _write_state_locked (see state_engine.py).
    - Atomic write: writes to a NamedTemporaryFile in the same directory, then
      calls os.replace() to atomically swap the temp file into place.
    - Throttled: skips write if called again within _SNAPSHOT_THROTTLE_S seconds
      for the same project_id.
    - Failure-isolated: entire body is wrapped in try/except — errors are logged
      as warnings and swallowed, never propagated to the caller.

    Args:
        project_id: Project identifier (used as throttle key).
        state_file: Path to workspace-state.json (used to derive snapshot path
                    and to read source_state_mtime).
        state_dict: Pre-loaded workspace state dict (must not call read_state()
                    to avoid re-entrant lock deadlock).
    """
    try:
        now = time.time()
        last = _last_snapshot_times.get(project_id, 0.0)
        if now - last < _SNAPSHOT_THROTTLE_S:
            return  # Throttle: skip this write

        _last_snapshot_times[project_id] = now

        snapshot_path = state_file.parent / "python-metrics.json"

        # Compute metrics from the pre-loaded state dict (no lock re-entry)
        python_metrics = collect_metrics_from_state(state_dict, project_id)

        try:
            source_state_mtime = state_file.stat().st_mtime
        except OSError:
            source_state_mtime = None

        payload = {
            "python": python_metrics,
            "meta": {
                "generated_at": now,
                "source_state_mtime": source_state_mtime,
            },
        }

        # Atomic write: temp file in same directory → os.replace()
        dir_path = state_file.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=dir_path,
            suffix=".tmp",
            delete=False,
        ) as tmp_f:
            tmp_path = tmp_f.name
            import json
            json.dump(payload, tmp_f, indent=2)
            tmp_f.flush()

        os.replace(tmp_path, str(snapshot_path))

    except Exception as exc:
        logger.warning(
            "python-metrics snapshot write failed (non-fatal)",
            extra={"project_id": project_id, "error": str(exc)},
        )


