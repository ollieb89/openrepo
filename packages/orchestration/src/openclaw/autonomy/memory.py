"""
memU persistence integration for autonomy contexts.

This module provides the AutonomyMemoryStore class for persisting and
retrieving autonomy contexts from memU. Contexts are stored with metadata
for querying and archived when tasks complete or fail.

The memory category "AUTONOMY_STATE" is used for all autonomy context
storage, enabling targeted retrieval and analysis of task execution history.

Example:
    from openclaw.autonomy.memory import AutonomyMemoryStore
    from openclaw.autonomy.types import AutonomyContext
    
    # Save a context
    context = AutonomyContext(task_id="task-123")
    AutonomyMemoryStore.save_context(context, project="myapp")
    
    # Load a context
    context = AutonomyMemoryStore.load_context("task-123")
    
    # Archive completed context
    AutonomyMemoryStore.archive_context(context, project="myapp")
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from .types import AutonomyContext

logger = logging.getLogger("openclaw.autonomy.memory")

# Memory category for autonomy state storage
MEMORY_CATEGORY = "AUTONOMY_STATE"

# Metadata keys for querying
META_TASK_ID = "task_id"
META_PROJECT = "project"
META_STATE = "state"
META_TIMESTAMP = "timestamp"
META_ARCHIVED = "archived"


class AutonomyMemoryStore:
    """
    Persistence layer for autonomy contexts using memU.
    
    Provides methods to save, load, and archive AutonomyContext objects
    to/from memU with proper metadata for querying. Contexts are stored
    as JSON with metadata for filtering by task_id, project, state, etc.
    
    The store gracefully handles memU unavailability by logging warnings
    but never raising exceptions that would break task execution.
    
    Example:
        # Save current context
        AutonomyMemoryStore.save_context(context, project="myapp")
        
        # Load by task_id
        context = AutonomyMemoryStore.load_context("task-123")
        
        # Query by project and state
        contexts = AutonomyMemoryStore.query(
            project="myapp",
            state="complete"
        )
        
        # Archive completed task
        AutonomyMemoryStore.archive_context(context, project="myapp")
    """
    
    @classmethod
    def save_context(
        cls,
        context: AutonomyContext,
        project: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Save an autonomy context to memU.
        
        The context is serialized to JSON and stored with metadata for
        querying. Overwrites any existing context for the same task_id.
        
        Args:
            context: The autonomy context to save
            project: Project identifier for namespacing
            metadata: Additional metadata to store
            
        Returns:
            True if saved successfully, False otherwise
            
        Example:
            context = AutonomyContext(task_id="task-123", state=AutonomyState.EXECUTING)
            success = AutonomyMemoryStore.save_context(context, project="myapp")
        """
        try:
            # Serialize context to JSON
            context_data = context.to_dict()
            content = json.dumps(context_data, indent=2)
            
            # Build metadata
            meta = {
                META_TASK_ID: context.task_id,
                META_STATE: context.state.value,
                META_TIMESTAMP: datetime.utcnow().isoformat(),
                META_ARCHIVED: False,
            }
            if project:
                meta[META_PROJECT] = project
            if metadata:
                meta.update(metadata)
            
            # Store in memU
            cls._memorize(content, meta)
            
            logger.debug(f"Saved autonomy context for task {context.task_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to save autonomy context: {e}")
            return False
    
    @classmethod
    def load_context(cls, task_id: str) -> Optional[AutonomyContext]:
        """
        Load an autonomy context from memU by task_id.
        
        Retrieves the most recent non-archived context for the task.
        
        Args:
            task_id: The task identifier
            
        Returns:
            AutonomyContext if found, None otherwise
            
        Example:
            context = AutonomyMemoryStore.load_context("task-123")
            if context:
                print(f"State: {context.state.value}")
        """
        try:
            # Query by task_id, prefer non-archived
            results = cls._retrieve(
                category=MEMORY_CATEGORY,
                meta_filters={META_TASK_ID: task_id},
                limit=10,
            )
            
            if not results:
                return None
            
            # Find first non-archived result, or fall back to most recent
            for result in results:
                meta = result.get("metadata", {})
                if not meta.get(META_ARCHIVED, False):
                    return cls._parse_context(result)
            
            # All archived, return most recent
            return cls._parse_context(results[0])
            
        except Exception as e:
            logger.warning(f"Failed to load autonomy context: {e}")
            return None
    
    @classmethod
    def archive_context(
        cls,
        context: AutonomyContext,
        project: Optional[str] = None,
        archive_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Archive a completed or escalated autonomy context.
        
        Archived contexts are marked and can be filtered in queries.
        This should be called when a task reaches a terminal state.
        
        Args:
            context: The autonomy context to archive
            project: Project identifier
            archive_metadata: Additional metadata for the archive record
            
        Returns:
            True if archived successfully, False otherwise
            
        Example:
            # Archive on task completion
            AutonomyMemoryStore.archive_context(
                context,
                project="myapp",
                archive_metadata={"completion_status": "success"}
            )
        """
        try:
            # Serialize context
            context_data = context.to_dict()
            content = json.dumps(context_data, indent=2)
            
            # Build archive metadata
            meta = {
                META_TASK_ID: context.task_id,
                META_STATE: context.state.value,
                META_TIMESTAMP: datetime.utcnow().isoformat(),
                META_ARCHIVED: True,
            }
            if project:
                meta[META_PROJECT] = project
            if archive_metadata:
                meta.update(archive_metadata)
            
            # Store in memU
            cls._memorize(content, meta)
            
            logger.info(f"Archived autonomy context for task {context.task_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to archive autonomy context: {e}")
            return False
    
    @classmethod
    def query(
        cls,
        project: Optional[str] = None,
        state: Optional[str] = None,
        archived: Optional[bool] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AutonomyContext]:
        """
        Query autonomy contexts by metadata filters.
        
        Args:
            project: Filter by project
            state: Filter by state value (e.g., "complete", "executing")
            archived: Filter by archived status (None = both)
            since: Only results after this datetime
            limit: Maximum results to return
            
        Returns:
            List of matching AutonomyContext objects
            
        Example:
            # Get all completed tasks for a project
            completed = AutonomyMemoryStore.query(
                project="myapp",
                state="complete",
                archived=True,
            )
        """
        try:
            # Build metadata filters
            meta_filters: Dict[str, Any] = {}
            if project:
                meta_filters[META_PROJECT] = project
            if state:
                meta_filters[META_STATE] = state
            if archived is not None:
                meta_filters[META_ARCHIVED] = archived
            
            # Query memU
            results = cls._retrieve(
                category=MEMORY_CATEGORY,
                meta_filters=meta_filters if meta_filters else None,
                limit=limit,
            )
            
            # Filter by timestamp if needed
            contexts = []
            for result in results:
                meta = result.get("metadata", {})
                if since:
                    ts_str = meta.get(META_TIMESTAMP)
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str)
                        if ts < since:
                            continue
                
                context = cls._parse_context(result)
                if context:
                    contexts.append(context)
            
            return contexts
            
        except Exception as e:
            logger.warning(f"Failed to query autonomy contexts: {e}")
            return []
    
    @classmethod
    def _memorize(cls, content: str, metadata: Dict[str, Any]) -> None:
        """
        Internal: Store content in memU.
        
        Args:
            content: JSON string to store
            metadata: Metadata dict
        """
        # Import here to avoid circular imports at module level
        try:
            from openclaw.memorize import memorize
            memorize(
                content=content,
                category=MEMORY_CATEGORY,
                metadata=metadata,
            )
        except ImportError:
            # memU not available - log but don't fail
            logger.debug(f"memU not available, context not persisted: {metadata.get(META_TASK_ID)}")
            raise RuntimeError("memU not available")
    
    @classmethod
    def _retrieve(
        cls,
        category: str,
        meta_filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Internal: Retrieve content from memU.
        
        Args:
            category: Memory category
            meta_filters: Metadata filters
            limit: Maximum results
            
        Returns:
            List of result dicts with 'content' and 'metadata' keys
        """
        try:
            from openclaw.memorize import retrieve
            results = retrieve(
                category=category,
                meta_filters=meta_filters,
                limit=limit,
            )
            return results
        except ImportError:
            logger.debug("memU not available, cannot retrieve contexts")
            return []
    
    @classmethod
    def _parse_context(cls, result: Dict[str, Any]) -> Optional[AutonomyContext]:
        """
        Internal: Parse a memU result into AutonomyContext.
        
        Args:
            result: memU result dict with 'content' and 'metadata'
            
        Returns:
            AutonomyContext or None if parsing fails
        """
        try:
            content = result.get("content", "")
            if not content:
                return None
            
            data = json.loads(content)
            return AutonomyContext.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to parse autonomy context: {e}")
            return None
    
    @classmethod
    def get_task_history(cls, task_id: str) -> List[Dict[str, Any]]:
        """
        Get the full history of a task's context changes.
        
        Retrieves all stored versions of a task's context, useful for
        debugging or analyzing task evolution over time.
        
        Args:
            task_id: The task identifier
            
        Returns:
            List of dicts with 'context', 'metadata', and 'timestamp'
            
        Example:
            history = AutonomyMemoryStore.get_task_history("task-123")
            for entry in history:
                print(f"{entry['timestamp']}: {entry['context'].state.value}")
        """
        try:
            results = cls._retrieve(
                category=MEMORY_CATEGORY,
                meta_filters={META_TASK_ID: task_id},
                limit=1000,  # Get all history
            )
            
            history = []
            for result in results:
                context = cls._parse_context(result)
                if context:
                    history.append({
                        "context": context,
                        "metadata": result.get("metadata", {}),
                        "timestamp": result.get("metadata", {}).get(META_TIMESTAMP),
                    })
            
            # Sort by timestamp
            history.sort(key=lambda x: x["timestamp"] or "")
            return history
            
        except Exception as e:
            logger.warning(f"Failed to get task history: {e}")
            return []


__all__ = [
    "AutonomyMemoryStore",
    "MEMORY_CATEGORY",
    "META_TASK_ID",
    "META_PROJECT",
    "META_STATE",
    "META_TIMESTAMP",
    "META_ARCHIVED",
]
