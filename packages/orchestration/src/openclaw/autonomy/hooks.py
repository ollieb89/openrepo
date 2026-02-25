"""
Spawn flow hooks for autonomy integration.

This module provides hooks that integrate the autonomy framework into the
task spawn/execute flow. Hooks are called at key lifecycle points to create
and manage autonomy contexts for tasks.

Example:
    from openclaw.autonomy.hooks import on_task_spawn, get_autonomy_context
    
    # Called when spawning a new task
    context = on_task_spawn("task-123", task_spec)
    
    # Later, retrieve the context
    context = get_autonomy_context("task-123")
"""

import logging
from typing import Dict, Any, Optional

from .types import AutonomyContext, AutonomyState
from .state import StateMachine
from .events import (
    AutonomyEventBus,
    AutonomyStateChanged,
    EVENT_STATE_CHANGED,
)

logger = logging.getLogger("openclaw.autonomy.hooks")

# In-memory store of autonomy contexts by task_id
# In production, contexts are persisted to memU via AutonomyMemoryStore
_context_store: Dict[str, AutonomyContext] = {}

# Track state machines per task
_state_machines: Dict[str, StateMachine] = {}


def on_task_spawn(task_id: str, task_spec: Dict[str, Any]) -> AutonomyContext:
    """
    Hook called when a task is spawned.
    
    Creates an initial autonomy context with PLANNING state and emits a
    state change event. This hook should be called before the container
    starts executing.
    
    Args:
        task_id: Unique identifier for the task
        task_spec: Task specification dictionary containing task details
        
    Returns:
        AutonomyContext: The created context for the task
        
    Example:
        context = on_task_spawn("task-123", {
            "description": "Implement feature X",
            "project": "myapp",
            "estimated_hours": 4.0,
        })
    """
    # Create initial context in PLANNING state
    context = AutonomyContext(
        task_id=task_id,
        state=AutonomyState.PLANNING,
        confidence_score=0.0,  # Will be updated by confidence scorer
    )
    
    # Store context
    _context_store[task_id] = context
    
    # Create state machine for this task
    max_retries = task_spec.get("max_retries", 1)
    _state_machines[task_id] = StateMachine(context, max_retries=max_retries)
    
    # Emit state change event (initial state)
    AutonomyEventBus.emit(AutonomyStateChanged(
        task_id=task_id,
        old_state="",
        new_state=AutonomyState.PLANNING.value,
        reason="Task spawned, entering planning phase",
    ))
    
    logger.info(f"Created autonomy context for task {task_id} in PLANNING state")
    
    return context


def get_autonomy_context(task_id: str) -> Optional[AutonomyContext]:
    """
    Retrieve the autonomy context for a task.
    
    Args:
        task_id: The task identifier
        
    Returns:
        AutonomyContext if found, None otherwise
        
    Example:
        context = get_autonomy_context("task-123")
        if context:
            print(f"Current state: {context.state.value}")
    """
    return _context_store.get(task_id)


def get_state_machine(task_id: str) -> Optional[StateMachine]:
    """
    Retrieve the state machine for a task.
    
    Args:
        task_id: The task identifier
        
    Returns:
        StateMachine if found, None otherwise
    """
    return _state_machines.get(task_id)


def on_container_healthy(task_id: str) -> None:
    """
    Hook called when a task's container becomes healthy.
    
    Transitions the autonomy context from PLANNING to EXECUTING state
    and emits a state change event.
    
    Args:
        task_id: The task identifier
        
    Raises:
        ValueError: If no context exists for the task
        
    Example:
        # Called by container health check
        on_container_healthy("task-123")
    """
    context = _context_store.get(task_id)
    if not context:
        raise ValueError(f"No autonomy context found for task {task_id}")
    
    state_machine = _state_machines.get(task_id)
    if not state_machine:
        raise ValueError(f"No state machine found for task {task_id}")
    
    old_state = context.state.value
    
    # Transition to EXECUTING state
    state_machine.transition(
        AutonomyState.EXECUTING,
        reason="Container healthy, beginning execution"
    )
    
    # Emit state change event
    AutonomyEventBus.emit(AutonomyStateChanged(
        task_id=task_id,
        old_state=old_state,
        new_state=AutonomyState.EXECUTING.value,
        reason="Container healthy, beginning execution",
    ))
    
    logger.info(f"Task {task_id} transitioned to EXECUTING state")


def on_task_complete(task_id: str, result: Dict[str, Any]) -> None:
    """
    Hook called when a task completes successfully.
    
    Transitions the autonomy context to COMPLETE state and emits events.
    
    Args:
        task_id: The task identifier
        result: Task result dictionary with output data
        
    Raises:
        ValueError: If no context exists for the task
        
    Example:
        on_task_complete("task-123", {
            "status": "success",
            "output": "Task completed successfully",
        })
    """
    context = _context_store.get(task_id)
    if not context:
        raise ValueError(f"No autonomy context found for task {task_id}")
    
    state_machine = _state_machines.get(task_id)
    if not state_machine:
        raise ValueError(f"No state machine found for task {task_id}")
    
    old_state = context.state.value
    
    # Transition to COMPLETE state
    state_machine.transition(
        AutonomyState.COMPLETE,
        reason=f"Task completed successfully: {result.get('status', 'success')}"
    )
    
    # Emit state change event
    AutonomyEventBus.emit(AutonomyStateChanged(
        task_id=task_id,
        old_state=old_state,
        new_state=AutonomyState.COMPLETE.value,
        reason="Task completed successfully",
    ))
    
    logger.info(f"Task {task_id} completed with state COMPLETE")


def on_task_failed(task_id: str, error: str) -> None:
    """
    Hook called when a task fails.
    
    Handles failure by either transitioning to BLOCKED (for retry) or
    ESCALATING (if max retries exceeded). Emits appropriate events.
    
    Args:
        task_id: The task identifier
        error: Error message describing the failure
        
    Raises:
        ValueError: If no context exists for the task
        
    Example:
        on_task_failed("task-123", "Container exited with code 1")
    """
    context = _context_store.get(task_id)
    if not context:
        raise ValueError(f"No autonomy context found for task {task_id}")
    
    state_machine = _state_machines.get(task_id)
    if not state_machine:
        raise ValueError(f"No state machine found for task {task_id}")
    
    old_state = context.state.value
    
    # Always transition to BLOCKED on failure
    state_machine.transition(
        AutonomyState.BLOCKED,
        reason=f"Task failed: {error}"
    )
    
    # Emit state change event for BLOCKED
    AutonomyEventBus.emit(AutonomyStateChanged(
        task_id=task_id,
        old_state=old_state,
        new_state=AutonomyState.BLOCKED.value,
        reason=f"Task failed, entering blocked state: {error}",
    ))
    
    # Let the state machine handle retry vs escalation
    # It will transition to either EXECUTING or ESCALATING
    state_machine.handle_blocked(reason=error)
    
    # Check what state we ended up in
    new_state = context.state
    if new_state == AutonomyState.EXECUTING:
        logger.info(f"Task {task_id} failed, retry attempt {context.retry_count}")
        # Emit state change event for retry
        AutonomyEventBus.emit(AutonomyStateChanged(
            task_id=task_id,
            old_state=AutonomyState.BLOCKED.value,
            new_state=AutonomyState.EXECUTING.value,
            reason=f"Retry attempt {context.retry_count}: {error}",
        ))
        
        # Emit retry attempted event
        from .events import AutonomyRetryAttempted
        AutonomyEventBus.emit(AutonomyRetryAttempted(
            task_id=task_id,
            attempt_number=context.retry_count,
            max_retries=state_machine.max_retries,
            reason=error,
        ))
    elif new_state == AutonomyState.ESCALATING:
        logger.warning(f"Task {task_id} escalated after max retries: {error}")
        # Emit state change event for escalation
        AutonomyEventBus.emit(AutonomyStateChanged(
            task_id=task_id,
            old_state=AutonomyState.BLOCKED.value,
            new_state=AutonomyState.ESCALATING.value,
            reason=f"Max retries exceeded, escalating: {error}",
        ))
        
        # Emit escalation triggered event
        from .events import AutonomyEscalationTriggered
        AutonomyEventBus.emit(AutonomyEscalationTriggered(
            task_id=task_id,
            reason=error,
            confidence=context.confidence_score,
        ))


def on_task_removed(task_id: str, archive: bool = True) -> Optional[AutonomyContext]:
    """
    Hook called when a task is removed from the pool.
    
    Optionally archives the autonomy context to memU before removal.
    
    Args:
        task_id: The task identifier
        archive: If True, archive context to memU before removal
        
    Returns:
        The removed context, or None if not found
        
    Example:
        # Clean up task and archive its context
        context = on_task_removed("task-123", archive=True)
    """
    context = _context_store.pop(task_id, None)
    _state_machines.pop(task_id, None)
    
    if context and archive:
        # Archive to memU via AutonomyMemoryStore
        try:
            from .memory import AutonomyMemoryStore
            AutonomyMemoryStore.archive_context(context)
            logger.info(f"Archived autonomy context for task {task_id}")
        except Exception as e:
            logger.warning(f"Failed to archive context for task {task_id}: {e}")
    
    # Clear any buffered confidence updates
    AutonomyEventBus.clear_buffer(task_id)
    
    logger.info(f"Removed autonomy context for task {task_id}")
    
    return context


def update_confidence(task_id: str, score: float, factors: Dict[str, float]) -> None:
    """
    Update the confidence score for a task.
    
    Emits a confidence updated event (with debouncing).
    
    Args:
        task_id: The task identifier
        score: New confidence score (0.0-1.0)
        factors: Dictionary of factor names to values
        
    Raises:
        ValueError: If no context exists for the task
        
    Example:
        update_confidence("task-123", 0.85, {
            "complexity": 0.3,
            "ambiguity": 0.2,
            "past_success": 0.9,
            "time_estimate": 0.8,
        })
    """
    context = _context_store.get(task_id)
    if not context:
        raise ValueError(f"No autonomy context found for task {task_id}")
    
    # Update context
    context.confidence_score = score
    context.update_timestamp()
    
    # Emit event (debounced)
    from .events import AutonomyConfidenceUpdated
    AutonomyEventBus.emit(AutonomyConfidenceUpdated(
        task_id=task_id,
        score=score,
        factors=factors,
    ))


def list_active_contexts() -> Dict[str, AutonomyContext]:
    """
    Get all active autonomy contexts.
    
    Returns:
        Dictionary mapping task_id to AutonomyContext
        
    Example:
        contexts = list_active_contexts()
        for task_id, context in contexts.items():
            print(f"{task_id}: {context.state.value}")
    """
    return dict(_context_store)


__all__ = [
    "on_task_spawn",
    "get_autonomy_context",
    "get_state_machine",
    "on_container_healthy",
    "on_task_complete",
    "on_task_failed",
    "on_task_removed",
    "update_confidence",
    "list_active_contexts",
]
