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


# JSON Schema for openclaw.json validation (CONF-02)
# Defines required fields, types, and allowed top-level keys.
# Unknown top-level fields generate a WARNING at startup; missing required fields
# or wrong types cause sys.exit(1) before any work is done (CONF-06).
#
# Required (missing = exit): gateway.port (int), agents.list (array)
# Optional: all other fields — sensible defaults apply
OPENCLAW_JSON_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["gateway", "agents"],
    "additionalProperties": False,
    "properties": {
        "meta":               {"type": "object"},
        "active_project":     {"type": "string"},
        "source_directories": {"type": "array", "items": {"type": "string"}},
        "agents": {
            "type": "object",
            "required": ["list"],
            "properties": {
                "list":     {"type": "array"},
                "defaults": {"type": "object"},
            },
        },
        "commands":  {"type": "object"},
        "channels":  {"type": "object"},
        "gateway": {
            "type": "object",
            "required": ["port"],
            "properties": {
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "mode": {"type": "string"},
                "bind": {"type": "string"},
                "auth": {"type": "object"},
            },
        },
        "memory":  {"type": "object"},
        "plugins": {"type": "object"},
    },
}

# JSON Schema for project.json validation (CONF-06 lazy validation)
# Validated when a project is first accessed, not at startup.
# Known top-level fields determined from inspection of all 9 real project.json files.
# Required: workspace (non-empty string), tech_stack (object)
PROJECT_JSON_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["workspace", "tech_stack"],
    "additionalProperties": False,
    "properties": {
        "id":                 {"type": "string"},
        "name":               {"type": "string"},
        "agent_display_name": {"type": "string"},
        "workspace":          {"type": "string", "minLength": 1},
        "tech_stack":         {"type": "object"},
        "agents":             {"type": "object"},
        "l3_overrides":       {"type": "object"},
    },
}


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
