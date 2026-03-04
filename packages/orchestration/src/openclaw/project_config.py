"""
Project Configuration Resolver

Resolves the active project from openclaw.json and loads its manifest
from projects/<id>/project.json. Provides workspace path, tech stack,
and agent mappings without hardcoding.
"""

import json
import os
import sys as _sys
from pathlib import Path
from typing import Any, Dict, Optional

from .config import (
    get_project_root,
    get_active_project_env,
    DEFAULT_POOL_MAX_CONCURRENT,
    DEFAULT_POOL_MODE,
    DEFAULT_POOL_OVERFLOW_POLICY,
    DEFAULT_POOL_QUEUE_TIMEOUT_S,
    DEFAULT_POOL_RECOVERY_POLICY,
)
from .config_validator import (  # noqa: F401
    validate_project_config,
    validate_project_config_schema,
    validate_openclaw_config,
    validate_agent_hierarchy,
    ConfigValidationError,
)
from .logging import get_logger

_logger = get_logger("project_config")


def _is_tty() -> bool:
    """Return True if stderr is an interactive TTY."""
    return hasattr(_sys.stderr, "isatty") and _sys.stderr.isatty()


def _emit_validation_results(
    fatal: list, warnings: list, config_path: str
) -> None:
    """
    Print validation warnings and errors to stderr, then exit if any fatal errors.

    Called before logging is configured — output goes directly to stderr.
    TTY: coloured labels. Non-TTY: plain text.
    """
    red    = "\033[91m" if _is_tty() else ""
    yellow = "\033[93m" if _is_tty() else ""
    reset  = "\033[0m"  if _is_tty() else ""

    for w in warnings:
        print(f"{yellow}WARNING{reset}: {w}", file=_sys.stderr, flush=True)
    for e in fatal:
        print(f"{red}ERROR{reset}: {e}", file=_sys.stderr, flush=True)
    if fatal:
        _sys.exit(1)


_VALID_POOL_MODES = {"shared", "isolated"}
_VALID_OVERFLOW_POLICIES = {"reject", "wait", "priority"}
_VALID_RECOVERY_POLICIES = {"mark_failed", "auto_retry", "manual"}


def load_and_validate_openclaw_config() -> Dict[str, Any]:
    """
    Load openclaw.json, validate schema, and validate agent hierarchy.

    Schema validation (CONF-02, CONF-06):
    - Unknown top-level fields -> WARNING to stderr, continue
    - Missing required fields or wrong types -> ERROR to stderr, sys.exit(1)

    Agent hierarchy validation (REL-02/REL-03 — existing):
    - Raises ConfigValidationError on bad reports_to chains

    Raises:
        FileNotFoundError: If openclaw.json does not exist.
        ConfigValidationError: If agent hierarchy has invalid reports_to or level constraints.
    """
    root = get_project_root()
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    # Schema validation — CONF-02, CONF-06 (must run before agent hierarchy)
    fatal, warnings = validate_openclaw_config(config, str(config_path))
    _emit_validation_results(fatal, warnings, str(config_path))
    # Agent hierarchy validation — existing behaviour preserved
    validate_agent_hierarchy(config, str(config_path))
    return config


def get_active_project_id() -> str:
    """Read the active project ID from OPENCLAW_PROJECT env var or openclaw.json."""
    env_project = get_active_project_env()  # routes through config.py
    if env_project:
        return env_project

    config = load_and_validate_openclaw_config()

    project_id = config.get("active_project")
    if not project_id:
        return ""
    return project_id


def load_project_config(project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Load a project manifest from projects/<id>/project.json.

    Args:
        project_id: Explicit project ID. If None, reads from active_project.

    Returns:
        Parsed project.json dict.

    Raises:
        FileNotFoundError: If the project manifest doesn't exist.
        ValueError: If no active project is configured.
    """
    if project_id is None:
        project_id = get_active_project_id()

    root = get_project_root()
    manifest_path = root / "projects" / project_id / "project.json"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Project manifest not found: {manifest_path}\n"
            f"Create it with: python3 orchestration/project_cli.py init --id {project_id}"
        )

    with open(manifest_path) as f:
        config = json.load(f)

    validate_project_config(config, str(manifest_path))
    # Schema pass: detects unknown fields as warnings, validates types (CONF-06)
    validate_project_config_schema(config, str(manifest_path))
    return config


def get_source_directories() -> list:
    """Get the configured source directories from openclaw.json."""
    root = get_project_root()
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    return config.get("source_directories", [])


def get_workspace_path(project_id: Optional[str] = None) -> str:
    """Get the workspace path for a project, expanding ~ and env vars."""
    config = load_project_config(project_id)
    raw = config["workspace"]
    return os.path.expandvars(os.path.expanduser(raw))


def get_tech_stack(project_id: Optional[str] = None) -> Dict[str, str]:
    """Get the tech stack for a project."""
    config = load_project_config(project_id)
    return config.get("tech_stack", {})


def get_agent_mapping(project_id: Optional[str] = None) -> Dict[str, str]:
    """Get the agent role -> ID mapping for a project."""
    config = load_project_config(project_id)
    return config.get("agents", {})


def get_pool_config(project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and validate pool configuration from a project's l3_overrides.

    Reads project.json fresh on every call (supports hot-reload when project.json
    is modified between spawn calls).

    Returns a dict with all pool keys resolved to safe defaults:
        {
            "max_concurrent": int,       # default 3
            "pool_mode": str,            # default "shared" — values: "shared", "isolated"
            "overflow_policy": str,      # default "wait" — values: "reject", "wait", "priority"
            "queue_timeout_s": int,      # default 300
            "recovery_policy": str,      # default "mark_failed" — values: "mark_failed", "auto_retry", "manual"
        }

    Invalid values produce a warning log and fall back to defaults.
    This function NEVER raises on bad pool config — callers should always
    receive a usable config dict.

    Args:
        project_id: Explicit project ID. If None, uses the active project.

    Returns:
        Dict with resolved pool configuration.
    """
    defaults = {
        "max_concurrent": DEFAULT_POOL_MAX_CONCURRENT,
        "pool_mode": DEFAULT_POOL_MODE,
        "overflow_policy": DEFAULT_POOL_OVERFLOW_POLICY,
        "queue_timeout_s": DEFAULT_POOL_QUEUE_TIMEOUT_S,
        "recovery_policy": DEFAULT_POOL_RECOVERY_POLICY,
    }

    try:
        config = load_project_config(project_id)
    except Exception as exc:
        _logger.warning(
            "Failed to load project config for pool — using defaults",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return defaults

    overrides = config.get("l3_overrides", {})
    result = defaults.copy()

    # max_concurrent: must be a positive int
    if "max_concurrent" in overrides:
        val = overrides["max_concurrent"]
        if isinstance(val, int) and val > 0:
            result["max_concurrent"] = val
        else:
            _logger.warning(
                "Invalid pool config: max_concurrent must be a positive integer — using default",
                extra={
                    "project_id": project_id,
                    "got": val,
                    "default": defaults["max_concurrent"],
                },
            )

    # pool_mode: must be one of the known modes
    if "pool_mode" in overrides:
        val = overrides["pool_mode"]
        if isinstance(val, str) and val in _VALID_POOL_MODES:
            result["pool_mode"] = val
        else:
            _logger.warning(
                "Invalid pool config: pool_mode must be one of %s — using default",
                sorted(_VALID_POOL_MODES),
                extra={
                    "project_id": project_id,
                    "got": val,
                    "default": defaults["pool_mode"],
                },
            )

    # overflow_policy: must be one of the known policies
    if "overflow_policy" in overrides:
        val = overrides["overflow_policy"]
        if isinstance(val, str) and val in _VALID_OVERFLOW_POLICIES:
            result["overflow_policy"] = val
        else:
            _logger.warning(
                "Invalid pool config: overflow_policy must be one of %s — using default",
                sorted(_VALID_OVERFLOW_POLICIES),
                extra={
                    "project_id": project_id,
                    "got": val,
                    "default": defaults["overflow_policy"],
                },
            )

    # queue_timeout_s: must be a positive int
    if "queue_timeout_s" in overrides:
        val = overrides["queue_timeout_s"]
        if isinstance(val, int) and val > 0:
            result["queue_timeout_s"] = val
        else:
            _logger.warning(
                "Invalid pool config: queue_timeout_s must be a positive integer — using default",
                extra={
                    "project_id": project_id,
                    "got": val,
                    "default": defaults["queue_timeout_s"],
                },
            )

    # recovery_policy: must be one of the known policies
    if "recovery_policy" in overrides:
        val = overrides["recovery_policy"]
        if isinstance(val, str) and val in _VALID_RECOVERY_POLICIES:
            result["recovery_policy"] = val
        else:
            _logger.warning(
                "Invalid pool config: recovery_policy must be one of %s — using default",
                sorted(_VALID_RECOVERY_POLICIES),
                extra={
                    "project_id": project_id,
                    "got": val,
                    "default": defaults["recovery_policy"],
                },
            )

    return result


def get_memu_config() -> Dict[str, Any]:
    """Read memory service config from openclaw.json.

    Returns:
        Dict with 'memu_api_url' and 'enabled' keys. Returns defaults on any error.
        Never raises -- callers receive a usable (possibly empty) config.
    """
    defaults = {"memu_api_url": "", "enabled": True}
    try:
        root = get_project_root()
        config_path = root / "openclaw.json"
        with open(config_path) as f:
            cfg = json.load(f)
        memory_cfg = cfg.get("memory", {})
        result = defaults.copy()
        if "memu_api_url" in memory_cfg:
            result["memu_api_url"] = memory_cfg["memu_api_url"]
        if "enabled" in memory_cfg:
            result["enabled"] = bool(memory_cfg["enabled"])
        if "conflict_threshold" in memory_cfg:
            result["conflict_threshold"] = float(memory_cfg["conflict_threshold"])
        return result
    except Exception as exc:
        _logger.warning(
            "Failed to read memu config -- memorization disabled",
            extra={"error": str(exc)},
        )
        return defaults


def get_conflict_threshold() -> float:
    """Return the cosine similarity conflict detection threshold.

    Resolution order:
    1. openclaw.json memory.conflict_threshold (operator override)
    2. config.MEMORY_CONFLICT_THRESHOLD (default: 0.85)

    Never raises — returns the config.py default on any read/parse error.
    """
    try:
        cfg = get_memu_config()
        override = cfg.get("conflict_threshold")
        if override is not None:
            return float(override)
    except Exception:
        pass
    from openclaw.config import MEMORY_CONFLICT_THRESHOLD
    return MEMORY_CONFLICT_THRESHOLD


class ProjectNotFoundError(Exception):
    """Raised when project manifest does not exist for a given project_id."""
    pass


# Valid values for autonomy config
_VALID_CONFIDENCE_CALCULATORS = {"threshold", "adaptive"}

# Autonomy config defaults
DEFAULT_ESCALATION_THRESHOLD = 0.6
DEFAULT_CONFIDENCE_CALCULATOR = "threshold"
DEFAULT_MAX_RETRIES = 1
DEFAULT_BLOCKED_TIMEOUT_MINUTES = 30


def get_autonomy_config() -> Dict[str, Any]:
    """
    Read autonomy configuration from openclaw.json.

    Returns:
        Dict with autonomy configuration. Returns defaults on any error.
        Never raises -- callers receive a usable config.

    Resolution order:
    1. openclaw.json autonomy.* settings
    2. OPENCLAW_ESCALATION_THRESHOLD env var (overrides escalation_threshold)
    3. Module defaults (defined above)
    """
    defaults = {
        "escalation_threshold": DEFAULT_ESCALATION_THRESHOLD,
        "confidence_calculator": DEFAULT_CONFIDENCE_CALCULATOR,
        "max_retries": DEFAULT_MAX_RETRIES,
        "blocked_timeout_minutes": DEFAULT_BLOCKED_TIMEOUT_MINUTES,
    }

    try:
        root = get_project_root()
        config_path = root / "openclaw.json"
        with open(config_path) as f:
            cfg = json.load(f)

        autonomy_cfg = cfg.get("autonomy", {})
        result = defaults.copy()

        # escalation_threshold: float 0.0-1.0
        if "escalation_threshold" in autonomy_cfg:
            val = autonomy_cfg["escalation_threshold"]
            if isinstance(val, (int, float)) and 0.0 <= val <= 1.0:
                result["escalation_threshold"] = float(val)
            else:
                _logger.warning(
                    "Invalid autonomy config: escalation_threshold must be 0.0-1.0 -- using default",
                    extra={"got": val, "default": defaults["escalation_threshold"]},
                )

        # confidence_calculator: enum "threshold" or "adaptive"
        if "confidence_calculator" in autonomy_cfg:
            val = autonomy_cfg["confidence_calculator"]
            if isinstance(val, str) and val in _VALID_CONFIDENCE_CALCULATORS:
                result["confidence_calculator"] = val
            else:
                _logger.warning(
                    "Invalid autonomy config: confidence_calculator must be one of %s -- using default",
                    sorted(_VALID_CONFIDENCE_CALCULATORS),
                    extra={"got": val, "default": defaults["confidence_calculator"]},
                )

        # max_retries: non-negative int
        if "max_retries" in autonomy_cfg:
            val = autonomy_cfg["max_retries"]
            if isinstance(val, int) and val >= 0:
                result["max_retries"] = val
            else:
                _logger.warning(
                    "Invalid autonomy config: max_retries must be >= 0 -- using default",
                    extra={"got": val, "default": defaults["max_retries"]},
                )

        # blocked_timeout_minutes: positive int
        if "blocked_timeout_minutes" in autonomy_cfg:
            val = autonomy_cfg["blocked_timeout_minutes"]
            if isinstance(val, int) and val >= 1:
                result["blocked_timeout_minutes"] = val
            else:
                _logger.warning(
                    "Invalid autonomy config: blocked_timeout_minutes must be >= 1 -- using default",
                    extra={"got": val, "default": defaults["blocked_timeout_minutes"]},
                )

        # Env var override for escalation_threshold
        env_threshold = os.environ.get("OPENCLAW_ESCALATION_THRESHOLD")
        if env_threshold is not None:
            try:
                val = float(env_threshold)
                if 0.0 <= val <= 1.0:
                    result["escalation_threshold"] = val
                else:
                    _logger.warning(
                        "Invalid OPENCLAW_ESCALATION_THRESHOLD env var: must be 0.0-1.0 -- using config/default",
                        extra={"got": env_threshold},
                    )
            except ValueError:
                _logger.warning(
                    "Invalid OPENCLAW_ESCALATION_THRESHOLD env var: not a number -- using config/default",
                    extra={"got": env_threshold},
                )

        return result
    except Exception as exc:
        _logger.warning(
            "Failed to read autonomy config -- using defaults",
            extra={"error": str(exc)},
        )
        return defaults


def get_escalation_threshold() -> float:
    """
    Return the escalation threshold for autonomy decisions.

    Resolution order:
    1. OPENCLAW_ESCALATION_THRESHOLD env var
    2. openclaw.json autonomy.escalation_threshold
    3. Module default (0.6)

    Never raises -- returns the default on any read/parse error.
    """
    cfg = get_autonomy_config()
    return cfg.get("escalation_threshold", DEFAULT_ESCALATION_THRESHOLD)


def get_confidence_calculator_type() -> str:
    """
    Return the confidence calculator type.

    Resolution order:
    1. openclaw.json autonomy.confidence_calculator
    2. Module default ("threshold")

    Returns:
        str: Either "threshold" or "adaptive"

    Never raises -- returns the default on any read/parse error.
    """
    cfg = get_autonomy_config()
    return cfg.get("confidence_calculator", DEFAULT_CONFIDENCE_CALCULATOR)
