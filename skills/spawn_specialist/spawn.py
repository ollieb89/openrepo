"""
L3 Specialist Container Spawning Module

Implements the spawn_specialist skill for L2 to spawn isolated
L3 containers with Docker Python SDK. Handles security isolation, GPU passthrough,
and state synchronization. Project-aware — resolves project identity at spawn time.
"""

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

# Add orchestration to path for state engine import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import docker
from docker.types import DeviceRequest
from orchestration.state_engine import JarvisState
from orchestration.project_config import (
    get_active_project_id,
    load_project_config,
    get_workspace_path,
    get_agent_mapping,
    get_state_path,
    get_memu_config,
)
from orchestration.snapshot import _detect_default_branch
from orchestration.logging import get_logger

logger = get_logger("spawn")

_PROJECT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9-]{1,20}$')

# Module-level Docker client singleton for connection reuse across spawns
_docker_client: Optional[docker.DockerClient] = None

# Memory retrieval + SOUL injection constants
MEMORY_CONTEXT_BUDGET = 2000  # Hard cap in characters for injected memory section
_RETRIEVE_TIMEOUT = httpx.Timeout(3.0, connect=2.0)  # Match memory_client.py pattern
_RETRIEVE_LIMIT = 10  # Max items to request from memU
SOUL_CONTAINER_PATH = "/run/openclaw/soul.md"  # Container-side path for augmented SOUL

_LOCALHOST_PATTERN = re.compile(r'(https?://)(?:localhost|127\.0\.0\.1)((?::\d+)?(?:/.*)?$)')


def _rewrite_memu_url_for_container(url: str, dns_hostname: str = "openclaw-memory") -> str:
    """Rewrite localhost/127.0.0.1 in memU URL to Docker DNS hostname.
    Only replaces the hostname portion — port and path are preserved.
    Non-localhost URLs pass through unchanged."""
    if not url:
        return url
    return _LOCALHOST_PATTERN.sub(r'\1' + dns_hostname + r'\2', url)


def _ensure_openclaw_network(client: docker.DockerClient, network_name: str = "openclaw-net") -> None:
    """Ensure the named Docker bridge network exists, creating it if absent.
    Idempotent — safe to call on every spawn."""
    try:
        client.networks.get(network_name)
        logger.debug("Docker network exists", extra={"network": network_name})
    except docker.errors.NotFound:
        try:
            client.networks.create(network_name, driver="bridge")
            logger.info("Created Docker network", extra={"network": network_name})
        except docker.errors.APIError as exc:
            logger.warning(
                "Failed to create Docker network (non-blocking)",
                extra={"network": network_name, "error": str(exc)},
            )


def get_docker_client() -> docker.DockerClient:
    """Return a shared Docker client, creating or reconnecting as needed.

    Lazily creates the client on first call (INFO log). Verifies liveness via
    ping on every call; if the daemon has restarted the ping fails and a fresh
    client is created (WARNING log). Subsequent reuses are logged at DEBUG.

    No threading locks are used — docker.DockerClient is already thread-safe
    for concurrent API calls.

    Returns:
        A live docker.DockerClient connected to the local Docker daemon.

    Raises:
        RuntimeError: If the Docker daemon is not reachable.
    """
    global _docker_client

    if _docker_client is None:
        _docker_client = docker.from_env()
        logger.info("Docker client created")
        return _docker_client

    # Verify liveness; reconnect transparently if daemon restarted
    try:
        _docker_client.ping()
        logger.debug("Docker client reused")
    except Exception:
        _docker_client = docker.from_env()
        logger.warning("Docker client reconnected (daemon restart detected)")

    return _docker_client


def _validate_project_id(project_id: str) -> None:
    """Validate project ID format: 1-20 chars, alphanumeric and hyphens only.

    Raises:
        ValueError: If project_id is invalid.
    """
    if not _PROJECT_ID_PATTERN.match(project_id):
        raise ValueError(
            f"Invalid project ID '{project_id}': must be 1-20 chars, "
            "alphanumeric and hyphens only."
        )


def load_l3_config(project_id: Optional[str] = None) -> Dict[str, Any]:
    """Load L3 specialist configuration, with optional project overrides."""
    try:
        agent_map = get_agent_mapping(project_id)
        l3_agent_id = agent_map.get("l3_executor", "l3_specialist")
    except (FileNotFoundError, ValueError):
        l3_agent_id = "l3_specialist"

    config_path = Path(__file__).parent.parent.parent / "agents" / l3_agent_id / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    # Apply project-level L3 overrides if available
    try:
        project = load_project_config(project_id)
        l3_overrides = project.get("l3_overrides", {})
        if l3_overrides:
            container = config.get("container", {})
            if "mem_limit" in l3_overrides:
                container["mem_limit"] = l3_overrides["mem_limit"]
            if "cpu_quota" in l3_overrides:
                container["cpu_quota"] = l3_overrides["cpu_quota"]
            config["container"] = container
    except (FileNotFoundError, ValueError):
        pass  # No project config — use base L3 config as-is

    return config


def get_skill_timeout(skill_hint: str) -> int:
    """Get timeout in seconds for a skill from the L3 config."""
    config = load_l3_config()
    skill_registry = config.get("skill_registry", {})
    skill_config = skill_registry.get(skill_hint, {})
    return skill_config.get("timeout_seconds", 600)


def _retrieve_memories_sync(base_url: str, project_id: str, query: str) -> list:
    """Retrieve memories from memU synchronously using httpx.Client.

    Uses a sync HTTP client (not MemoryClient which is async) to avoid event-loop
    conflicts when spawn.py is called from pool.py's async context.

    Args:
        base_url:   Root URL of the memU service, e.g. "http://localhost:18791".
        project_id: Project ID used as the memU user_id scope key.
        query:      Natural-language query for semantic retrieval.

    Returns:
        List of memory dicts on success, [] on any error (graceful degradation).
    """
    if not base_url or not project_id:
        return []
    payload = {
        "queries": [{"role": "user", "content": query}],
        "where": {"user_id": project_id},
    }
    try:
        with httpx.Client(base_url=base_url, timeout=_RETRIEVE_TIMEOUT) as client:
            response = client.post("/retrieve", json=payload)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data[:_RETRIEVE_LIMIT]
            if isinstance(data, dict) and "items" in data:
                return data["items"][:_RETRIEVE_LIMIT]
            return []
    except Exception as exc:
        logger.warning(
            "Pre-spawn memory retrieval failed (non-blocking)",
            extra={"project_id": project_id, "error": str(exc)},
        )
        return []


def _format_memory_context(memories: list) -> str:
    """Format retrieved memories into two distinct markdown sections by category.

    Splits memories into:
    - "## Past Work Context" — L3 task outcomes (category == "l3_outcome" or
      no special category)
    - "## Past Review Outcomes" — L2 review decisions (category ==
      "review_decision" OR agent_type == "l2_pm" as fallback)

    Both sections share the MEMORY_CONTEXT_BUDGET (2,000 chars). Items are
    added in rank order from memU and the shared counter stops as soon as a
    bullet would exceed the budget (whole-item drop, not truncation). Empty
    sections are omitted — no empty headers, no placeholders. Empty input
    returns "" (no headers at all).

    Args:
        memories: List of memory dicts from memU /retrieve response.

    Returns:
        One or two section strings joined by double newline, or "" when no
        items fit within the budget or the input list is empty.
    """
    if not memories:
        return ""

    work_bullets = []
    review_bullets = []
    total_chars = 0

    for item in memories:
        # Extract content — memU stores text in resource_url field
        text = item.get("resource_url", "") or item.get("content", "") or ""
        if not text:
            continue

        # Discriminate category: dual check (category field + agent_type fallback)
        is_review = (
            item.get("category", "") == "review_decision"
            or item.get("agent_type", "") == "l2_pm"
        )

        bullet = f"- {text}"
        candidate = total_chars + len(bullet) + 1  # +1 for \n separator
        if candidate > MEMORY_CONTEXT_BUDGET:
            break  # drop remaining items rather than truncating

        if is_review:
            review_bullets.append(bullet)
        else:
            work_bullets.append(bullet)
        total_chars += len(bullet) + 1

    sections = []
    if work_bullets:
        sections.append("## Past Work Context\n\n" + "\n".join(work_bullets))
    if review_bullets:
        sections.append("## Past Review Outcomes\n\n" + "\n".join(review_bullets))

    return "\n\n".join(sections) if sections else ""


def _build_augmented_soul(project_root: Path, memory_context: str) -> str:
    """Read the L3 SOUL.md base and append the memory context section.

    Reads the L3 specialist SOUL directly (NOT render_soul() which produces L2
    agent content). The L3 SOUL has no template variables, so it can be read
    as plain text.

    Args:
        project_root:   Root directory of the openclaw project.
        memory_context: Formatted ## Memory Context section, or "" for none.

    Returns:
        Augmented SOUL string, or "" if the L3 SOUL file is missing.
        When memory_context is empty, returns the base SOUL unchanged.
    """
    soul_path = project_root / "agents" / "l3_specialist" / "agent" / "SOUL.md"
    if not soul_path.exists():
        return ""
    base = soul_path.read_text(encoding="utf-8")
    if not memory_context:
        return base
    return base.rstrip("\n") + "\n\n" + memory_context + "\n"


def _write_soul_tempfile(content: str) -> Path:
    """Write SOUL content to a named temporary file.

    DEPRECATED: Use _write_soul_file() for new code. Retained for existing tests.

    Uses delete=False so the file path can be passed to Docker volumes dict and
    the file remains on disk until the caller explicitly unlinks it. Docker
    bind-mounts by inode — the host can unlink after containers.run() returns
    and the container retains read access.

    Args:
        content: Full text content to write to the temp file.

    Returns:
        Path to the created temp file (caller is responsible for cleanup).
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".soul.md",
        prefix="openclaw-",
        delete=False,
    )
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _write_soul_file(content: str, project_id: str, task_id: str, workspace_root: Path) -> Path:
    """Write augmented SOUL to per-task file in project state directory.
    Path: workspace/.openclaw/<project_id>/soul-<task_id>.md
    File persists after container exit for debugging.
    Caller does NOT clean up — files are removed with project removal.

    Args:
        content:        Full text content to write.
        project_id:     Project ID for directory namespacing.
        task_id:        Task ID for unique filename.
        workspace_root: Root of the openclaw project (parent of .openclaw/).

    Returns:
        Path to the written soul file.
    """
    state_dir = workspace_root / ".openclaw" / project_id
    state_dir.mkdir(parents=True, exist_ok=True)
    soul_path = state_dir / f"soul-{task_id}.md"
    soul_path.write_text(content, encoding="utf-8")
    return soul_path


def spawn_l3_specialist(
    task_id: str,
    skill_hint: str,
    task_description: str,
    workspace_path: str,
    requires_gpu: bool = False,
    cli_runtime: str = "claude-code",
    project_id: Optional[str] = None,
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
        project_id: Project ID for namespacing. If None, resolved from active project.

    Returns:
        Docker container object

    Raises:
        docker.errors.APIError: If Docker daemon is not running
        docker.errors.ImageNotFound: If the L3 image is not built
        ValueError: If project_id is invalid or cannot be resolved
    """
    # Resolve project identity once at entry — thread explicitly from here on
    if project_id is None:
        project_id = get_active_project_id()
    _validate_project_id(project_id)

    # Get shared Docker client (creates or reconnects as needed)
    try:
        client = get_docker_client()
    except Exception as e:
        raise RuntimeError(
            f"Docker daemon not running: {e}. Please start Docker and try again."
        ) from e

    # Ensure openclaw-net bridge network exists (idempotent)
    _ensure_openclaw_network(client)

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

    # Detect default branch for this project's workspace — injected into container
    default_branch = _detect_default_branch(Path(workspace_path), project_id)

    # Build namespaced container name — prevents cross-project name collisions
    container_name = f"openclaw-{project_id}-l3-{task_id}"

    # Get project root for orchestration mount
    project_root = Path(__file__).parent.parent.parent

    # Load L3 config for hierarchy metadata (pass project_id for overrides)
    l3_config = load_l3_config(project_id)

    # Resolve spawned_by from project config, falling back to L3 config
    try:
        agent_map = get_agent_mapping(project_id)
        spawned_by = agent_map.get("l2_pm", l3_config.get("spawned_by", "pumplai_pm"))
    except (FileNotFoundError, ValueError):
        spawned_by = l3_config.get("spawned_by", "pumplai_pm")

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

        # Environment variables — OPENCLAW_PROJECT injected for container-side identity
        "environment": {
            "TASK_ID": task_id,
            "SKILL_HINT": skill_hint,
            "STAGING_BRANCH": staging_branch,
            "DEFAULT_BRANCH": default_branch,
            "CLI_RUNTIME": cli_runtime,
            "TASK_DESCRIPTION": task_description,
            "OPENCLAW_PROJECT": project_id,
            "OPENCLAW_STATE_FILE": f"/workspace/.openclaw/{project_id}/workspace-state.json",
            "MEMU_API_URL": _rewrite_memu_url_for_container(get_memu_config().get("memu_api_url", "")),
            "MEMU_AGENT_ID": "l3_specialist",
            "MEMU_PROJECT_ID": project_id,
            "MEMU_ENABLED": "1",
        },

        # Docker network — enables DNS resolution for openclaw-memory service
        "network": "openclaw-net",

        # Security isolation (HIE-04 requirements)
        "security_opt": ["no-new-privileges"],
        "cap_drop": ["ALL"],

        # Resource limits
        "mem_limit": l3_config.get("container", {}).get("mem_limit", "4g"),
        "cpu_quota": l3_config.get("container", {}).get("cpu_quota", 100000),

        # Restart policy (L2 handles retries, not Docker)
        "restart_policy": {"Name": "no"},

        # Labels for tracking and project-scoped filtering
        "labels": {
            "openclaw.managed": "true",
            "openclaw.level": str(l3_config.get("level", 3)),
            "openclaw.task_id": task_id,
            "openclaw.spawned_by": spawned_by,
            "openclaw.skill": skill_hint,
            "openclaw.tier": f"l{l3_config.get('level', 3)}",  # preserved for backward compat
            "openclaw.project": project_id,
            "openclaw.task.type": skill_hint,
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

    # Create task entry in state.json before spawning — use project-scoped path
    state_file = get_state_path(project_id)
    jarvis = JarvisState(state_file)
    jarvis.create_task(
        task_id=task_id,
        skill_hint=skill_hint,
        metadata={
            "cli_runtime": cli_runtime,
            "requires_gpu": requires_gpu,
            "container_name": container_name,
            "staging_branch": staging_branch,
            "spawn_requested_at": time.time(),
        }
    )

    # Check for existing container with same name and remove if found
    try:
        old_container = client.containers.get(container_name)
        logger.info("Removing existing container", extra={"task_id": task_id, "project_id": project_id, "container_name": container_name})
        old_container.remove(force=True)
    except docker.errors.NotFound:
        pass  # Container doesn't exist, which is fine

    # --- Pre-spawn memory retrieval and SOUL injection ---
    memu_cfg = get_memu_config()
    memu_url = memu_cfg.get("memu_api_url", "")
    query = f"{task_description} skill:{skill_hint}"
    memories = _retrieve_memories_sync(memu_url, project_id, query)
    memory_context = _format_memory_context(memories)

    if memory_context:
        bullet_count = sum(1 for line in memory_context.splitlines() if line.startswith("-"))
        logger.info(
            f"Injected {bullet_count} memories ({len(memory_context)} chars) into SOUL",
            extra={"task_id": task_id, "project_id": project_id},
        )

    soul_content = _build_augmented_soul(project_root, memory_context)
    soul_file = None
    if soul_content:
        soul_file = _write_soul_file(soul_content, project_id, task_id, project_root)
        container_config["volumes"][str(soul_file)] = {
            "bind": SOUL_CONTAINER_PATH,
            "mode": "ro",
        }
        container_config["environment"]["SOUL_FILE"] = SOUL_CONTAINER_PATH

    # Spawn container
    logger.info("Spawning L3 container", extra={"task_id": task_id, "project_id": project_id, "container_name": container_name, "skill": skill_hint, "gpu": requires_gpu})

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
        logger.info("Container removed", extra={"container_name": container.name})
    except docker.errors.NotFound:
        logger.debug("Container already removed", extra={"container_name": container.name})
    except Exception as e:
        logger.error("Error removing container", extra={"container_name": container.name, "error": str(e)})


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
    # Resolve default workspace from project config
    try:
        _default_workspace = get_workspace_path()
    except (FileNotFoundError, ValueError):
        _default_workspace = None

    parser.add_argument("--workspace", default=_default_workspace, help="Workspace path")
    parser.add_argument("--project", default=None, help="Project ID (overrides active_project)")
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
        project_id=args.project,
    )

    print(f"Container spawned: {container.id}")
