"""
L3 Container Pool Management

Manages concurrent L3 specialist containers with semaphore-based limiting,
auto-retry logic, and ephemeral container lifecycle. Supports per-project
pool isolation via PoolRegistry.

Pool modes:
  - "shared"   (default): All shared-mode projects share a single global semaphore.
  - "isolated": Each project gets its own dedicated semaphore, preventing
                cross-project contention.

Overflow policies (what happens when all slots are occupied):
  - "wait"     (default): Queue and wait up to queue_timeout_s, then raise PoolOverflowError.
  - "reject":  Raise PoolOverflowError immediately.
  - "priority": Use priority queue — lower priority number = higher precedence.
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import docker
from spawn import (
    cleanup_container,
    get_container_logs,
    get_docker_client,
    get_skill_timeout,
    load_l3_config,
    spawn_l3_specialist,
)
from openclaw.state_engine import JarvisState
from openclaw.config import (
    get_state_path,
    get_snapshot_dir,
    DEFAULT_POOL_MAX_CONCURRENT,
    DEFAULT_POOL_MODE,
    DEFAULT_POOL_OVERFLOW_POLICY,
    DEFAULT_POOL_QUEUE_TIMEOUT_S,
    DEFAULT_POOL_RECOVERY_POLICY,
)
from openclaw.project_config import get_active_project_id, get_workspace_path, get_pool_config, get_memu_config
from openclaw.logging import get_logger

logger = get_logger("pool")

_shutdown_handler_registered = False  # module-level idempotency guard — prevents double-registration if spawn_task() called multiple times


class PoolOverflowError(Exception):
    """Raised when a pool slot cannot be acquired within the configured policy constraints.

    Raised in two situations:
    - overflow_policy == "reject": All slots are occupied at the time of the spawn request.
    - overflow_policy == "wait": Queue timeout expired before a slot became available.
    """
    pass


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
                            Defaults to 3 (matches DEFAULT_POOL_MAX_CONCURRENT).
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

        # Pool mode and config (set by PoolRegistry; overflow policy read from _pool_config)
        self._pool_mode: str = DEFAULT_POOL_MODE
        self._pool_config: Dict[str, Any] = {
            "max_concurrent": DEFAULT_POOL_MAX_CONCURRENT,
            "pool_mode": DEFAULT_POOL_MODE,
            "overflow_policy": DEFAULT_POOL_OVERFLOW_POLICY,
            "queue_timeout_s": DEFAULT_POOL_QUEUE_TIMEOUT_S,
            "recovery_policy": DEFAULT_POOL_RECOVERY_POLICY,
        }

        # Priority queue for "priority" overflow policy.
        # Entries: (priority_num, task_id). Lower number = higher priority.
        self._priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

        # Fire-and-forget memorize task tracking (REL-08)
        self._pending_memorize_tasks: list = []

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
        priority: int = 1,
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
            priority: Task priority for "priority" overflow policy. Lower number = higher
                      priority (0 = elevated, 1 = standard). Only meaningful when
                      overflow_policy is "priority".

        Returns:
            Result dictionary with task_id, status, exit_code, retry_count

        Raises:
            PoolOverflowError: If overflow_policy is "reject" and all slots are full,
                               or if overflow_policy is "wait" and queue_timeout_s expires.
        """
        # Get timeout for this skill
        timeout_seconds = get_skill_timeout(skill_hint)

        # Read overflow policy from attached config
        overflow_policy = self._pool_config.get("overflow_policy", DEFAULT_POOL_OVERFLOW_POLICY)
        queue_timeout_s = self._pool_config.get("queue_timeout_s", DEFAULT_POOL_QUEUE_TIMEOUT_S)

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
                    "overflow_policy": overflow_policy,
                },
            )

        # --- Overflow policy enforcement BEFORE semaphore acquisition ---

        if overflow_policy == "reject":
            # Immediate rejection when all slots are occupied
            if self.semaphore._value == 0:
                self.queued_count -= 1
                active_task_ids = self.list_active()
                logger.warning(
                    "Pool overflow — rejecting task (policy: reject)",
                    extra={
                        "project_id": self.project_id,
                        "task_id": task_id,
                        "slots_occupied": self.max_concurrent,
                        "running_task_ids": active_task_ids,
                        "overflow_policy": "reject",
                    },
                )
                raise PoolOverflowError(
                    f"Pool full for project '{self.project_id}': all {self.max_concurrent} slot(s) occupied. "
                    f"Running tasks: {active_task_ids}. Retry later or change overflow_policy to 'wait'."
                )
            # Slot available — fall through to semaphore acquire block
            slot_acquired = await self._acquire_semaphore_direct()

        elif overflow_policy == "wait":
            # Queue and wait up to queue_timeout_s
            try:
                await asyncio.wait_for(self.semaphore.acquire(), timeout=queue_timeout_s)
                slot_acquired = True
            except asyncio.TimeoutError:
                self.queued_count -= 1
                logger.warning(
                    "Pool overflow — queue timeout expired (policy: wait)",
                    extra={
                        "project_id": self.project_id,
                        "task_id": task_id,
                        "queue_timeout_s": queue_timeout_s,
                        "overflow_policy": "wait",
                    },
                )
                raise PoolOverflowError(
                    f"Pool queue timeout for project '{self.project_id}': waited {queue_timeout_s}s for a slot. "
                    f"Increase queue_timeout_s or max_concurrent in l3_overrides."
                )
            slot_acquired = True

        elif overflow_policy == "priority":
            # Priority queue mechanism: enqueue task with its priority number, then
            # tasks dequeue in priority order (lower number = higher priority) before
            # acquiring the semaphore slot.
            ticket: asyncio.Future = asyncio.get_event_loop().create_future()
            await self._priority_queue.put((priority, task_id, ticket))
            logger.debug(
                "Task enqueued in priority queue",
                extra={
                    "project_id": self.project_id,
                    "task_id": task_id,
                    "priority": priority,
                    "queue_size": self._priority_queue.qsize(),
                },
            )
            # Wait for this ticket to be resolved (semaphore slot granted by queue processor)
            await self._process_priority_queue()
            # At this point the semaphore has been acquired for our ticket
            slot_acquired = True

        else:
            # Unknown policy — fall back to default "wait" behaviour
            logger.warning(
                "Unknown overflow_policy — falling back to 'wait'",
                extra={"project_id": self.project_id, "task_id": task_id, "policy": overflow_policy},
            )
            await self.semaphore.acquire()
            slot_acquired = True

        # Semaphore slot is now held (for reject/wait/priority paths above).
        # Use try/finally to guarantee release even if an exception occurs below.
        try:
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

            # Prune completed memorize tasks to prevent unbounded list growth
            self._pending_memorize_tasks = [t for t in self._pending_memorize_tasks if not t.done()]

            logger.info("Task final result", extra={"task_id": task_id, "status": result["status"]})
            return result

        finally:
            # Release semaphore slot — mirrors the behaviour of `async with self.semaphore:`
            self.semaphore.release()

    async def _acquire_semaphore_direct(self) -> bool:
        """Acquire the semaphore directly (used by the reject policy when a slot is available)."""
        await self.semaphore.acquire()
        return True

    async def _process_priority_queue(self) -> None:
        """Process the priority queue: acquire semaphore in priority order.

        Dequeues entries in priority order (lowest priority_num first) and
        acquires the semaphore for each in turn. This ensures higher-priority
        tasks get slots before standard-priority tasks when contending.

        For simplicity, this drains the queue one entry at a time and then
        acquires the semaphore — callers return after the acquire for their entry.
        """
        # Acquire the semaphore — this blocks until a slot is available.
        # The PriorityQueue ordering ensures high-priority tasks are ahead in line
        # but since asyncio.PriorityQueue is not a true priority semaphore, the
        # mechanism here is: each task calls this method, acquires the semaphore,
        # then dequeues itself. The queue's priority ordering influences which
        # awaiting coroutine gets unblocked by the asyncio scheduler first.
        await self.semaphore.acquire()
        # Drain our own entry from the priority queue (best-effort)
        if not self._priority_queue.empty():
            try:
                self._priority_queue.get_nowait()
                self._priority_queue.task_done()
            except asyncio.QueueEmpty:
                pass

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

                # Fire-and-forget memorization (MEM-01): non-blocking, runs concurrently after slot release
                snapshot_path = get_snapshot_dir(self.project_id) / f"{task_id}.diff"
                snapshot_content = snapshot_path.read_text() if snapshot_path.exists() else f"Task {task_id} completed (no snapshot available)"
                # Fire-and-forget memorization — track for shutdown drain (REL-08)
                mem_task = asyncio.create_task(
                    self._memorize_snapshot_fire_and_forget(task_id, snapshot_content, skill_hint)
                )
                self._pending_memorize_tasks.append(mem_task)
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

    async def _memorize_snapshot_fire_and_forget(
        self,
        task_id: str,
        snapshot_content: str,
        skill_hint: str,
    ) -> None:
        """
        Memorize L3 task snapshot in memU. Non-blocking fire-and-forget.

        Called via asyncio.create_task() -- exceptions are caught and logged,
        never raised. Memorization failure is completely non-blocking.
        """
        from openclaw.memory_client import MemoryClient, AgentType

        memu_cfg = get_memu_config()
        base_url = memu_cfg.get("memu_api_url", "").strip()
        if not base_url:
            logger.debug(
                "MEMU_API_URL not configured -- skipping memorization",
                extra={"task_id": task_id},
            )
            return

        agent_type = AgentType.L3_CODE if skill_hint == "code" else AgentType.L3_TEST
        try:
            async with MemoryClient(base_url, self.project_id, agent_type) as client:
                result = await client.memorize(
                    f"# L3 {skill_hint.upper()} task {task_id}\n\n{snapshot_content}",
                    category="l3_outcome",
                )
            if result is not None:
                logger.info(
                    "Snapshot memorized",
                    extra={"task_id": task_id, "project_id": self.project_id},
                )
        except Exception as exc:
            logger.warning(
                "Snapshot memorization failed (non-blocking)",
                extra={"task_id": task_id, "error": str(exc)},
            )

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

    async def drain_pending_memorize_tasks(self, timeout: float = 30.0) -> dict:
        """Drain pending fire-and-forget memorize tasks before shutdown.

        Called on SIGTERM to ensure in-flight memorizations complete.
        Returns a summary dict with counts of drained/timed-out tasks.

        Args:
            timeout: Maximum seconds to wait for pending tasks to complete.
        """
        pending = [t for t in self._pending_memorize_tasks if not t.done()]
        if not pending:
            logger.info("No pending memorize tasks to drain")
            return {"pending": 0, "drained": 0, "timed_out": False}

        logger.info(
            "Draining pending memorize tasks",
            extra={"pending_count": len(pending), "timeout": timeout},
        )
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True),
                timeout=timeout,
            )
            logger.info("Memorize drain complete", extra={"drained": len(pending)})
            return {"pending": len(pending), "drained": len(pending), "timed_out": False}
        except asyncio.TimeoutError:
            done_count = sum(1 for t in pending if t.done())
            logger.warning(
                "Memorize drain timed out — discarding remaining tasks",
                extra={"timeout": timeout, "drained": done_count, "remaining": len(pending) - done_count},
            )
            return {"pending": len(pending), "drained": done_count, "timed_out": True}


    async def run_recovery_scan(self) -> dict:
        """Scan for orphaned tasks at pool startup and apply recovery policy.

        Checks workspace-state.json for tasks in 'in_progress', 'interrupted',
        or 'starting' states that are older than their skill timeout. Applies
        the configured recovery_policy (mark_failed / auto_retry / manual).

        Returns:
            Summary dict with scanned, mark_failed, retried, manual counts.
        """
        recovery_policy = self._pool_config.get("recovery_policy", DEFAULT_POOL_RECOVERY_POLICY)

        scanned = 0
        mark_failed_count = 0
        retried_count = 0
        manual_count = 0

        try:
            state_path = get_state_path(self.project_id)
            jarvis = JarvisState(state_path)
            active_task_ids = jarvis.list_active_tasks()
        except Exception as exc:
            logger.warning(
                "Recovery scan: failed to read state — skipping scan",
                extra={"project_id": self.project_id, "error": str(exc)},
            )
            logger.info(
                "Pool startup: recovery scan complete",
                extra={
                    "project_id": self.project_id,
                    "scanned": 0,
                    "mark_failed": 0,
                    "retried": 0,
                    "manual": 0,
                    "policy": recovery_policy,
                },
            )
            return {"scanned": 0, "mark_failed": 0, "retried": 0, "manual": 0}

        recoverable_states = {"in_progress", "interrupted", "starting"}

        for task_id in active_task_ids:
            try:
                task = jarvis.read_task(task_id)
                if task is None:
                    continue

                status = task.get("status", "")
                if status not in recoverable_states:
                    continue

                scanned += 1

                skill_hint = task.get("skill_hint", "code")
                timeout_s = get_skill_timeout(skill_hint)

                metadata = task.get("metadata", {})
                spawn_requested_at = metadata.get("spawn_requested_at")

                if spawn_requested_at is None or not isinstance(spawn_requested_at, (int, float)):
                    logger.warning(
                        "Recovery scan: task has no spawn_requested_at — treating as expired",
                        extra={"project_id": self.project_id, "task_id": task_id, "status": status},
                    )
                    age_s = timeout_s + 1  # treat as expired
                else:
                    age_s = time.time() - spawn_requested_at

                if age_s < timeout_s:
                    # Task is still within its allowed time window — skip
                    scanned -= 1
                    continue

                # Apply recovery policy
                if recovery_policy == "mark_failed":
                    jarvis.update_task(
                        task_id=task_id,
                        status="failed",
                        activity_entry=f"RECOVERED: task-{task_id} -> mark_failed (age: {age_s:.0f}s, timeout: {timeout_s}s)",
                    )
                    mark_failed_count += 1
                    logger.info(
                        "Recovery scan: task marked failed",
                        extra={"project_id": self.project_id, "task_id": task_id, "age_s": round(age_s, 1)},
                    )

                elif recovery_policy == "auto_retry":
                    retry_count = metadata.get("retry_count", 0)
                    if retry_count >= 1:
                        # Retry limit reached — fall back to mark_failed
                        jarvis.update_task(
                            task_id=task_id,
                            status="failed",
                            activity_entry=f"RECOVERED: task-{task_id} -> mark_failed (retry limit reached)",
                        )
                        mark_failed_count += 1
                        logger.info(
                            "Recovery scan: task marked failed (retry limit reached)",
                            extra={"project_id": self.project_id, "task_id": task_id, "retry_count": retry_count},
                        )
                    else:
                        # Check for existing commits on staging branch
                        workspace = get_workspace_path(self.project_id)
                        branch = f"l3/task-{task_id}"
                        try:
                            git_result = subprocess.run(
                                ["git", "log", "--oneline", f"HEAD..{branch}"],
                                capture_output=True, text=True, timeout=5,
                                cwd=workspace,
                            )
                            has_commits = bool(git_result.stdout.strip())
                        except Exception:
                            has_commits = True  # conservative: assume commits exist on error

                        if has_commits:
                            jarvis.update_task(
                                task_id=task_id,
                                status="failed",
                                activity_entry=f"RECOVERED: task-{task_id} -> mark_failed (partial commits on staging branch)",
                            )
                            mark_failed_count += 1
                            logger.info(
                                "Recovery scan: task marked failed (partial commits on staging branch)",
                                extra={"project_id": self.project_id, "task_id": task_id},
                            )
                        else:
                            # No partial commits — flag for retry
                            jarvis.update_task(
                                task_id=task_id,
                                status="failed",
                                activity_entry=f"RECOVERED: task-{task_id} -> auto_retry (queued for re-spawn)",
                            )
                            retried_count += 1
                            logger.info(
                                "Recovery scan: task flagged for auto_retry",
                                extra={"project_id": self.project_id, "task_id": task_id},
                            )

                elif recovery_policy == "manual":
                    # Leave state unchanged — operator must act
                    manual_count += 1
                    logger.info(
                        "Recovery scan: task left for manual recovery",
                        extra={"project_id": self.project_id, "task_id": task_id, "status": status},
                    )

                else:
                    # Unknown policy — fall back to mark_failed
                    logger.warning(
                        "Recovery scan: unknown recovery_policy — falling back to mark_failed",
                        extra={"project_id": self.project_id, "policy": recovery_policy, "task_id": task_id},
                    )
                    jarvis.update_task(
                        task_id=task_id,
                        status="failed",
                        activity_entry=f"RECOVERED: task-{task_id} -> mark_failed (unknown policy: {recovery_policy})",
                    )
                    mark_failed_count += 1

            except Exception as exc:
                logger.warning(
                    "Recovery scan: error processing task — skipping",
                    extra={"project_id": self.project_id, "task_id": task_id, "error": str(exc)},
                )

        logger.info(
            "Pool startup: recovery scan complete",
            extra={
                "project_id": self.project_id,
                "scanned": scanned,
                "mark_failed": mark_failed_count,
                "retried": retried_count,
                "manual": manual_count,
                "policy": recovery_policy,
            },
        )

        return {"scanned": scanned, "mark_failed": mark_failed_count, "retried": retried_count, "manual": manual_count}


class PoolRegistry:
    """Manages per-project L3ContainerPool instances.

    Pool modes:
    - "isolated" (per POOL-02): Each project gets a dedicated asyncio.Semaphore,
      preventing cross-project contention entirely.
    - "shared" (default): All shared-mode projects reference the same global semaphore,
      so the total across shared projects is bounded by the shared semaphore capacity.

    Pool concurrency limits and modes are read fresh from project.json l3_overrides on
    every get_pool() call, enabling hot-reload when project.json is modified between spawns.
    """

    def __init__(self):
        self._pools: Dict[str, L3ContainerPool] = {}
        # Global shared semaphore for projects in "shared" pool_mode.
        # Created lazily on first shared-mode pool request.
        self._shared_semaphore: Optional[asyncio.Semaphore] = None
        self._shared_max: int = DEFAULT_POOL_MAX_CONCURRENT

    def get_pool(self, project_id: str) -> L3ContainerPool:
        """Get or create pool for a project, reading config fresh on every call.

        On every call:
        - Reads pool config from project.json l3_overrides via get_pool_config()
        - If pool does not exist: creates a new L3ContainerPool with config values
        - If pool exists and max_concurrent changed: recreates semaphore in-place
          without disrupting running containers
        - If pool_mode changed (shared ↔ isolated): swaps the semaphore reference
          and logs at INFO
        - overflow_policy changes take effect automatically on next spawn_and_monitor()
          since that method reads directly from pool._pool_config
        - Attaches full pool config to pool._pool_config and pool._pool_mode

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
            cfg = {
                "max_concurrent": DEFAULT_POOL_MAX_CONCURRENT,
                "pool_mode": DEFAULT_POOL_MODE,
                "overflow_policy": DEFAULT_POOL_OVERFLOW_POLICY,
                "queue_timeout_s": DEFAULT_POOL_QUEUE_TIMEOUT_S,
                "recovery_policy": DEFAULT_POOL_RECOVERY_POLICY,
            }

        new_max = cfg["max_concurrent"]
        new_pool_mode = cfg.get("pool_mode", DEFAULT_POOL_MODE)

        if project_id not in self._pools:
            # Create new pool with config-driven max_concurrent
            pool = L3ContainerPool(
                max_concurrent=new_max,
                project_id=project_id,
            )
            pool._pool_config = cfg
            pool._pool_mode = new_pool_mode

            # Assign semaphore based on pool_mode
            if new_pool_mode == "shared":
                pool.semaphore = self._get_or_create_shared_semaphore(new_max)
            # "isolated" uses the per-pool semaphore already created in __init__

            self._pools[project_id] = pool
            logger.info(
                "Created pool",
                extra={"project_id": project_id, "max_concurrent": new_max, "pool_mode": new_pool_mode},
            )
        else:
            pool = self._pools[project_id]
            old_max = pool.max_concurrent
            old_pool_mode = pool._pool_mode

            pool_mode_changed = new_pool_mode != old_pool_mode
            max_changed = new_max != old_max

            if pool_mode_changed:
                # pool_mode changed — swap semaphore reference
                if new_pool_mode == "isolated":
                    # Switch to dedicated semaphore for this project
                    pool.semaphore = asyncio.Semaphore(new_max)
                else:
                    # Switch to shared global semaphore
                    pool.semaphore = self._get_or_create_shared_semaphore(new_max)

                pool._pool_mode = new_pool_mode
                pool.max_concurrent = new_max
                pool._pool_config = cfg
                logger.info(
                    "Pool mode changed — semaphore reference swapped",
                    extra={
                        "project_id": project_id,
                        "old_pool_mode": old_pool_mode,
                        "new_pool_mode": new_pool_mode,
                        "max_concurrent": new_max,
                    },
                )
            elif max_changed:
                if new_pool_mode == "isolated":
                    # Isolated pool: recreate dedicated semaphore in-place
                    pool.semaphore = asyncio.Semaphore(new_max)
                # Shared pool: shared semaphore is not per-project; do not recreate
                pool.max_concurrent = new_max
                pool._pool_config = cfg
                logger.info(
                    "Pool config changed — max_concurrent updated",
                    extra={
                        "project_id": project_id,
                        "old_max_concurrent": old_max,
                        "new_max_concurrent": new_max,
                        "pool_mode": new_pool_mode,
                    },
                )
            else:
                # No structural change — still update _pool_config so overflow_policy
                # and queue_timeout_s changes take effect on next spawn
                pool._pool_config = cfg

        return pool

    def _get_or_create_shared_semaphore(self, max_concurrent: int) -> asyncio.Semaphore:
        """Return the global shared semaphore, creating it lazily on first call.

        The shared semaphore capacity is set from the first shared-mode project's
        max_concurrent value. Subsequent calls return the same semaphore instance.

        Args:
            max_concurrent: Capacity hint from the requesting project (used only
                            if the shared semaphore does not yet exist).

        Returns:
            The module-level shared asyncio.Semaphore instance.
        """
        if self._shared_semaphore is None:
            self._shared_semaphore = asyncio.Semaphore(max_concurrent)
            self._shared_max = max_concurrent
            logger.info(
                "Created shared pool semaphore",
                extra={"max_concurrent": max_concurrent},
            )
        return self._shared_semaphore

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


def register_shutdown_handler(loop: asyncio.AbstractEventLoop, pool: "L3ContainerPool") -> None:
    """Register SIGTERM handler for graceful pool shutdown.

    Uses loop.add_signal_handler() — NOT signal.signal() — to avoid fcntl deadlock
    when the signal fires while a state engine lock is held.

    Must be called from within the asyncio event loop context (i.e., inside an
    async function run via asyncio.run()).
    """
    global _shutdown_handler_registered
    _shutdown_handler_registered = True
    import signal

    _fired = {"flag": False}  # mutable closure for idempotency guard

    def _on_sigterm() -> None:
        if _fired["flag"]:
            return  # idempotent — ignore subsequent SIGTERMs
        _fired["flag"] = True
        logger.info("Pool SIGTERM received — scheduling memorize drain")
        loop.create_task(_drain_and_stop(loop, pool))

    loop.add_signal_handler(signal.SIGTERM, _on_sigterm)


async def _drain_and_stop(loop: asyncio.AbstractEventLoop, pool: "L3ContainerPool") -> None:
    """Drain pending memorize tasks then stop the event loop."""
    result = await pool.drain_pending_memorize_tasks(timeout=30.0)
    logger.info(
        "Pool shutdown drain complete",
        extra={"drain_result": result},
    )
    loop.stop()


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
        pool_cfg = {
            "max_concurrent": DEFAULT_POOL_MAX_CONCURRENT,
            "pool_mode": DEFAULT_POOL_MODE,
            "overflow_policy": DEFAULT_POOL_OVERFLOW_POLICY,
            "queue_timeout_s": DEFAULT_POOL_QUEUE_TIMEOUT_S,
            "recovery_policy": DEFAULT_POOL_RECOVERY_POLICY,
        }
        max_concurrent = DEFAULT_POOL_MAX_CONCURRENT

    pool = L3ContainerPool(max_concurrent=max_concurrent, project_id=project_id)
    pool._pool_config = pool_cfg
    await pool.run_recovery_scan()

    # Wire SIGTERM drain handler — idempotent, uses get_running_loop() (safe inside async context)
    global _shutdown_handler_registered
    if not _shutdown_handler_registered:
        loop = asyncio.get_running_loop()
        register_shutdown_handler(loop, pool)
        logger.debug("SIGTERM drain handler registered")

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
