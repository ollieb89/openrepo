import os
from pathlib import Path

# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds

# Cache configuration
CACHE_TTL_SECONDS = 5.0  # Max age before forced re-read (safety net; mtime is primary)

# Logging configuration
LOG_LEVEL = os.environ.get("OPENCLAW_LOG_LEVEL", "INFO").upper()

# Activity log rotation — trim when log exceeds this many entries
ACTIVITY_LOG_MAX_ENTRIES = int(os.environ.get("OPENCLAW_ACTIVITY_LOG_MAX", "100"))

# Pool defaults — single source; pool.py and project_config.py import these
DEFAULT_POOL_MAX_CONCURRENT = 3
DEFAULT_POOL_MODE = "shared"
DEFAULT_POOL_OVERFLOW_POLICY = "wait"
DEFAULT_POOL_QUEUE_TIMEOUT_S = 300
DEFAULT_POOL_RECOVERY_POLICY = "mark_failed"

# Memory injection — hard cap in characters for SOUL memory section
MEMORY_CONTEXT_BUDGET = 2000


def _find_project_root() -> Path:
    """Resolve the OpenClaw project root directory.

    Resolution order:
    1. OPENCLAW_ROOT env var — used by Docker containers and CI environments
       to point at the mounted openclaw directory.
    2. ~/.openclaw — the conventional home-directory install location.

    Never uses Path(__file__).parent — that resolves to the package install
    location inside site-packages, not the live project root.
    """
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        return Path(env_root)
    return Path.home() / ".openclaw"


def get_project_root() -> Path:
    """Return the OpenClaw project root directory.

    Public API wrapper around _find_project_root(). Used by monitor.py
    for projects directory enumeration and other callers needing the root.

    Resolution order: OPENCLAW_ROOT env var → ~/.openclaw
    """
    return _find_project_root()


def get_state_path(project_id: str) -> Path:
    """Return the workspace state file path for the given project.

    Args:
        project_id: The project identifier (required — no active-project fallback).

    Resolution order:
    1. OPENCLAW_STATE_FILE env var — set by container entrypoint.sh to point at
       the mounted workspace state file. Takes priority to align with container usage.
    2. Derived path: <project_root>/workspace/.openclaw/<project_id>/workspace-state.json

    This function is compute-only — it does not validate that the path exists.
    Callers are responsible for validating the project upstream.
    """
    env_state = os.environ.get("OPENCLAW_STATE_FILE")
    if env_state:
        return Path(env_state)
    return _find_project_root() / "workspace" / ".openclaw" / project_id / "workspace-state.json"


def get_snapshot_dir(project_id: str) -> Path:
    """Return the snapshots directory path for the given project.

    Args:
        project_id: The project identifier (required — no active-project fallback).

    Derived path: <project_root>/workspace/.openclaw/<project_id>/snapshots

    This function does not check OPENCLAW_STATE_FILE — snapshot directories
    have no equivalent env var override. It is compute-only and does not
    validate that the path exists.
    """
    return _find_project_root() / "workspace" / ".openclaw" / project_id / "snapshots"
