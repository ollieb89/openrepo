"""
L3 Specialist Container Spawning Module

Implements the spawn_specialist skill for L2 (PumplAI_PM) to spawn isolated
L3 containers with Docker Python SDK. Handles security isolation, GPU passthrough,
and state synchronization.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add orchestration to path for state engine import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import docker
from docker.types import DeviceRequest
from orchestration.state_engine import JarvisState


def load_l3_config() -> Dict[str, Any]:
    """Load L3 specialist configuration from config.json."""
    config_path = Path(__file__).parent.parent.parent / "agents" / "l3_specialist" / "config.json"
    with open(config_path) as f:
        return json.load(f)


def get_skill_timeout(skill_hint: str) -> int:
    """Get timeout in seconds for a skill from the L3 config."""
    config = load_l3_config()
    skill_registry = config.get("skill_registry", {})
    skill_config = skill_registry.get(skill_hint, {})
    return skill_config.get("timeout_seconds", 600)


def spawn_l3_specialist(
    task_id: str,
    skill_hint: str,
    task_description: str,
    workspace_path: str,
    requires_gpu: bool = False,
    cli_runtime: str = "claude-code",
) -> Any:
    """
    Spawn an L3 specialist container for task execution.

    Args:
        task_id: Unique task identifier
        skill_hint: Skill to use (code or test)
        task_description: Description of the task
        workspace_path: Path to the workspace directory on host
        requires_gpu: Whether GPU passthrough is required
        cli_runtime: CLI runtime to use (claude-code, codex, gemini-cli)

    Returns:
        Docker container object

    Raises:
        docker.errors.APIError: If Docker daemon is not running
        docker.errors.ImageNotFound: If the L3 image is not built
    """
    client = docker.from_env()

    # Verify Docker daemon is running
    try:
        client.ping()
    except Exception as e:
        raise RuntimeError(
            f"Docker daemon not running: {e}. Please start Docker and try again."
        ) from e

    # Check if L3 image exists
    try:
        client.images.get("openclaw-l3-specialist:latest")
    except docker.errors.ImageNotFound:
        raise RuntimeError(
            "L3 specialist image not found. Build with:\n"
            "  docker build -t openclaw-l3-specialist:latest docker/l3-specialist/"
        ) from None

    # Create staging branch name
    staging_branch = f"l3/task-{task_id}"

    # Build container name
    container_name = f"openclaw-l3-{task_id}"

    # Get project root for orchestration mount
    project_root = Path(__file__).parent.parent.parent

    # Build container configuration
    container_config = {
        "image": "openclaw-l3-specialist:latest",
        "name": container_name,
        "detach": True,

        # Volume mounts
        "volumes": {
            workspace_path: {"bind": "/workspace", "mode": "rw"},
            str(project_root / "orchestration"): {"bind": "/orchestration", "mode": "ro"},
            str(project_root / "workspace" / ".openclaw"): {"bind": "/workspace/.openclaw", "mode": "rw"},
        },

        # Environment variables
        "environment": {
            "TASK_ID": task_id,
            "SKILL_HINT": skill_hint,
            "STAGING_BRANCH": staging_branch,
            "CLI_RUNTIME": cli_runtime,
            "TASK_DESCRIPTION": task_description,
        },

        # Security isolation (HIE-04 requirements)
        "security_opt": ["no-new-privileges"],
        "cap_drop": ["ALL"],

        # Resource limits
        "mem_limit": "4g",
        "cpu_quota": 100000,  # 1 CPU

        # Restart policy (L2 handles retries, not Docker)
        "restart_policy": {"Name": "no"},

        # Labels for tracking
        "labels": {
            "openclaw.tier": "l3",
            "openclaw.task_id": task_id,
            "openclaw.spawned_by": "pumplai_pm",
            "openclaw.skill": skill_hint,
        },

        # User matching (match host UID to avoid permission errors)
        "user": f"{os.getuid()}:{os.getgid()}",
    }

    # Add GPU support if required
    if requires_gpu:
        container_config["device_requests"] = [
            DeviceRequest(
                count=-1,  # All GPUs
                capabilities=[["gpu"]],
                driver="nvidia"
            )
        ]

    # Create task entry in state.json before spawning
    state_file = project_root / "workspace" / ".openclaw" / "workspace-state.json"
    jarvis = JarvisState(state_file)
    jarvis.create_task(
        task_id=task_id,
        skill_hint=skill_hint,
        metadata={
            "cli_runtime": cli_runtime,
            "requires_gpu": requires_gpu,
            "container_name": container_name,
            "staging_branch": staging_branch,
        }
    )

    # Check for existing container with same name and remove if found
    try:
        old_container = client.containers.get(container_name)
        print(f"[spawn] Removing existing container: {container_name}")
        old_container.remove(force=True)
    except docker.errors.NotFound:
        pass  # Container doesn't exist, which is fine

    # Spawn container
    print(f"[spawn] Spawning L3 container: {container_name}")
    print(f"[spawn] Task: {task_id}, Skill: {skill_hint}, GPU: {requires_gpu}")
    
    container = client.containers.run(**container_config)
    return container


def cleanup_container(container) -> None:
    """
    Force remove a container, handling already-removed case gracefully.

    Args:
        container: Docker container object
    """
    try:
        container.remove(force=True)
        print(f"[cleanup] Removed container: {container.name}")
    except docker.errors.NotFound:
        print(f"[cleanup] Container already removed: {container.name}")
    except Exception as e:
        print(f"[cleanup] Error removing container: {e}")


def get_container_logs(container, tail: int = 100) -> str:
    """
    Get last N log lines from container.

    Args:
        container: Docker container object
        tail: Number of lines to retrieve (default 100)

    Returns:
        Log output as string
    """
    try:
        logs = container.logs(tail=tail, stdout=True, stderr=True)
        return logs.decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error retrieving logs: {e}"


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Spawn L3 specialist container")
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument("skill_hint", choices=["code", "test"], help="Skill to use")
    parser.add_argument("task_description", help="Task description")
    parser.add_argument("--workspace", default="/home/ollie/.openclaw/workspace", help="Workspace path")
    parser.add_argument("--gpu", action="store_true", help="Enable GPU passthrough")
    parser.add_argument("--runtime", default="claude-code", help="CLI runtime")
    
    args = parser.parse_args()

    container = spawn_l3_specialist(
        task_id=args.task_id,
        skill_hint=args.skill_hint,
        task_description=args.task_description,
        workspace_path=args.workspace,
        requires_gpu=args.gpu,
        cli_runtime=args.runtime,
    )
    
    print(f"Container spawned: {container.id}")
