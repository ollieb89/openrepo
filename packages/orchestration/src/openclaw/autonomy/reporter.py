"""
L3 self-reporting interface for autonomy state.

This module provides the interface for L3 agents to report their autonomy state,
including sentinel file I/O for distributed state tracking.
"""

import json
import os
from pathlib import Path
from typing import Optional

from .types import AutonomyContext, AutonomyState


SENTINEL_VERSION = "1.0"
SENTINEL_FILENAME = "autonomy-state.json"


class AutonomyReporter:
    """
    Handles reading and writing autonomy state for L3 self-reporting.
    
    This class manages the sentinel file format and provides methods for
    L3 agents to report their state and for the orchestrator to read it.
    
    Sentinel file format (JSON):
    {
        "version": "1.0",
        "timestamp": "2026-02-25T14:30:00",
        "task_id": "task-123",
        "state": "executing",
        "confidence_score": 0.75,
        "retry_count": 0,
        "escalation_reason": null,
        "updated_at": "2026-02-25T14:30:00"
    }
    """
    
    def __init__(self, workspace_state_dir: Path):
        """
        Initialize the reporter.
        
        Args:
            workspace_state_dir: Directory where jarvis-state.json is stored
        """
        self.workspace_state_dir = Path(workspace_state_dir)
    
    def _get_sentinel_path(self, task_id: str) -> Path:
        """Get the path to the sentinel file for a task."""
        return self.workspace_state_dir / f"{task_id}-{SENTINEL_FILENAME}"
    
    def write_state(self, context: AutonomyContext) -> Path:
        """
        Write the autonomy context to the sentinel file.
        
        Args:
            context: The autonomy context to write
            
        Returns:
            Path to the written sentinel file
        """
        sentinel_path = self._get_sentinel_path(context.task_id)
        
        data = {
            "version": SENTINEL_VERSION,
            "timestamp": context.updated_at.isoformat(),
            "task_id": context.task_id,
            "state": context.state.value,
            "confidence_score": context.confidence_score,
            "retry_count": context.retry_count,
            "escalation_reason": context.escalation_reason,
            "updated_at": context.updated_at.isoformat(),
        }
        
        sentinel_path.write_text(json.dumps(data, indent=2))
        return sentinel_path
    
    def read_state(self, task_id: str) -> Optional[AutonomyContext]:
        """
        Read the autonomy context from the sentinel file.
        
        Args:
            task_id: The task ID to read state for
            
        Returns:
            AutonomyContext if found, None otherwise
        """
        sentinel_path = self._get_sentinel_path(task_id)
        
        if not sentinel_path.exists():
            return None
        
        try:
            data = json.loads(sentinel_path.read_text())
            
            # Validate version
            version = data.get("version", "1.0")
            if version != SENTINEL_VERSION:
                # Handle version migrations here if needed
                pass
            
            # Convert sentinel format to AutonomyContext format
            # Sentinel uses 'timestamp' for both created and updated
            context_data = {
                "task_id": data["task_id"],
                "state": data["state"],
                "confidence_score": data["confidence_score"],
                "retry_count": data["retry_count"],
                "escalation_reason": data.get("escalation_reason"),
                "created_at": data.get("timestamp", data.get("updated_at")),
                "updated_at": data.get("updated_at", data.get("timestamp")),
                "transition_history": [],  # Sentinel format doesn't store history
            }
            
            return AutonomyContext.from_dict(context_data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def report_state(self, context: AutonomyContext) -> Path:
        """
        Report the current state by writing to the sentinel file.
        
        This is the main interface for L3 agents to report their state.
        
        Args:
            context: The current autonomy context
            
        Returns:
            Path to the written sentinel file
        """
        return self.write_state(context)
    
    def clear_state(self, task_id: str) -> bool:
        """
        Clear the sentinel file for a task (after completion or escalation).
        
        Args:
            task_id: The task ID to clear
            
        Returns:
            True if file was removed, False if it didn't exist
        """
        sentinel_path = self._get_sentinel_path(task_id)
        
        if sentinel_path.exists():
            sentinel_path.unlink()
            return True
        return False
    
    def list_active_tasks(self) -> list[str]:
        """
        List all task IDs with active sentinel files.
        
        Returns:
            List of task IDs
        """
        task_ids = []
        
        if not self.workspace_state_dir.exists():
            return task_ids
        
        for file_path in self.workspace_state_dir.glob(f"*-{SENTINEL_FILENAME}"):
            # Extract task_id from filename (task_id-autonomy-state.json)
            task_id = file_path.name.replace(f"-{SENTINEL_FILENAME}", "")
            task_ids.append(task_id)
        
        return task_ids


def get_reporter_for_task(task_id: str, workspace_root: Optional[Path] = None) -> AutonomyReporter:
    """
    Factory function to get an AutonomyReporter for a task.
    
    This helper determines the workspace state directory from the task context
    and returns a configured reporter.
    
    Args:
        task_id: The task ID
        workspace_root: Optional workspace root path (auto-detected if not provided)
        
    Returns:
        Configured AutonomyReporter
    """
    if workspace_root is None:
        # Auto-detect from environment or current directory
        # This would integrate with project_config.get_state_path() in practice
        from ..config import get_state_path
        state_path = Path(get_state_path())
        workspace_state_dir = state_path.parent
    else:
        workspace_state_dir = Path(workspace_root) / ".openclaw" / "state"
    
    return AutonomyReporter(workspace_state_dir)


__all__ = [
    "AutonomyReporter",
    "get_reporter_for_task",
    "SENTINEL_VERSION",
    "SENTINEL_FILENAME",
]
