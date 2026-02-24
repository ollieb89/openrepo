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

from .config_validator import validate_project_config, validate_agent_hierarchy, ConfigValidationError  # noqa: F401


def _find_project_root() -> Path:
    """Find the OpenClaw project root (directory containing openclaw.json)."""
    # Check env var first
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        return Path(env_root)

    # Walk up from this file: orchestration/ -> project root
    return Path(__file__).parent.parent


def load_and_validate_openclaw_config() -> Dict[str, Any]:
    """
    Load openclaw.json and validate agent hierarchy.

    Raises:
        FileNotFoundError: If openclaw.json does not exist.
        ConfigValidationError: If agent hierarchy has invalid reports_to or level constraints.
    """
    root = _find_project_root()
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

    root = _find_project_root()
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
    root = _find_project_root()
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


class ProjectNotFoundError(Exception):
    """Raised when project manifest does not exist for a given project_id."""
    pass


def get_state_path(project_id: Optional[str] = None) -> Path:
    """
    Return the per-project state file path.

    Path: <project_root>/workspace/.openclaw/<project_id>/workspace-state.json

    Raises:
        ProjectNotFoundError: If project_id has no manifest in projects/<id>/project.json
        ValueError: If no active project is configured and project_id is None
    """
    if project_id is None:
        project_id = get_active_project_id()

    root = _find_project_root()
    manifest_path = root / "projects" / project_id / "project.json"
    if not manifest_path.exists():
        raise ProjectNotFoundError(
            f"Project '{project_id}' not found. No manifest at {manifest_path}"
        )

    return root / "workspace" / ".openclaw" / project_id / "workspace-state.json"


def get_snapshot_dir(project_id: Optional[str] = None) -> Path:
    """
    Return the per-project snapshot directory path.

    Path: <project_root>/workspace/.openclaw/<project_id>/snapshots/

    Raises:
        ProjectNotFoundError: If project_id has no manifest in projects/<id>/project.json
        ValueError: If no active project is configured and project_id is None
    """
    if project_id is None:
        project_id = get_active_project_id()

    root = _find_project_root()
    manifest_path = root / "projects" / project_id / "project.json"
    if not manifest_path.exists():
        raise ProjectNotFoundError(
            f"Project '{project_id}' not found. No manifest at {manifest_path}"
        )

    return root / "workspace" / ".openclaw" / project_id / "snapshots"
