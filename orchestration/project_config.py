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


def _find_project_root() -> Path:
    """Find the OpenClaw project root (directory containing openclaw.json)."""
    # Check env var first
    env_root = os.environ.get("OPENCLAW_ROOT")
    if env_root:
        return Path(env_root)

    # Walk up from this file: orchestration/ -> project root
    return Path(__file__).parent.parent


def get_active_project_id() -> str:
    """Read the active project ID from openclaw.json or OPENCLAW_PROJECT env var."""
    env_project = os.environ.get("OPENCLAW_PROJECT")
    if env_project:
        return env_project

    root = _find_project_root()
    config_path = root / "openclaw.json"
    with open(config_path) as f:
        config = json.load(f)

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
            f"Create it with: mkdir -p projects/{project_id} && "
            f"cp projects/pumplai/project.json projects/{project_id}/project.json"
        )

    with open(manifest_path) as f:
        return json.load(f)


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
