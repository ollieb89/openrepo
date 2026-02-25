"""
Test fixtures for autonomy framework tests.

Provides mock implementations and fixtures for testing the autonomy
framework without requiring full infrastructure (memU, event bus, etc.).
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional

from openclaw.autonomy.types import AutonomyContext, AutonomyState, StateTransition
from openclaw.autonomy.state import StateMachine


class MockMemUStore:
    """Mock memU store for testing."""
    
    def __init__(self):
        self._storage: Dict[str, List[Dict[str, Any]]] = {}
    
    def memorize(self, content: str, category: str, metadata: Dict[str, Any]) -> None:
        """Store content in mock storage."""
        if category not in self._storage:
            self._storage[category] = []
        
        self._storage[category].append({
            "content": content,
            "metadata": metadata,
        })
    
    def retrieve(
        self,
        category: str,
        meta_filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve content from mock storage."""
        items = self._storage.get(category, [])
        
        if meta_filters:
            filtered = []
            for item in items:
                meta = item.get("metadata", {})
                matches = all(
                    meta.get(key) == value
                    for key, value in meta_filters.items()
                )
                if matches:
                    filtered.append(item)
            items = filtered
        
        return items[:limit]
    
    def clear(self):
        """Clear all storage."""
        self._storage.clear()


class MockEventBus:
    """Mock event bus for testing."""
    
    def __init__(self):
        self._handlers: Dict[str, List] = {}
        self._events: List[Dict[str, Any]] = []
    
    def subscribe(self, event_type: str, handler) -> None:
        """Subscribe to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def emit(self, envelope: Dict[str, Any]) -> None:
        """Emit an event."""
        self._events.append(envelope)
        
        event_type = envelope.get("event_type", "")
        handlers = self._handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(envelope)
            except Exception:
                pass  # Mock doesn't care about handler errors
    
    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get emitted events, optionally filtered by type."""
        if event_type:
            return [e for e in self._events if e.get("event_type") == event_type]
        return self._events
    
    def clear(self):
        """Clear all events and handlers."""
        self._events.clear()
        self._handlers.clear()


@pytest.fixture
def mock_memu():
    """Provide a mock memU store."""
    return MockMemUStore()


@pytest.fixture
def mock_event_bus():
    """Provide a mock event bus."""
    return MockEventBus()


@pytest.fixture
def sample_context():
    """Provide a sample AutonomyContext."""
    return AutonomyContext(
        task_id="test-task-001",
        state=AutonomyState.PLANNING,
        confidence_score=0.5,
        retry_count=0,
    )


@pytest.fixture
def sample_context_executing():
    """Provide a sample AutonomyContext in EXECUTING state."""
    return AutonomyContext(
        task_id="test-task-002",
        state=AutonomyState.EXECUTING,
        confidence_score=0.75,
        retry_count=0,
    )


@pytest.fixture
def sample_context_blocked():
    """Provide a sample AutonomyContext in BLOCKED state."""
    context = AutonomyContext(
        task_id="test-task-003",
        state=AutonomyState.BLOCKED,
        confidence_score=0.4,
        retry_count=1,
    )
    # Add a transition to blocked
    context.transition_history.append(
        StateTransition(
            from_state=AutonomyState.EXECUTING,
            to_state=AutonomyState.BLOCKED,
            timestamp=datetime.utcnow(),
            reason="Task failed",
        )
    )
    return context


@pytest.fixture
def state_machine(sample_context):
    """Provide a StateMachine with a sample context."""
    return StateMachine(sample_context, max_retries=1)


@pytest.fixture
def state_machine_no_retries(sample_context):
    """Provide a StateMachine with no retries allowed."""
    return StateMachine(sample_context, max_retries=0)


@pytest.fixture
def clear_hooks_store():
    """Clear the hooks module context store before and after test."""
    from openclaw.autonomy import hooks
    
    # Clear before test
    hooks._context_store.clear()
    hooks._state_machines.clear()
    
    yield
    
    # Clear after test
    hooks._context_store.clear()
    hooks._state_machines.clear()
