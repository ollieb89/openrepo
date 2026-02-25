"""
Autonomy Framework for OpenClaw

This package provides the foundational architecture for agent autonomy,
enabling L3 agents to self-direct their work with confidence-based
decision making and state tracking.

Example:
    from openclaw.autonomy import AutonomyState, AutonomyContext, StateMachine
    
    # Create context for a task
    context = AutonomyContext(
        task_id="task-123",
        state=AutonomyState.PLANNING,
        confidence_score=0.8
    )
    
    # Create state machine and transition
    sm = StateMachine(context)
    sm.transition(AutonomyState.EXECUTING, "Starting work")
"""

from .types import AutonomyState, AutonomyContext, StateTransition
from .state import StateMachine
from .reporter import AutonomyReporter, get_reporter_for_task

__all__ = [
    # Types
    "AutonomyState",
    "AutonomyContext",
    "StateTransition",
    # State machine
    "StateMachine",
    # Reporting
    "AutonomyReporter",
    "get_reporter_for_task",
]
