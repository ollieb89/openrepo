import os
import httpx
from pathlib import Path

# Lock configuration
LOCK_TIMEOUT = 5  # seconds
LOCK_RETRY_ATTEMPTS = 3

# Polling configuration
POLL_INTERVAL = 1.0  # seconds — legacy single-file mode default; also used as --interval CLI arg default

# Adaptive monitor polling intervals (OBS-05)
# Multi-project tail_state() uses these instead of POLL_INTERVAL.
# Active = any running openclaw-managed L3 containers; idle = none.
# Hardcoded per locked decision — not configurable in openclaw.json.
# Transition lag: up to 30s when swarm goes idle → active (acceptable).
POLL_INTERVAL_ACTIVE = 2.0   # seconds when L3 containers are running
POLL_INTERVAL_IDLE   = 30.0  # seconds when swarm is quiescent

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

# Memory conflict detection — cosine similarity threshold (QUAL-07)
# New memories whose cosine similarity to an existing memory meets or exceeds this
# value are treated as conflicts: the write is skipped and the event is logged.
# The existing memory is kept; the new one is dropped.
#
# Rationale for 0.85 default (no production data available as of v1.5):
#   - text-embedding-3-small (1536-dim) typically scores 0.90–0.99 for near-duplicate
#     text and 0.70–0.85 for related-but-distinct content (OpenAI docs + benchmarks).
#   - 0.85 sits at the boundary of the "related" → "duplicate" transition zone.
#   - Conservative choice: prefer false negatives (missing a conflict) over false
#     positives (incorrectly dropping distinct memories), because missed conflicts
#     are recoverable via the health scan endpoint whereas dropped memories are not.
#   - Operator can tune via openclaw.json memory.conflict_threshold once production
#     data is available.
MEMORY_CONFLICT_THRESHOLD = 0.85


# Agent Registry Schema (Unified)
AGENT_REGISTRY_SCHEMA: dict = {
    "type": "object",
    "required": ["id", "name", "level"],
    "properties": {
        "id": { "type": "string", "pattern": "^[a-zA-Z0-9_]+$" },
        "name": { "type": "string" },
        "level": { "type": "integer", "enum": [1, 2, 3] },
        "reports_to": { "type": ["string", "null"] },
        "subordinates": { "type": "array", "items": { "type": "string" } },
        "model": { "type": "string" },
        "provider": { "type": "string" },
        "orchestration": {
            "type": "object",
            "properties": {
                "role": { "type": "string", "enum": ["strategic", "coordinator", "domain", "executor", "tactical"] },
                "max_concurrent": { "type": "integer", "minimum": 1 },
                "skill_registry": {
                    "anyOf": [
                        { "type": "array", "items": { "type": "string" } },
                        { "type": "object" }
                    ]
                },
                "identity_ref": { "type": "string" },
                "soul_ref": { "type": "string" },
                "projects": { "type": "array", "items": { "type": "string" } },
                "container": {
                    "type": "object",
                    "properties": {
                        "image": { "type": "string" },
                        "mem_limit": { "type": "string" },
                        "cpu_quota": { "type": "integer" }
                    }
                },
                "runtime": {
                    "type": "object",
                    "properties": {
                        "default": { "type": "string" },
                        "supported": { "type": "array", "items": { "type": "string" } }
                    }
                }
            }
        },
        "sandbox": { "type": "object" }
    }
}

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
                "list":     {"type": "array", "items": AGENT_REGISTRY_SCHEMA},
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
        "memory": {
            "type": "object",
            "properties": {
                "memu_api_url":       {"type": "string"},
                "enabled":            {"type": "boolean"},
                "conflict_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
        },
        "autonomy": {
            "type": "object",
            "properties": {
                "enabled":                 {"type": "boolean", "default": False},
                "escalation_threshold":    {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.6},
                "confidence_calculator":   {"type": "string", "enum": ["threshold", "adaptive"], "default": "threshold"},
                "max_retries":             {"type": "integer", "minimum": 0, "default": 1},
                "blocked_timeout_minutes": {"type": "integer", "minimum": 1, "default": 30},
            },
        },
        "plugins": {"type": "object"},
        "skills":  {"type": "object"},
        "topology": {
            "type": "object",
            "properties": {
                "proposal_confidence_warning_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 5,
                },
                "rubric_weights": {
                    "type": "object",
                    "properties": {
                        "complexity":             {"type": "number"},
                        "coordination_overhead":  {"type": "number"},
                        "risk_containment":       {"type": "number"},
                        "time_to_first_output":   {"type": "number"},
                        "cost_estimate":          {"type": "number"},
                        "preference_fit":         {"type": "number"},
                    },
                },
                "auto_approve_l1": {
                    "type": "boolean",
                    "default": False,
                },
                "pushback_threshold": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 8,
                },
            },
        },
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


# ── Env Var Precedence ────────────────────────────────────────────────────────
# The following environment variables override their config-file counterparts.
# Resolution order (first set wins):
#
#   OPENCLAW_ROOT             → project root directory (default: ~/.openclaw)
#   OPENCLAW_PROJECT          → active project ID (default: openclaw.json active_project)
#   OPENCLAW_LOG_LEVEL        → log verbosity: DEBUG|INFO|WARNING|ERROR (default: INFO)
#   OPENCLAW_ACTIVITY_LOG_MAX → max activity log entries per task (default: 100)
#   OPENCLAW_STATE_FILE       → workspace state file path (L3 containers only)
#
# All env var reads are centralised in this module. No component should call
# os.environ directly for OpenClaw configuration values.
# ─────────────────────────────────────────────────────────────────────────────


def _find_project_root() -> Path:
    """Resolve the OpenClaw project root directory.

    Resolution order:
    1. OPENCLAW_ROOT env var — used by Docker containers and CI environments
       to point at the mounted openclaw directory. Auto-creates the directory
       if it does not exist (first-run behaviour when env var is set explicitly).
    2. ~/.openclaw — the conventional home-directory install location.

    Never uses Path(__file__).parent — that resolves to the package install
    location inside site-packages, not the live project root.
    """
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        root = Path(env_root)
        root.mkdir(parents=True, exist_ok=True)
        return root

    # Search for openclaw.json in CWD and its parents (root detection)
    try:
        current = Path.cwd()
        for _ in range(10):  # Reasonable depth limit
            if (current / "openclaw.json").exists():
                return current
            if current.parent == current:
                break
            current = current.parent
    except Exception:
        pass

    return Path.home() / ".openclaw"


def get_project_root() -> Path:
    """Return the OpenClaw project root directory.

    Public API wrapper around _find_project_root(). Used by monitor.py
    for projects directory enumeration and other callers needing the root.

    Resolution order:
    1. OPENCLAW_ROOT env var
    2. Search upward from current working directory for openclaw.json
    3. Default to ~/.openclaw
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


def get_autonomy_config() -> dict:
    """Return the autonomy configuration from openclaw.json with defaults applied.
    
    If the config cannot be loaded, returns safe defaults (autonomy disabled).
    """
    try:
        from openclaw.project_config import load_and_validate_openclaw_config
        config = load_and_validate_openclaw_config()
        autonomy = config.get("autonomy", {})
    except Exception:
        autonomy = {}
        
    return {
        "enabled": autonomy.get("enabled", False),
        "escalation_threshold": autonomy.get("escalation_threshold", 0.6),
        "confidence_calculator": autonomy.get("confidence_calculator", "threshold"),
        "max_retries": autonomy.get("max_retries", 1),
        "blocked_timeout_minutes": autonomy.get("blocked_timeout_minutes", 30),
    }


def get_topology_config() -> dict:
    """Return the topology configuration from openclaw.json with defaults applied.

    Returns safe defaults if the config cannot be loaded.

    Returns:
        Dict with:
        - proposal_confidence_warning_threshold: int (default 5)
        - rubric_weights: dict of 6 dimension -> float weights (sum to 1.0)
        - auto_approve_l1: bool (default False)
        - pushback_threshold: int (default 8)
        - exploration_rate: float (default 0.20) — epsilon for greedy exploration in preference scoring
        - decay_lambda: float (default 0.05) — exponential decay rate for correction weighting (~14-day half-life)
        - pattern_extraction_threshold: int (default 5) — minimum corrections before LLM pattern extraction
    """
    try:
        from openclaw.project_config import load_and_validate_openclaw_config
        config = load_and_validate_openclaw_config()
        topology = config.get("topology", {})
    except Exception:
        topology = {}

    default_weights = {
        "complexity":             0.15,
        "coordination_overhead":  0.15,
        "risk_containment":       0.20,
        "time_to_first_output":   0.20,
        "cost_estimate":          0.10,
        "preference_fit":         0.20,
    }

    return {
        "proposal_confidence_warning_threshold": topology.get(
            "proposal_confidence_warning_threshold", 5
        ),
        "rubric_weights": topology.get("rubric_weights", default_weights),
        "auto_approve_l1": topology.get("auto_approve_l1", False),
        "pushback_threshold": topology.get("pushback_threshold", 8),
        "exploration_rate": topology.get("exploration_rate", 0.20),
        "decay_lambda": topology.get("decay_lambda", 0.05),
        "pattern_extraction_threshold": topology.get("pattern_extraction_threshold", 5),
    }


def get_active_project_env() -> "str | None":
    """Return the OPENCLAW_PROJECT env var value, or None if not set.

    Part of the env var precedence chain:
      OPENCLAW_ROOT → OPENCLAW_PROJECT → OPENCLAW_LOG_LEVEL → OPENCLAW_ACTIVITY_LOG_MAX

    The file-based fallback (openclaw.json active_project) is handled by
    project_config.get_active_project_id(). This function handles the env
    var half only — callers must not read OPENCLAW_PROJECT directly.
    """
    return os.environ.get("OPENCLAW_PROJECT") or None


def get_gateway_config() -> dict:
    """Extract gateway config from openclaw.json."""
    from openclaw.project_config import load_and_validate_openclaw_config
    try:
        config = load_and_validate_openclaw_config()
        return config.get("gateway", {"port": 18789})
    except Exception:
        return {"port": 18789}


async def gateway_healthy(base_url: str = "http://localhost:18789") -> bool:
    """Check if the openclaw gateway is responding."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{base_url}/health")
            return r.status_code == 200
    except httpx.HTTPError:
        return False


def is_bootstrap_mode() -> bool:
    """Return True if running in bootstrap mode (no gateway required).

    Bootstrap mode is activated via OPENCLAW_BOOTSTRAP=1 env var.
    CLI --bootstrap flag is handled by argparse and sets this env var.
    """
    return os.environ.get("OPENCLAW_BOOTSTRAP", "0") == "1"


async def _ensure_gateway_async() -> None:
    """Check gateway health and exit if unavailable (non-bootstrap)."""
    if is_bootstrap_mode():
        import logging
        logging.getLogger("openclaw.config").info("Running in bootstrap mode (no gateway)")
        return

    gw = get_gateway_config()
    base_url = f"http://localhost:{gw.get('port', 18789)}"
    healthy = await gateway_healthy(base_url)
    if not healthy:
        import sys
        print(
            f"FATAL: Gateway not responding at {base_url}. "
            "Start it with: openclaw gateway start",
            file=sys.stderr,
        )
        sys.exit(1)


def ensure_gateway() -> None:
    """Synchronous wrapper for gateway health check at CLI startup.

    Call this at the top of long-running CLI commands (monitor tail,
    tail --events) that require a gateway. Setup commands (project init,
    project list, monitor status) skip this check.

    In bootstrap mode (OPENCLAW_BOOTSTRAP=1), the check is skipped entirely.
    """
    import asyncio
    asyncio.run(_ensure_gateway_async())


def get_agent_registry():
    """Return a loaded AgentRegistry for the current project root.

    Calling this at startup triggers auto-discovery, drift detection,
    orphan warnings, and defaults inheritance. Non-fatal — returns an
    empty registry if project root has no agents/ or openclaw.json.

    This is the canonical way startup code and CLI commands obtain the
    registry. Independent of ensure_gateway() — callers invoke them in
    sequence as needed.

    Returns:
        AgentRegistry instance loaded from the current project root.
    """
    from openclaw.agent_registry import AgentRegistry
    root = get_project_root()
    return AgentRegistry(root)
