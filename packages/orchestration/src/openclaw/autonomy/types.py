"""
Autonomy framework type definitions.

This module defines the core types and enums for the agent autonomy system,
including the state machine states and transition rules.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


class AutonomyState(Enum):
    """
    States in the agent autonomy lifecycle.
    
    State machine:
        PLANNING -> EXECUTING
        EXECUTING -> BLOCKED | COMPLETE
        BLOCKED -> EXECUTING (retry 1) | ESCALATING
        
    Terminal states: COMPLETE, ESCALATING
    """
    PLANNING = "planning"
    EXECUTING = "executing"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    ESCALATING = "escalating"
    
    def is_terminal(self) -> bool:
        """Return True if this is a terminal state."""
        return self in (AutonomyState.COMPLETE, AutonomyState.ESCALATING)
    
    def can_transition_to(self, new_state: "AutonomyState") -> bool:
        """
        Check if a transition from this state to new_state is valid.
        
        Valid transitions:
        - PLANNING -> EXECUTING
        - EXECUTING -> BLOCKED, COMPLETE
        - BLOCKED -> EXECUTING, ESCALATING
        - (No valid transitions from terminal states)
        """
        valid_transitions = {
            AutonomyState.PLANNING: {AutonomyState.EXECUTING},
            AutonomyState.EXECUTING: {AutonomyState.BLOCKED, AutonomyState.COMPLETE},
            AutonomyState.BLOCKED: {AutonomyState.EXECUTING, AutonomyState.ESCALATING},
            AutonomyState.COMPLETE: set(),  # Terminal
            AutonomyState.ESCALATING: set(),  # Terminal
        }
        return new_state in valid_transitions.get(self, set())


@dataclass
class StateTransition:
    """Record of a state transition."""
    from_state: AutonomyState
    to_state: AutonomyState
    timestamp: datetime
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateTransition":
        """Create from dictionary."""
        return cls(
            from_state=AutonomyState(data["from_state"]),
            to_state=AutonomyState(data["to_state"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            reason=data["reason"],
        )


@dataclass
class AutonomyContext:
    """
    Context for an autonomous task execution.
    
    Tracks the state, confidence, retry attempts, and escalation
    information for a single L3 task.
    """
    task_id: str
    state: AutonomyState = AutonomyState.PLANNING
    confidence_score: float = 0.0
    retry_count: int = 0
    escalation_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    transition_history: List[StateTransition] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate field constraints."""
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")
        if self.retry_count < 0:
            raise ValueError(f"retry_count cannot be negative, got {self.retry_count}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "confidence_score": self.confidence_score,
            "retry_count": self.retry_count,
            "escalation_reason": self.escalation_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "transition_history": [t.to_dict() for t in self.transition_history],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyContext":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            state=AutonomyState(data["state"]),
            confidence_score=data["confidence_score"],
            retry_count=data["retry_count"],
            escalation_reason=data.get("escalation_reason"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            transition_history=[
                StateTransition.from_dict(t) for t in data.get("transition_history", [])
            ],
        )
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


__all__ = [
    "AutonomyState",
    "StateTransition", 
    "AutonomyContext",
]
