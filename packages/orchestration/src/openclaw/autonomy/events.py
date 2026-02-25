"""
Autonomy event types for the OpenClaw event bus.

This module defines the event types used by the autonomy framework for
decoupled communication between components. Events are emitted when autonomy
state changes, confidence updates, escalations occur, and retry attempts happen.

Example:
    from openclaw.autonomy.events import AutonomyStateChanged, AutonomyEventBus
    
    # Emit a state change event
    event = AutonomyStateChanged(
        task_id="task-123",
        old_state="planning",
        new_state="executing",
        reason="Container healthy, starting work"
    )
    AutonomyEventBus.emit(event)
"""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime


@dataclass
class AutonomyEvent(ABC):
    """
    Base class for all autonomy events.
    
    All autonomy events must have:
    - event_type: String identifier for the event type
    - task_id: The task this event relates to
    - timestamp: Unix timestamp of when the event occurred
    - payload: Event-specific data as a dictionary
    """
    task_id: str
    timestamp: float = field(default_factory=time.time)
    event_type: str = field(default="autonomy.base", init=False)
    
    @abstractmethod
    def to_payload(self) -> Dict[str, Any]:
        """Convert event-specific data to a dictionary payload."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert full event to dictionary for serialization."""
        return {
            "event_type": self.event_type,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "payload": self.to_payload(),
        }
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyEvent":
        """Create event from dictionary - subclasses should override."""
        raise NotImplementedError("Subclasses must implement from_dict")


@dataclass
class AutonomyStateChanged(AutonomyEvent):
    """
    Event emitted when an autonomy state transition occurs.
    
    Attributes:
        old_state: Previous state (e.g., "planning", "executing")
        new_state: New state after transition
        reason: Human-readable reason for the transition
    """
    old_state: str = ""
    new_state: str = ""
    reason: str = ""
    event_type: str = field(default="autonomy.state_changed", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "old_state": self.old_state,
            "new_state": self.new_state,
            "reason": self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyStateChanged":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            old_state=payload.get("old_state", ""),
            new_state=payload.get("new_state", ""),
            reason=payload.get("reason", ""),
        )


@dataclass
class AutonomyConfidenceUpdated(AutonomyEvent):
    """
    Event emitted when confidence score is updated.
    
    Attributes:
        score: New confidence score (0.0-1.0)
        factors: Dictionary of factor names to their values
    """
    score: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    event_type: str = field(default="autonomy.confidence_updated", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "factors": self.factors,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyConfidenceUpdated":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            score=payload.get("score", 0.0),
            factors=payload.get("factors", {}),
        )


@dataclass
class AutonomyEscalationTriggered(AutonomyEvent):
    """
    Event emitted when a task is escalated to human oversight.
    
    Attributes:
        reason: Why the task was escalated
        confidence: Confidence score at time of escalation
    """
    reason: str = ""
    confidence: float = 0.0
    event_type: str = field(default="autonomy.escalation_triggered", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "reason": self.reason,
            "confidence": self.confidence,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyEscalationTriggered":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            reason=payload.get("reason", ""),
            confidence=payload.get("confidence", 0.0),
        )


@dataclass
class AutonomyRetryAttempted(AutonomyEvent):
    """
    Event emitted when a retry is attempted from BLOCKED state.
    
    Attributes:
        attempt_number: Current retry attempt (1-based)
        max_retries: Maximum allowed retries
        reason: Why the retry was triggered
    """
    attempt_number: int = 1
    max_retries: int = 1
    reason: str = ""
    event_type: str = field(default="autonomy.retry_attempted", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "attempt_number": self.attempt_number,
            "max_retries": self.max_retries,
            "reason": self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyRetryAttempted":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            attempt_number=payload.get("attempt_number", 1),
            max_retries=payload.get("max_retries", 1),
            reason=payload.get("reason", ""),
        )


class AutonomyEventBus:
    """
    Event bus wrapper for autonomy events.
    
    Provides a clean interface for emitting and subscribing to autonomy events
    while wrapping the underlying event bus. Includes buffering for high-frequency
    events like confidence updates.
    
    Example:
        # Subscribe to state changes
        def on_state_change(event: Dict[str, Any]):
            print(f"State changed: {event}")
        
        AutonomyEventBus.subscribe("autonomy.state_changed", on_state_change)
        
        # Emit an event
        event = AutonomyStateChanged(
            task_id="task-123",
            old_state="planning",
            new_state="executing",
            reason="Starting work"
        )
        AutonomyEventBus.emit(event)
    """
    
    # Debounce buffer for confidence updates: task_id -> (last_emit_time, last_score)
    _confidence_buffer: Dict[str, tuple] = {}
    
    # Debounce interval in seconds for confidence updates
    CONFIDENCE_DEBOUNCE_SECONDS = 5.0
    
    @classmethod
    def emit(cls, event: AutonomyEvent) -> None:
        """
        Emit an autonomy event to the event bus.
        
        Events are fire-and-forget - this method returns immediately and
        handlers execute in daemon threads. For confidence updates, applies
        debouncing to avoid flooding the bus with high-frequency changes.
        
        Args:
            event: The autonomy event to emit
        """
        # Debounce confidence updates
        if isinstance(event, AutonomyConfidenceUpdated):
            if not cls._should_emit_confidence(event):
                return
        
        # Import here to avoid circular imports at module level
        from openclaw import event_bus
        
        # Convert to envelope dict and emit
        envelope = event.to_dict()
        event_bus.emit(envelope)
    
    @classmethod
    def _should_emit_confidence(cls, event: AutonomyConfidenceUpdated) -> bool:
        """
        Determine if a confidence update should be emitted (debouncing).
        
        Allows emission if:
        - No previous confidence update for this task
        - Previous update was > CONFIDENCE_DEBOUNCE_SECONDS ago
        - Score changed by > 0.1 (significant change)
        
        Args:
            event: The confidence update event
            
        Returns:
            True if the event should be emitted
        """
        now = time.time()
        buffered = cls._confidence_buffer.get(event.task_id)
        
        if buffered is None:
            # First confidence update for this task
            cls._confidence_buffer[event.task_id] = (now, event.score)
            return True
        
        last_time, last_score = buffered
        time_delta = now - last_time
        score_delta = abs(event.score - last_score)
        
        # Emit if enough time passed or significant score change
        if time_delta >= cls.CONFIDENCE_DEBOUNCE_SECONDS or score_delta > 0.1:
            cls._confidence_buffer[event.task_id] = (now, event.score)
            return True
        
        return False
    
    @classmethod
    def subscribe(cls, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Subscribe to a specific autonomy event type.
        
        Args:
            event_type: Event type string (e.g., "autonomy.state_changed")
            handler: Callable that receives the event envelope dict
        """
        from openclaw import event_bus
        event_bus.subscribe(event_type, handler)
    
    @classmethod
    def clear_buffer(cls, task_id: Optional[str] = None) -> None:
        """
        Clear the confidence update buffer.
        
        Args:
            task_id: Specific task to clear, or None to clear all
        """
        if task_id is None:
            cls._confidence_buffer.clear()
        else:
            cls._confidence_buffer.pop(task_id, None)


# Event type constants for subscription
EVENT_STATE_CHANGED = "autonomy.state_changed"
EVENT_CONFIDENCE_UPDATED = "autonomy.confidence_updated"
EVENT_ESCALATION_TRIGGERED = "autonomy.escalation_triggered"
EVENT_RETRY_ATTEMPTED = "autonomy.retry_attempted"


__all__ = [
    # Event classes
    "AutonomyEvent",
    "AutonomyStateChanged",
    "AutonomyConfidenceUpdated",
    "AutonomyEscalationTriggered",
    "AutonomyRetryAttempted",
    # Event bus
    "AutonomyEventBus",
    # Constants
    "EVENT_STATE_CHANGED",
    "EVENT_CONFIDENCE_UPDATED",
    "EVENT_ESCALATION_TRIGGERED",
    "EVENT_RETRY_ATTEMPTED",
]
