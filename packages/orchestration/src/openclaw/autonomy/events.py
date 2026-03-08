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
    - project_id: Optional project identifier for dashboard routing
    - payload: Event-specific data as a dictionary
    """
    task_id: str
    timestamp: float = field(default_factory=time.time)
    project_id: Optional[str] = None
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
            "project_id": self.project_id,
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
            project_id=data.get("project_id"),
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
            project_id=data.get("project_id"),
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
            project_id=data.get("project_id"),
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
            project_id=data.get("project_id"),
            attempt_number=payload.get("attempt_number", 1),
            max_retries=payload.get("max_retries", 1),
            reason=payload.get("reason", ""),
        )


@dataclass
class AutonomyPlanGenerated(AutonomyEvent):
    """
    Event emitted when an L3 agent generates its execution plan.
    
    Attributes:
        plan: The generated plan as a dictionary/structure
    """
    plan: Dict[str, Any] = field(default_factory=dict)
    event_type: str = field(default="autonomy.plan_generated", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "plan": self.plan,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyPlanGenerated":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            project_id=data.get("project_id"),
            plan=payload.get("plan", {}),
        )


@dataclass
class AutonomyProgressUpdated(AutonomyEvent):
    """
    Event emitted when an L3 agent updates its progress on a planned step.
    
    Attributes:
        step_number: Current step number
        total_steps: Total steps in the plan
        status: Status of the step (e.g., "started", "completed", "failed")
        duration_seconds: Time taken so far
        output_snippet: Snippet of execution output
    """
    step_number: int = 1
    total_steps: int = 1
    status: str = "started"
    duration_seconds: float = 0.0
    output_snippet: str = ""
    event_type: str = field(default="autonomy.progress_updated", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "total_steps": self.total_steps,
            "status": self.status,
            "duration_seconds": self.duration_seconds,
            "output_snippet": self.output_snippet,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyProgressUpdated":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            project_id=data.get("project_id"),
            step_number=payload.get("step_number", 1),
            total_steps=payload.get("total_steps", 1),
            status=payload.get("status", "started"),
            duration_seconds=payload.get("duration_seconds", 0.0),
            output_snippet=payload.get("output_snippet", ""),
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
        
        try:
            # Convert to envelope dict and emit
            envelope = event.to_dict()
            event_bus.emit(envelope)
        except Exception:
            # Events should be fire-and-forget, don't block on bus failures
            pass
    
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
EVENT_PLAN_GENERATED = "autonomy.plan_generated"
EVENT_PROGRESS_UPDATED = "autonomy.progress_updated"
EVENT_TOOLS_SELECTED = "autonomy.tools_selected"
EVENT_COURSE_CORRECTION = "autonomy.course_correction"

@dataclass
class AutonomyToolsSelected(AutonomyEvent):
    task_id: str
    selected_tools: List[str] = field(default_factory=list)
    event_type: str = field(default="autonomy.tools_selected", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "selected_tools": self.selected_tools,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyToolsSelected":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            project_id=data.get("project_id"),
            selected_tools=payload.get("selected_tools", []),
        )

@dataclass
class AutonomyCourseCorrection(AutonomyEvent):
    task_id: str
    failed_step: Dict[str, Any] = field(default_factory=dict)
    recovery_steps: List[Dict[str, Any]] = field(default_factory=list)
    event_type: str = field(default="autonomy.course_correction", init=False)
    
    def to_payload(self) -> Dict[str, Any]:
        return {
            "failed_step": self.failed_step,
            "recovery_steps": self.recovery_steps,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutonomyCourseCorrection":
        payload = data.get("payload", {})
        return cls(
            task_id=data.get("task_id", ""),
            timestamp=data.get("timestamp", time.time()),
            project_id=data.get("project_id"),
            failed_step=payload.get("failed_step", {}),
            recovery_steps=payload.get("recovery_steps", []),
        )


__all__ = [
    # Event classes
    "AutonomyEvent",
    "AutonomyStateChanged",
    "AutonomyConfidenceUpdated",
    "AutonomyEscalationTriggered",
    "AutonomyRetryAttempted",
    "AutonomyPlanGenerated",
    "AutonomyProgressUpdated",
    "AutonomyToolsSelected",
    "AutonomyCourseCorrection",
    # Event bus
    "AutonomyEventBus",
    # Constants
    "EVENT_STATE_CHANGED",
    "EVENT_CONFIDENCE_UPDATED",
    "EVENT_ESCALATION_TRIGGERED",
    "EVENT_RETRY_ATTEMPTED",
    "EVENT_PLAN_GENERATED",
    "EVENT_PROGRESS_UPDATED",
    "EVENT_TOOLS_SELECTED",
    "EVENT_COURSE_CORRECTION",
]
