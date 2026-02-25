"""
Project Configuration Resolver

Resolves the active project from openclaw.json and loads its manifest
from projects/<id>/project.json. Provides workspace path, tech stack,
and agent mappings without hardcoding.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .config import (
    get_project_root,
    DEFAULT_POOL_MAX_CONCURRENT,
    DEFAULT_POOL_MODE,
    DEFAULT_POOL_OVERFLOW_POLICY,
    DEFAULT_POOL_QUEUE_TIMEOUT_S,
    DEFAULT_POOL_RECOVERY_POLICY,
)
from .config_validator import validate_project_config, validate_agent_hierarchy, ConfigValidationError  # noqa: F401
from .logging import get_logger

_logger = get_logger("project_config")

_VALID_POOL_MODES = {"shared", "isolated"}
_VALID_OVERFLOW_POLICIES = {"reject", "wait", "priority"}
_VALID_RECOVERY_POLICIES = {"mark_failed", "auto_retry", "manual"}


def load_and_validate_openclaw_config() -> Dict[str, Any]:
    """
    Load openclaw.json and validate agent hierarchy.

    Raises:
        FileNotFoundError: If openclaw.json does not exist.
        ConfigValidationError: If agent hierarchy has invalid reports_to or level constraints.
    """
    root = get_project_root()
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    validate_agent_hierarchy(config, str(config_path))
    return config


def get_active_project_id() -> str:
    """Read the active project ID from openclaw.json or OPENCLAW_PROJECT env var."""
    env_project = os.environ.get("OPENCLAW_PROJECT")
    if env_project:
        return env_project

    config = load_and_validate_openclaw_config()

    project_id = config.get("active_project")
    if not project_id:
        raise ValueError(
            "No active project set. Add '\"active_project\": \"<id>\"' to openclaw.json "
            "or set OPENCLAW_PROJECT env var."
        )
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
    return config


def get_source_directories() -> list:
    """Get the configured source directories from openclaw.json."""
    root = get_project_root()
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)
    return config.get("source_directories", [])


def get_workspace_path(project_id: Optional[str] = None) -> str:
    """Get the workspace path for a project."""
    config = load_project_config(project_id)
    return config["workspace"]


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
        return result
    except Exception as exc:
        _logger.warning(
            "Failed to read memu config -- memorization disabled",
            extra={"error": str(exc)},
        )
        return defaults


class ProjectNotFoundError(Exception):
    """Raised when project manifest does not exist for a given project_id."""
    pass
