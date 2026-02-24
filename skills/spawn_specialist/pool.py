"""
L3 Container Pool Management

Manages concurrent L3 specialist containers with semaphore-based limiting,
auto-retry logic, and ephemeral container lifecycle. Supports per-project
pool isolation via PoolRegistry.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import docker
from spawn import (
    cleanup_container,
    get_container_logs,
    get_docker_client,
    get_skill_timeout,
    load_l3_config,
    spawn_l3_specialist,
)
from orchestration.state_engine import JarvisState
from orchestration.project_config import get_active_project_id, get_workspace_path, get_state_path, get_pool_config
from orchestration.logging import get_logger

logger = get_logger("pool")

_POOL_DEFAULTS = {
    "max_concurrent": 3,
    "pool_mode": "shared",
    "overflow_policy": "wait",
    "queue_timeout_s": 300,
}


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
            max_concurrent: Maximum number of concurrent containers. Should be sourced
                            from project.json l3_overrides.max_concurrent via get_pool_config().
                            Defaults to 3 (matches _POOL_DEFAULTS["max_concurrent"]).
            project_id: Project scope for this pool. If None, resolved lazily
                        from the active project at first use.
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_containers: Dict[str, Any] = {}
        self.max_concurrent = max_concurrent
        self.project_id = project_id

        # Aggregate counters (in-memory, not persisted)
        self.completed_count: int = 0
        self.queued_count: int = 0
        self._saturated: bool = False

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

        # Track queued tasks and detect saturation onset
        self.queued_count += 1
        was_saturated = self.semaphore._value == 0  # All slots occupied
        if was_saturated and not self._saturated:
            self._saturated = True
            logger.warning(
                "Pool saturation onset",
                extra={
                    "project_id": self.project_id,
                    "queued_task_id": task_id,
                    "queue_depth": self.queued_count,
                    "active_task_ids": self.list_active(),
                },
            )

        # Acquire semaphore (blocks if max concurrent containers already running)
        async with self.semaphore:
            # Slot acquired — no longer queued
            self.queued_count -= 1

            # Log saturation resolution if we were saturated
            if self._saturated:
                self._saturated = False
                logger.info(
                    "Pool saturation resolved",
                    extra={
                        "project_id": self.project_id,
                        "task_id": task_id,
                        "queue_depth": self.queued_count,
                    },
                )

            logger.info("Acquired pool slot", extra={"task_id": task_id})

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
                logger.warning("Task failed, retrying", extra={"task_id": task_id, "retry_count": 1})

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

            # Increment completed count for any terminal state
            self.completed_count += 1

            logger.info("Task final result", extra={"task_id": task_id, "status": result["status"]})
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
        # Cumulative wall-clock time spent in state engine calls (lock wait proxy)
        lock_wait_total_ms: float = 0.0
        # Track spawn request time for total duration calculation
        spawn_requested_at: float = time.time()

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
            logger.info("Container spawned", extra={"task_id": task_id, "container_name": container.name})

            # Record container_started_at timestamp
            container_started_at = time.time()
            jarvis = JarvisState(get_state_path(self.project_id))
            t0 = time.time()
            jarvis.set_task_metric(task_id, "container_started_at", container_started_at)
            lock_wait_total_ms += (time.time() - t0) * 1000

            # Monitor container execution
            monitor_result = await self.monitor_container(
                container=container,
                task_id=task_id,
                timeout_seconds=timeout_seconds,
            )

            result["status"] = monitor_result["status"]
            result["exit_code"] = monitor_result["exit_code"]

            # Record completed_at before status update
            completed_at = time.time()
            t0 = time.time()
            jarvis.set_task_metric(task_id, "completed_at", completed_at)
            lock_wait_total_ms += (time.time() - t0) * 1000

            # Record retry_count
            t0 = time.time()
            jarvis.set_task_metric(task_id, "retry_count", retry_count)
            lock_wait_total_ms += (time.time() - t0) * 1000

            # Update state based on result — resolve state path from project_id
            if result["status"] == "completed":
                t0 = time.time()
                jarvis.update_task(
                    task_id=task_id,
                    status="completed",
                    activity_entry=f"Task completed successfully (exit code: {result['exit_code']})",
                )
                lock_wait_total_ms += (time.time() - t0) * 1000
            else:
                # Get error context
                last_logs = get_container_logs(container, tail=50)
                t0 = time.time()
                jarvis.update_task(
                    task_id=task_id,
                    status="failed",
                    activity_entry=f"Task failed (exit code: {result['exit_code']}, retry: {retry_count}). Logs: {last_logs[:200]}",
                )
                lock_wait_total_ms += (time.time() - t0) * 1000

            # Persist cumulative lock wait
            jarvis.set_task_metric(task_id, "lock_wait_ms", round(lock_wait_total_ms, 2))

            # Emit structured lifecycle metrics log
            spawn_to_complete_ms = (completed_at - spawn_requested_at) * 1000
            execution_ms = (completed_at - container_started_at) * 1000
            logger.info(
                "Task lifecycle metrics",
                extra={
                    "task_id": task_id,
                    "spawn_to_complete_ms": round(spawn_to_complete_ms, 2),
                    "execution_ms": round(execution_ms, 2),
                    "lock_wait_ms": round(lock_wait_total_ms, 2),
                    "retry_count": retry_count,
                },
            )

        except asyncio.TimeoutError:
            logger.error("Task timed out", extra={"task_id": task_id, "timeout": timeout_seconds})
            result["status"] = "timeout"
            result["exit_code"] = -1

            # Kill container on timeout
            if container:
                try:
                    container.kill()
                except Exception as e:
                    logger.error("Error killing container on timeout", extra={"task_id": task_id, "error": str(e)})

            # Update state
            jarvis = JarvisState(get_state_path(self.project_id))
            jarvis.set_task_metric(task_id, "retry_count", retry_count)
            jarvis.update_task(
                task_id=task_id,
                status="timeout",
                activity_entry=f"Task timed out after {timeout_seconds} seconds",
            )

        except Exception as e:
            logger.error("Task execution error", extra={"task_id": task_id, "error": str(e)})
            result["status"] = "error"
            result["exit_code"] = -1
            result["error"] = str(e)

            # Update state
            jarvis = JarvisState(get_state_path(self.project_id))
            jarvis.set_task_metric(task_id, "retry_count", retry_count)
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
        logger.info("Monitoring container", extra={"task_id": task_id, "timeout": timeout_seconds})

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
                    logger.debug("L3 output", extra={"task_id": task_id, "output": decoded})
            except Exception as e:
                logger.debug("Log streaming ended", extra={"task_id": task_id, "error": str(e)})

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

            logger.info("Container exited", extra={"task_id": task_id, "exit_code": exit_code, "status": status})

            return {
                "exit_code": exit_code,
                "status": status,
            }

        except asyncio.TimeoutError:
            logger.error("Container timeout", extra={"task_id": task_id})
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

    def get_pool_stats(self) -> Dict[str, Any]:
        """Return live utilization snapshot for this pool.

        Returns:
            Dict with active, queued, completed, max_concurrent, saturation_pct,
            saturated, and project_id fields.
        """
        active = self.get_active_count()
        return {
            "project_id": self.project_id,
            "active": active,
            "queued": self.queued_count,
            "completed": self.completed_count,
            "max_concurrent": self.max_concurrent,
            "saturation_pct": round((active / self.max_concurrent) * 100, 1),
            "saturated": self._saturated,
        }


class PoolRegistry:
    """Manages per-project L3ContainerPool instances.

    Each project gets its own independent pool with its own semaphore,
    preventing cross-project semaphore contention.

    Pool concurrency limits are read fresh from project.json l3_overrides on every
    get_pool() call, enabling hot-reload when project.json is modified between spawns.
    """

    def __init__(self):
        self._pools: Dict[str, L3ContainerPool] = {}

    def get_pool(self, project_id: str) -> L3ContainerPool:
        """Get or create pool for a project, reading config fresh on every call.

        On every call:
        - Reads pool config from project.json l3_overrides via get_pool_config()
        - If pool exists and max_concurrent changed: recreates semaphore in-place
          without disrupting running containers
        - If pool does not exist: creates a new L3ContainerPool with config values
        - Attaches full pool config to pool._pool_config for use by overflow logic

        Args:
            project_id: Project ID to get or create pool for.

        Returns:
            L3ContainerPool instance for the project.
        """
        # Read fresh pool config on every call (hot-reload support)
        try:
            cfg = get_pool_config(project_id)
        except Exception as exc:
            logger.warning(
                "Failed to load pool config — using defaults",
                extra={"project_id": project_id, "error": str(exc)},
            )
            cfg = _POOL_DEFAULTS.copy()

        new_max = cfg["max_concurrent"]

        if project_id not in self._pools:
            # Create new pool with config-driven max_concurrent
            pool = L3ContainerPool(
                max_concurrent=new_max,
                project_id=project_id,
            )
            pool._pool_config = cfg
            self._pools[project_id] = pool
            logger.info(
                "Created pool",
                extra={"project_id": project_id, "max_concurrent": new_max},
            )
        else:
            pool = self._pools[project_id]
            old_max = pool.max_concurrent
            if new_max != old_max:
                # max_concurrent changed — recreate semaphore in-place
                # Running containers are not disrupted: asyncio.Semaphore internal
                # value is reset; in-flight acquires continue to completion
                pool.semaphore = asyncio.Semaphore(new_max)
                pool.max_concurrent = new_max
                pool._pool_config = cfg
                logger.info(
                    "Pool config changed — semaphore recreated",
                    extra={
                        "project_id": project_id,
                        "old_max_concurrent": old_max,
                        "new_max_concurrent": new_max,
                    },
                )
            else:
                # Config unchanged — still update _pool_config in case other fields changed
                pool._pool_config = cfg

        return pool

    def active_count(self) -> Dict[str, int]:
        """Return active container count per project."""
        return {pid: pool.get_active_count() for pid, pool in self._pools.items()}

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Return pool utilization stats for all projects.

        Returns:
            Dict mapping project_id to pool stats dict (same format as
            L3ContainerPool.get_pool_stats()).
        """
        return {pid: pool.get_pool_stats() for pid, pool in self._pools.items()}


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
            raise ValueError(
                "No workspace path configured. Set active_project in openclaw.json "
                "or pass --workspace explicitly."
            )

    if project_id is None:
        try:
            project_id = get_active_project_id()
        except (FileNotFoundError, ValueError):
            project_id = None  # spawn_l3_specialist will resolve it

    # Read pool config from project.json for config-driven max_concurrent
    try:
        pool_cfg = get_pool_config(project_id)
        max_concurrent = pool_cfg["max_concurrent"]
    except Exception:
        max_concurrent = _POOL_DEFAULTS["max_concurrent"]

    pool = L3ContainerPool(max_concurrent=max_concurrent, project_id=project_id)
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
        _default_workspace = None
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
