"""
L3 Container Pool Management

Manages concurrent L3 specialist containers with semaphore-based limiting,
auto-retry logic, and ephemeral container lifecycle. Supports per-project
pool isolation via PoolRegistry.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import docker
from spawn import (
    cleanup_container,
    get_container_logs,
    get_skill_timeout,
    load_l3_config,
    spawn_l3_specialist,
)
from orchestration.state_engine import JarvisState
from orchestration.project_config import get_active_project_id, get_workspace_path, get_state_path


class L3ContainerPool:
    """
    Manage pool of L3 specialist containers with max 3 concurrent limit.

    Uses asyncio.Semaphore for concurrency control and implements auto-retry
    once on failure. Containers are ephemeral (removed after completion).

    Each pool instance is scoped to a single project_id. State file access
    is resolved per-call via get_state_path(self.project_id) — there is no
    cached self.state_file attribute.
    """

    def __init__(self, max_concurrent: int = 3, project_id: Optional[str] = None):
        """
        Initialize the container pool.

        Args:
            max_concurrent: Maximum number of concurrent containers (default 3)
            project_id: Project scope for this pool. If None, resolved lazily
                        from the active project at first use.
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_containers: Dict[str, Any] = {}
        self.max_concurrent = max_concurrent
        self.project_id = project_id

        # Get project root for reference
        self.project_root = Path(__file__).parent.parent.parent

    async def spawn_and_monitor(
        self,
        task_id: str,
        skill_hint: str,
        task_description: str,
        workspace_path: str,
        requires_gpu: bool = False,
        cli_runtime: str = "claude-code",
    ) -> Dict[str, Any]:
        """
        Spawn L3 container with concurrency limit, monitor execution, and handle retry.

        Args:
            task_id: Unique task identifier
            skill_hint: Skill to use (code or test)
            task_description: Description of the task
            workspace_path: Path to the workspace directory on host
            requires_gpu: Whether GPU passthrough is required
            cli_runtime: CLI runtime to use

        Returns:
            Result dictionary with task_id, status, exit_code, retry_count
        """
        # Get timeout for this skill
        timeout_seconds = get_skill_timeout(skill_hint)

        # Acquire semaphore (blocks if max concurrent containers already running)
        async with self.semaphore:
            print(f"[pool] Acquired slot for task: {task_id}")

            # First attempt
            result = await self._attempt_task(
                task_id=task_id,
                skill_hint=skill_hint,
                task_description=task_description,
                workspace_path=workspace_path,
                requires_gpu=requires_gpu,
                cli_runtime=cli_runtime,
                timeout_seconds=timeout_seconds,
                retry_count=0,
            )

            # Auto-retry once on failure (per locked decision)
            if result["status"] == "failed" and result["retry_count"] == 0:
                print(f"[pool] Task {task_id} failed, retrying once...")

                # Clean up failed container
                if task_id in self.active_containers:
                    cleanup_container(self.active_containers[task_id])
                    del self.active_containers[task_id]

                # Retry
                result = await self._attempt_task(
                    task_id=task_id,
                    skill_hint=skill_hint,
                    task_description=f"{task_description} (retry)",
                    workspace_path=workspace_path,
                    requires_gpu=requires_gpu,
                    cli_runtime=cli_runtime,
                    timeout_seconds=timeout_seconds,
                    retry_count=1,
                )

            print(f"[pool] Task {task_id} final result: {result['status']}")
            return result

    async def _attempt_task(
        self,
        task_id: str,
        skill_hint: str,
        task_description: str,
        workspace_path: str,
        requires_gpu: bool,
        cli_runtime: str,
        timeout_seconds: int,
        retry_count: int,
    ) -> Dict[str, Any]:
        """
        Attempt to execute a task in an L3 container.

        Args:
            task_id: Task identifier
            skill_hint: Skill to use
            task_description: Task description
            workspace_path: Workspace path
            requires_gpu: GPU flag
            cli_runtime: CLI runtime
            timeout_seconds: Timeout for this skill
            retry_count: Current retry attempt (0 = first, 1 = retry)

        Returns:
            Result dictionary
        """
        container = None
        result = {
            "task_id": task_id,
            "status": "unknown",
            "exit_code": -1,
            "retry_count": retry_count,
        }

        try:
            # Spawn container (sync operation in executor) — thread project_id explicitly
            loop = asyncio.get_event_loop()
            container = await loop.run_in_executor(
                None,
                lambda: spawn_l3_specialist(
                    task_id=task_id,
                    skill_hint=skill_hint,
                    task_description=task_description,
                    workspace_path=workspace_path,
                    requires_gpu=requires_gpu,
                    cli_runtime=cli_runtime,
                    project_id=self.project_id,
                ),
            )

            self.active_containers[task_id] = container
            print(f"[pool] Spawned container for task {task_id}: {container.name}")

            # Monitor container execution
            monitor_result = await self.monitor_container(
                container=container,
                task_id=task_id,
                timeout_seconds=timeout_seconds,
            )

            result["status"] = monitor_result["status"]
            result["exit_code"] = monitor_result["exit_code"]

            # Update state based on result — resolve state path from project_id
            jarvis = JarvisState(get_state_path(self.project_id))
            if result["status"] == "completed":
                jarvis.update_task(
                    task_id=task_id,
                    status="completed",
                    activity_entry=f"Task completed successfully (exit code: {result['exit_code']})",
                )
            else:
                # Get error context
                last_logs = get_container_logs(container, tail=50)
                jarvis.update_task(
                    task_id=task_id,
                    status="failed",
                    activity_entry=f"Task failed (exit code: {result['exit_code']}, retry: {retry_count}). Logs: {last_logs[:200]}",
                )

        except asyncio.TimeoutError:
            print(f"[pool] Task {task_id} timed out after {timeout_seconds}s")
            result["status"] = "timeout"
            result["exit_code"] = -1

            # Kill container on timeout
            if container:
                try:
                    container.kill()
                except Exception as e:
                    print(f"[pool] Error killing container on timeout: {e}")

            # Update state
            jarvis = JarvisState(get_state_path(self.project_id))
            jarvis.update_task(
                task_id=task_id,
                status="timeout",
                activity_entry=f"Task timed out after {timeout_seconds} seconds",
            )

        except Exception as e:
            print(f"[pool] Error executing task {task_id}: {e}")
            result["status"] = "error"
            result["exit_code"] = -1
            result["error"] = str(e)

            # Update state
            jarvis = JarvisState(get_state_path(self.project_id))
            jarvis.update_task(
                task_id=task_id,
                status="failed",
                activity_entry=f"Task execution error: {str(e)[:200]}",
            )

        finally:
            # Cleanup container (ephemeral lifecycle)
            if container:
                await loop.run_in_executor(None, cleanup_container, container)

            if task_id in self.active_containers:
                del self.active_containers[task_id]

        return result

    async def monitor_container(
        self,
        container: Any,
        task_id: str,
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """
        Monitor container execution and capture logs.

        Args:
            container: Docker container object
            task_id: Task identifier
            timeout_seconds: Timeout for container execution

        Returns:
            Dictionary with exit_code and status
        """
        print(f"[pool] Monitoring container for task {task_id} (timeout: {timeout_seconds}s)")

        # Stream logs in real-time
        async def stream_logs():
            try:
                loop = asyncio.get_event_loop()
                # Get log stream from container (this is sync, run in executor)
                log_stream = await loop.run_in_executor(
                    None,
                    lambda: container.logs(stream=True, follow=True, stdout=True, stderr=True),
                )

                async for log_line in log_stream:
                    decoded = log_line.decode("utf-8", errors="replace").strip()
                    print(f"[L3-{task_id}] {decoded}")
            except Exception as e:
                print(f"[pool] Log streaming error: {e}")

        # Start log streaming task
        log_task = asyncio.create_task(stream_logs())

        try:
            # Wait for container with timeout
            loop = asyncio.get_event_loop()
            wait_result = await asyncio.wait_for(
                loop.run_in_executor(None, container.wait),
                timeout=timeout_seconds,
            )

            exit_code = wait_result.get("StatusCode", -1)
            status = "completed" if exit_code == 0 else "failed"

            print(f"[pool] Container for task {task_id} exited with code {exit_code}")

            return {
                "exit_code": exit_code,
                "status": status,
            }

        except asyncio.TimeoutError:
            print(f"[pool] Container timeout for task {task_id}")
            raise  # Re-raise to be handled by caller

        finally:
            # Cancel log streaming
            log_task.cancel()
            try:
                await log_task
            except asyncio.CancelledError:
                pass

    def get_active_count(self) -> int:
        """Return number of active containers."""
        return len(self.active_containers)

    def list_active(self) -> list:
        """Return list of active task IDs."""
        return list(self.active_containers.keys())


class PoolRegistry:
    """Manages per-project L3ContainerPool instances.

    Each project gets its own independent pool with its own semaphore,
    preventing cross-project semaphore contention.
    """

    def __init__(self, max_per_project: int = 3):
        self._pools: Dict[str, L3ContainerPool] = {}
        self._max_per_project = max_per_project

    def get_pool(self, project_id: str) -> L3ContainerPool:
        """Get or create pool for a project.

        Returns the same pool instance on repeated calls for the same project_id.
        Different project IDs get independent pool instances with separate semaphores.
        """
        if project_id not in self._pools:
            self._pools[project_id] = L3ContainerPool(
                max_concurrent=self._max_per_project,
                project_id=project_id,
            )
        return self._pools[project_id]

    def active_count(self) -> Dict[str, int]:
        """Return active container count per project."""
        return {pid: pool.get_active_count() for pid, pool in self._pools.items()}


# Convenience function for spawning a single task
async def spawn_task(
    task_id: str,
    skill_hint: str,
    task_description: str,
    workspace_path: Optional[str] = None,
    requires_gpu: bool = False,
    cli_runtime: str = "claude-code",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Spawn a single L3 task with default pool settings.

    This is a convenience function that creates a pool and spawns one task.
    For multiple concurrent tasks, use the pool directly.
    For persistent per-project pools across calls, use PoolRegistry.

    Args:
        project_id: Project scope. If None, resolved from active project.
    """
    if workspace_path is None:
        try:
            workspace_path = get_workspace_path()
        except (FileNotFoundError, ValueError):
            workspace_path = "/home/ollie/.openclaw/workspace"

    if project_id is None:
        try:
            project_id = get_active_project_id()
        except (FileNotFoundError, ValueError):
            project_id = None  # spawn_l3_specialist will resolve it

    pool = L3ContainerPool(max_concurrent=3, project_id=project_id)
    return await pool.spawn_and_monitor(
        task_id=task_id,
        skill_hint=skill_hint,
        task_description=task_description,
        workspace_path=workspace_path,
        requires_gpu=requires_gpu,
        cli_runtime=cli_runtime,
    )


if __name__ == "__main__":
    # Test the pool with a single task
    import argparse

    parser = argparse.ArgumentParser(description="Test L3 container pool")
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument("skill_hint", choices=["code", "test"], help="Skill to use")
    parser.add_argument("task_description", help="Task description")
    try:
        _default_workspace = get_workspace_path()
    except (FileNotFoundError, ValueError):
        _default_workspace = "/home/ollie/.openclaw/workspace"
    parser.add_argument("--workspace", default=_default_workspace)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--runtime", default="claude-code")
    parser.add_argument("--project", default=None, help="Project ID (overrides active_project)")

    args = parser.parse_args()

    result = asyncio.run(spawn_task(
        task_id=args.task_id,
        skill_hint=args.skill_hint,
        task_description=args.task_description,
        workspace_path=args.workspace,
        requires_gpu=args.gpu,
        cli_runtime=args.runtime,
        project_id=args.project,
    ))

    print(f"\nResult: {result}")
