"""
Autonomy state machine implementation.

This module implements the state machine that manages autonomous task execution
with retry logic and escalation handling.
"""

from datetime import datetime
from typing import Optional

from .types import AutonomyContext, AutonomyState, StateTransition


class StateMachine:
    """
    Manages state transitions for autonomous task execution.
    
    Implements a 4-state model:
        PLANNING -> EXECUTING
        EXECUTING -> BLOCKED | COMPLETE
        BLOCKED -> EXECUTING (1 retry) | ESCALATING
        
    Terminal states: COMPLETE, ESCALATING
    
    Attributes:
        context: The AutonomyContext being managed
        max_retries: Maximum number of retry attempts from BLOCKED state (default 1)
    """
    
    def __init__(self, context: AutonomyContext, max_retries: int = 1):
        """
        Initialize the state machine.
        
        Args:
            context: The autonomy context to manage
            max_retries: Maximum retry attempts from BLOCKED (default 1)
        """
        self.context = context
        self.max_retries = max_retries
    
    @property
    def current_state(self) -> AutonomyState:
        """Return the current state."""
        return self.context.state
    
    def transition(self, new_state: AutonomyState, reason: str = "") -> None:
        """
        Transition to a new state.
        
        Args:
            new_state: The state to transition to
            reason: Reason for the transition
            
        Raises:
            ValueError: If the transition is invalid or from a terminal state
        """
        old_state = self.context.state
        
        # Check if current state is terminal
        if old_state.is_terminal():
            raise ValueError(
                f"Cannot transition from terminal state {old_state.value}"
            )
        
        # Validate transition
        if not old_state.can_transition_to(new_state):
            raise ValueError(
                f"Invalid transition: {old_state.value} -> {new_state.value}"
            )
        
        # Handle blocked retry logic
        if old_state == AutonomyState.BLOCKED and new_state == AutonomyState.EXECUTING:
            if self.context.retry_count >= self.max_retries:
                raise ValueError(
                    f"Maximum retries ({self.max_retries}) exceeded, "
                    f"must transition to ESCALATING"
                )
            self.context.retry_count += 1
        
        # Record the transition
        transition = StateTransition(
            from_state=old_state,
            to_state=new_state,
            timestamp=datetime.utcnow(),
            reason=reason,
        )
        self.context.transition_history.append(transition)
        
        # Update state
        self.context.state = new_state
        self.context.update_timestamp()
    
    def get_time_in_current_state(self) -> float:
        """
        Get the time (in seconds) spent in the current state.
        
        Returns:
            Seconds since entering the current state, or since context
            creation if no transitions have occurred.
        """
        if self.context.transition_history:
            last_transition = self.context.transition_history[-1]
            return (datetime.utcnow() - last_transition.timestamp).total_seconds()
        else:
            return (datetime.utcnow() - self.context.created_at).total_seconds()
    
    def handle_blocked(self, reason: str = "") -> None:
        """
        Handle the BLOCKED state with automatic retry or escalation logic.
        
        This method determines whether to retry (if under max_retries) or escalate.
        
        Args:
            reason: Reason for being blocked
        """
        if self.context.state != AutonomyState.BLOCKED:
            raise ValueError(
                f"handle_blocked() called from non-blocked state: {self.context.state.value}"
            )
        
        if self.context.retry_count < self.max_retries:
            # Retry - transition back to executing
            self.transition(AutonomyState.EXECUTING, f"Retry attempt {self.context.retry_count + 1}: {reason}")
        else:
            # Max retries reached - escalate
            self.context.escalation_reason = reason
            self.transition(AutonomyState.ESCALATING, f"Max retries exceeded, escalating: {reason}")
    
    def is_complete(self) -> bool:
        """Return True if the task has reached a terminal state."""
        return self.context.state.is_terminal()
    
    def can_retry(self) -> bool:
        """Return True if a retry is available from the current BLOCKED state."""
        return (
            self.context.state == AutonomyState.BLOCKED
            and self.context.retry_count < self.max_retries
        )


__all__ = ["StateMachine"]
