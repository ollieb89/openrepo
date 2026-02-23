"""
Jarvis Protocol State Engine - Cross-container state synchronization with file locking.

This module provides thread-safe state management using fcntl file locking
to enable multiple L3 containers to safely read and write shared state.
"""

import fcntl
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import LOCK_TIMEOUT, LOCK_RETRY_ATTEMPTS


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
                    return True
                except BlockingIOError:
                    if time.time() - start_time > self.lock_timeout:
                        raise TimeoutError(f"Lock acquisition timeout after {self.lock_timeout}s")
                    time.sleep(0.1)
        else:
            try:
                fcntl.flock(fd, lock_type | fcntl.LOCK_NB)
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

    def _read_state_locked(self, f) -> Dict[str, Any]:
        """Read state from file inside a lock context."""
        f.seek(0)
        try:
            content = f.read()
            if not content:
                return {"version": "1.0.0", "protocol": "jarvis", "tasks": {}, "metadata": {}}
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Log error and reinitialize with empty state
            print(f"[JarvisState] Warning: Corrupt JSON, reinitializing: {e}")
            return {"version": "1.0.0", "protocol": "jarvis", "tasks": {}, "metadata": {}}

    def read_state(self) -> Dict[str, Any]:
        """
        Read current state with shared lock (LOCK_SH).

        Returns:
            Full state dictionary
        """
        self._ensure_state_file()

        with self.state_file.open('r+') as f:
            self._acquire_lock(f.fileno(), fcntl.LOCK_SH)
            try:
                return self._read_state_locked(f)
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
                                'activity_log': [],
                                'created_at': time.time()
                            }

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
                        return

                    finally:
                        self._release_lock(f.fileno())

            except TimeoutError:
                if attempt == self.lock_retry_attempts - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff

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
