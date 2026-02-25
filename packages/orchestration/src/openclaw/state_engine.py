"""
Jarvis Protocol State Engine - Cross-container state synchronization with file locking.

This module provides thread-safe state management using fcntl file locking
to enable multiple L3 containers to safely read and write shared state.
"""

import asyncio
import copy
import fcntl
import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import LOCK_TIMEOUT, LOCK_RETRY_ATTEMPTS, CACHE_TTL_SECONDS, ACTIVITY_LOG_MAX_ENTRIES
from .logging import get_logger
from .project_config import get_active_project_id, get_memu_config

logger = get_logger("state_engine")

def _run_memory_injector(project_id: str, memu_url: str, agent_type: str, task_desc: str, workspace_path: Path) -> None:
    from .memory_injector import generate_memory_context
    from .memory_client import AgentType
    
    agent_enum = AgentType.L2_PM
    if agent_type == "code":
        agent_enum = AgentType.L3_CODE
    elif agent_type == "test":
        agent_enum = AgentType.L3_TEST
        
    def _run():
        try:
            asyncio.run(generate_memory_context(project_id, agent_enum, task_desc, workspace_path, memu_url))
        except Exception as e:
            logger.error(f"Memory injector failed: {e}")
            
    t = threading.Thread(target=_run, daemon=True)
    t.start()

def _run_memory_extractor(project_id: str, memu_url: str, agent_type: str, status: str, task_result: Dict[str, Any]) -> None:
    from .memory_extractor import extract_and_memorize
    from .memory_client import AgentType
    
    agent_enum = AgentType.L2_PM
    if agent_type == "code":
        agent_enum = AgentType.L3_CODE
    elif agent_type == "test":
        agent_enum = AgentType.L3_TEST
        
    def _run():
        try:
            asyncio.run(extract_and_memorize(project_id, agent_enum, task_result, status, memu_url))
        except Exception as e:
            logger.error(f"Memory extractor failed: {e}")
            
    t = threading.Thread(target=_run, daemon=True)
    t.start()


class JarvisState:
    """
    Thread-safe state engine for cross-container synchronization.

    Uses fcntl.flock() for exclusive writes (LOCK_EX) and shared reads (LOCK_SH).
    Implements atomic read-modify-write with timeout handling.
    """

    def __init__(self, state_file_path: Path):
        """
        Initialize the state engine with path to workspace-state.json.

        Args:
            state_file_path: Path to the state JSON file
        """
        self.state_file = Path(state_file_path)
        self.lock_timeout = LOCK_TIMEOUT
        self.lock_retry_attempts = LOCK_RETRY_ATTEMPTS
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_mtime: float = 0.0
        self._cache_time: float = 0.0  # time.time() when cache was populated

    def _is_cache_valid(self) -> tuple[bool, str]:
        """
        Check whether the in-memory cache is still valid.

        Returns:
            (is_valid, reason) — reason is only meaningful on cache miss.
        """
        if self._cache is None:
            return False, "first_read"
        if time.time() - self._cache_time > CACHE_TTL_SECONDS:
            return False, "ttl_expired"
        try:
            current_mtime = os.path.getmtime(self.state_file)
        except OSError:
            return False, "file_missing"
        if current_mtime != self._cache_mtime:
            return False, "mtime_changed"
        return True, ""

    def _acquire_lock(self, fd: int, lock_type: int, blocking: bool = True) -> bool:
        """
        Acquire file lock with optional timeout.

        Args:
            fd: File descriptor
            lock_type: fcntl.LOCK_EX or fcntl.LOCK_SH
            blocking: If True, wait for lock with timeout; if False, non-blocking

        Returns:
            True if lock acquired, False if timed out

        Raises:
            TimeoutError: If lock cannot be acquired within LOCK_TIMEOUT seconds
        """
        if blocking:
            start_time = time.time()
            while True:
                try:
                    fcntl.flock(fd, lock_type | fcntl.LOCK_NB)
                    lock_wait_ms = (time.time() - start_time) * 1000
                    logger.debug(
                        "Lock acquired",
                        extra={
                            "lock_type": "exclusive" if lock_type == fcntl.LOCK_EX else "shared",
                            "lock_wait_ms": round(lock_wait_ms, 2),
                        },
                    )
                    return True
                except BlockingIOError:
                    if time.time() - start_time > self.lock_timeout:
                        logger.error("Lock acquisition timeout", extra={"timeout": self.lock_timeout})
                        raise TimeoutError(f"Lock acquisition timeout after {self.lock_timeout}s")
                    time.sleep(0.1)
        else:
            try:
                fcntl.flock(fd, lock_type | fcntl.LOCK_NB)
                logger.debug(
                    "Lock acquired",
                    extra={
                        "lock_type": "exclusive" if lock_type == fcntl.LOCK_EX else "shared",
                        "lock_wait_ms": 0.0,
                    },
                )
                return True
            except BlockingIOError:
                return False

    def _release_lock(self, fd: int) -> None:
        """Release file lock."""
        fcntl.flock(fd, fcntl.LOCK_UN)

    def _ensure_state_file(self) -> None:
        """Ensure state file exists with valid schema."""
        if not self.state_file.exists():
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            initial_state = {
                "version": "1.0.0",
                "protocol": "jarvis",
                "tasks": {},
                "metadata": {
                    "created_at": time.time(),
                    "last_updated": time.time()
                }
            }
            with self.state_file.open('w') as f:
                json.dump(initial_state, f, indent=2)
                f.flush()

    def _create_backup(self) -> None:
        """
        Copy state file to .bak before writing.

        Only copies if the source file exists and has content (skip backup of empty files).
        """
        if self.state_file.exists() and self.state_file.stat().st_size > 0:
            backup_path = self.state_file.with_suffix('.json.bak')
            shutil.copy2(self.state_file, backup_path)
            logger.debug("State backup created", extra={"backup_path": str(backup_path)})

    def _read_state_locked(self, f) -> Dict[str, Any]:
        """Read state from file inside a lock context."""
        f.seek(0)
        content = f.read()
        if not content:
            # Empty file — attempt recovery from backup before reinitializing
            backup_path = self.state_file.with_suffix('.json.bak')
            if backup_path.exists():
                try:
                    with open(backup_path, 'r') as bf:
                        backup_content = bf.read()
                    recovered = json.loads(backup_content)
                    logger.warning(
                        "workspace-state.json was empty. Restored from backup."
                    )
                    f.seek(0)
                    f.truncate()
                    json.dump(recovered, f, indent=2)
                    f.flush()
                    return recovered
                except (json.JSONDecodeError, OSError) as backup_err:
                    logger.error(
                        "Backup also corrupt, reinitializing",
                        extra={"backup_error": str(backup_err)},
                    )
            else:
                logger.warning("State file is empty and no backup found, reinitializing empty state")
            return {"version": "1.0.0", "protocol": "jarvis", "tasks": {}, "metadata": {}}
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning("Corrupt JSON in state file, attempting backup recovery", extra={"error": str(e)})
            backup_path = self.state_file.with_suffix('.json.bak')
            if backup_path.exists():
                try:
                    with open(backup_path, 'r') as bf:
                        backup_content = bf.read()
                    recovered = json.loads(backup_content)
                    logger.warning(
                        "workspace-state.json was corrupt (invalid JSON). Restored from backup."
                    )
                    # Write recovered state back to main file
                    f.seek(0)
                    f.truncate()
                    json.dump(recovered, f, indent=2)
                    f.flush()
                    return recovered
                except (json.JSONDecodeError, OSError) as backup_err:
                    logger.error("Backup also corrupt, reinitializing", extra={"backup_error": str(backup_err)})
            else:
                logger.warning("No backup file found, reinitializing empty state")
            return {"version": "1.0.0", "protocol": "jarvis", "tasks": {}, "metadata": {}}

    def read_state(self) -> Dict[str, Any]:
        """
        Read current state with shared lock (LOCK_SH).

        Returns from in-memory cache when mtime has not changed (cache hit).
        Falls back to disk read with LOCK_SH on cache miss.

        Returns:
            Full state dictionary
        """
        self._ensure_state_file()

        # Check cache before acquiring any lock
        cache_valid, miss_reason = self._is_cache_valid()
        if cache_valid:
            logger.debug("State cache hit", extra={"state_file": str(self.state_file)})
            return copy.deepcopy(self._cache)

        logger.debug("State cache miss", extra={"reason": miss_reason})

        with self.state_file.open('r+') as f:
            self._acquire_lock(f.fileno(), fcntl.LOCK_SH)
            try:
                state = self._read_state_locked(f)
                # Populate cache after successful disk read
                self._cache = copy.deepcopy(state)
                self._cache_mtime = os.path.getmtime(self.state_file)
                self._cache_time = time.time()
                logger.debug("State read completed")
                return state
            finally:
                self._release_lock(f.fileno())

    def read_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Read single task entry.

        Args:
            task_id: The task identifier

        Returns:
            Task dictionary or None if not found
        """
        state = self.read_state()
        return state.get('tasks', {}).get(task_id)

    def _write_state_locked(self, f, state: Dict[str, Any]) -> None:
        """Write state to file inside a lock context (atomic write)."""
        # Ensure metadata key exists at top level
        if 'metadata' not in state:
            state['metadata'] = {}
        state['metadata']['last_updated'] = time.time()
        f.seek(0)
        f.truncate()
        json.dump(state, f, indent=2)
        f.flush()
        # Backup after successful write so .bak always holds the last known-good state
        self._create_backup()
        # Write-through: update cache so next read_state() returns from memory
        self._cache = copy.deepcopy(state)
        self._cache_mtime = os.path.getmtime(self.state_file)
        self._cache_time = time.time()
        logger.debug("Cache updated via write-through")

    def update_task(self, task_id: str, status: str, activity_entry: str) -> None:
        """
        Thread-safe state update with exclusive lock (LOCK_EX).

        Appends a timestamped entry to the activity_log array (full logging, not just status).

        Args:
            task_id: The task identifier
            status: New status (e.g., 'pending', 'in_progress', 'completed', 'failed')
            activity_entry: Description of the activity (appended to activity_log)

        Raises:
            TimeoutError: If lock cannot be acquired
        """
        self._ensure_state_file()

        # Retry loop with exponential backoff
        for attempt in range(self.lock_retry_attempts):
            try:
                with self.state_file.open('r+') as f:
                    self._acquire_lock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        state = self._read_state_locked(f)

                        # Ensure tasks dict exists
                        if 'tasks' not in state:
                            state['tasks'] = {}

                        # Ensure task entry exists
                        if task_id not in state['tasks']:
                            state['tasks'][task_id] = {
                                'status': 'pending',
                                'skill_hint': 'code',
                                'activity_log': [],
                                'created_at': time.time()
                            }
                            
                        old_status = state['tasks'][task_id].get('status', 'pending')
                        skill_hint = state['tasks'][task_id].get('skill_hint', 'code')

                        # Update status
                        state['tasks'][task_id]['status'] = status

                        # Append full activity log entry with timestamp
                        if 'activity_log' not in state['tasks'][task_id]:
                            state['tasks'][task_id]['activity_log'] = []

                        state['tasks'][task_id]['activity_log'].append({
                            'timestamp': time.time(),
                            'status': status,
                            'entry': activity_entry
                        })
                        state['tasks'][task_id]['updated_at'] = time.time()

                        # Atomic write
                        self._write_state_locked(f, state)
                        logger.info("Task updated", extra={"task_id": task_id, "status": status})
                        
                        # Trigger memory operations
                        try:
                            project_id = get_active_project_id()
                            memu_url = get_memu_config().get("url", "http://localhost:18791")
                            workspace_path = self.state_file.parent
                            
                            if old_status != 'in_progress' and status == 'in_progress':
                                _run_memory_injector(project_id, memu_url, skill_hint, activity_entry, workspace_path)
                            elif status in ('completed', 'failed', 'rejected'):
                                task_result = {
                                    "description": activity_entry,
                                    "summary": activity_entry
                                }
                                _run_memory_extractor(project_id, memu_url, skill_hint, status, task_result)
                        except Exception as e:
                            logger.error(f"Memory trigger failed: {e}")
                            
                        # Emit phase lifecycle event (fire-and-forget, never raises)
                        try:
                            from .event_bus import emit
                            from datetime import datetime, timezone
                            _status_to_event = {
                                "in_progress": "phase_started",
                                "completed": "phase_completed",
                                "waiting": "phase_blocked",
                            }
                            evt_type = _status_to_event.get(status)
                            if evt_type and task_id:
                                emit({
                                    "event_type": evt_type,
                                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                                    "project_id": get_active_project_id(),
                                    "phase_id": task_id.split("-")[0] if "-" in task_id else task_id,
                                    "container_id": None,
                                    "payload": {"task_id": task_id, "status": status, "activity_entry": activity_entry},
                                })
                        except Exception:
                            logger.debug("Event emission failed (non-blocking)", exc_info=True)

                        # Break out of retry loop on success; rotation runs after
                        break

                    finally:
                        self._release_lock(f.fileno())

            except TimeoutError:
                if attempt == self.lock_retry_attempts - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff

        # Trigger rotation check outside lock context (rotate_activity_log acquires its own lock)
        self.rotate_activity_log(task_id)

    def create_task(self, task_id: str, skill_hint: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize a new task entry.

        Args:
            task_id: The task identifier
            skill_hint: The skill to use (e.g., 'code', 'test')
            metadata: Optional additional metadata
        """
        self._ensure_state_file()

        for attempt in range(self.lock_retry_attempts):
            try:
                with self.state_file.open('r+') as f:
                    self._acquire_lock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        state = self._read_state_locked(f)

                        if 'tasks' not in state:
                            state['tasks'] = {}

                        state['tasks'][task_id] = {
                            'status': 'pending',
                            'skill_hint': skill_hint,
                            'activity_log': [],
                            'created_at': time.time(),
                            'updated_at': time.time(),
                            'metadata': metadata or {}
                        }

                        self._write_state_locked(f, state)
                        logger.info("Task created", extra={"task_id": task_id, "skill_hint": skill_hint})
                        return

                    finally:
                        self._release_lock(f.fileno())

            except TimeoutError:
                if attempt == self.lock_retry_attempts - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def set_task_metric(self, task_id: str, key: str, value: Any) -> None:
        """
        Stamp an arbitrary metric key onto a task entry.

        Uses LOCK_EX for atomic read-modify-write. Intended for pool.py to record
        timing and counter metrics (container_started_at, completed_at, lock_wait_ms,
        retry_count) without requiring a full update_task call.

        Args:
            task_id: The task identifier
            key: Metric key to set on the task entry
            value: Metric value (any JSON-serialisable type)

        Raises:
            TimeoutError: If lock cannot be acquired
        """
        self._ensure_state_file()

        for attempt in range(self.lock_retry_attempts):
            try:
                with self.state_file.open('r+') as f:
                    self._acquire_lock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        state = self._read_state_locked(f)

                        if 'tasks' not in state:
                            state['tasks'] = {}

                        if task_id not in state['tasks']:
                            state['tasks'][task_id] = {
                                'status': 'pending',
                                'activity_log': [],
                                'created_at': time.time(),
                            }

                        state['tasks'][task_id][key] = value
                        self._write_state_locked(f, state)
                        logger.debug(
                            "Task metric set",
                            extra={"task_id": task_id, "key": key},
                        )
                        return

                    finally:
                        self._release_lock(f.fileno())

            except TimeoutError:
                if attempt == self.lock_retry_attempts - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def rotate_activity_log(self, task_id: str) -> None:
        """
        Trim activity log when it exceeds ACTIVITY_LOG_MAX_ENTRIES.

        Oldest entries are discarded; a running count of discarded entries is
        preserved in ``archived_activity_count`` on the task entry. This keeps
        state files from growing unbounded (OBS-04).

        If the log is within the threshold this method returns immediately
        without acquiring any lock.

        Args:
            task_id: The task identifier
        """
        # Fast-path: read current log length from cache before acquiring any lock
        state = self.read_state()
        task = state.get('tasks', {}).get(task_id)
        if task is None:
            return
        activity_log = task.get('activity_log', [])
        if len(activity_log) <= ACTIVITY_LOG_MAX_ENTRIES:
            return  # Within threshold — no-op

        # Log exceeds threshold; acquire LOCK_EX and trim
        for attempt in range(self.lock_retry_attempts):
            try:
                with self.state_file.open('r+') as f:
                    self._acquire_lock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        state = self._read_state_locked(f)

                        if 'tasks' not in state or task_id not in state['tasks']:
                            return

                        log = state['tasks'][task_id].get('activity_log', [])
                        if len(log) <= ACTIVITY_LOG_MAX_ENTRIES:
                            # Another writer already trimmed between our check and lock
                            return

                        entries_to_archive = len(log) - ACTIVITY_LOG_MAX_ENTRIES
                        existing_archived = state['tasks'][task_id].get('archived_activity_count', 0)
                        state['tasks'][task_id]['archived_activity_count'] = existing_archived + entries_to_archive
                        state['tasks'][task_id]['activity_log'] = log[-ACTIVITY_LOG_MAX_ENTRIES:]

                        self._write_state_locked(f, state)
                        logger.info(
                            "Activity log rotated",
                            extra={
                                "task_id": task_id,
                                "entries_archived": entries_to_archive,
                                "remaining": ACTIVITY_LOG_MAX_ENTRIES,
                            },
                        )
                        return

                    finally:
                        self._release_lock(f.fileno())

            except TimeoutError:
                if attempt == self.lock_retry_attempts - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def list_active_tasks(self) -> List[str]:
        """
        Return task IDs with status not in ('completed', 'failed').

        Returns:
            List of active task IDs
        """
        state = self.read_state()
        tasks = state.get('tasks', {})
        terminal_states = {'completed', 'failed'}
        return [task_id for task_id, task in tasks.items() if task.get('status') not in terminal_states]

    def list_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Return all tasks.

        Returns:
            Dictionary mapping task_id to task data
        """
        state = self.read_state()
        return state.get('tasks', {})

    def get_memory_cursor(self, project_id: str) -> Optional[str]:
        """Return the ISO timestamp cursor for project_id, or None if not set.

        Reads from state.json under metadata.memory_cursors[project_id].
        Validates the value is a parseable ISO timestamp before returning.

        Returns None (not raises) on any read error — callers fall back to full fetch.
        Logs a warning when cursor is present but unparseable (corrupt cursor case).
        """
        try:
            state = self.read_state()
            cursors = state.get("metadata", {}).get("memory_cursors", {})
            value = cursors.get(project_id)
            if not isinstance(value, str) or not value:
                return None
            # Validate parseable as ISO datetime (import inside to avoid circular import risk)
            from datetime import datetime
            datetime.fromisoformat(value.rstrip("Z"))
            return value
        except Exception as exc:
            logger.warning(
                "Failed to read memory cursor — will do full fetch",
                extra={"project_id": project_id, "error": str(exc)},
            )
            return None

    def update_memory_cursor(self, project_id: str, iso_timestamp: str) -> None:
        """Persist the ISO timestamp cursor for project_id under metadata.memory_cursors.

        Uses LOCK_EX read-modify-write pattern (same as existing write methods).
        Creates metadata.memory_cursors dict if absent.

        Logs and swallows all exceptions — cursor write failure must never abort
        the spawn flow. Does NOT raise.
        """
        try:
            for attempt in range(self.lock_retry_attempts):
                try:
                    with self.state_file.open("r+") as f:
                        self._acquire_lock(f.fileno(), fcntl.LOCK_EX)
                        try:
                            state = self._read_state_locked(f)
                            if "metadata" not in state:
                                state["metadata"] = {}
                            if "memory_cursors" not in state["metadata"]:
                                state["metadata"]["memory_cursors"] = {}
                            state["metadata"]["memory_cursors"][project_id] = iso_timestamp
                            self._write_state_locked(f, state)
                            logger.debug(
                                "Memory cursor updated",
                                extra={"project_id": project_id, "cursor": iso_timestamp},
                            )
                            return
                        finally:
                            self._release_lock(f.fileno())
                except TimeoutError:
                    if attempt == self.lock_retry_attempts - 1:
                        raise
                    time.sleep(0.5 * (attempt + 1))
        except Exception as exc:
            logger.warning(
                "Failed to persist memory cursor — cursor lost for this spawn",
                extra={"project_id": project_id, "error": str(exc)},
            )
