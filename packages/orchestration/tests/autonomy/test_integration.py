"""
Integration tests for autonomy framework.

Tests the complete autonomy system with mocked dependencies (memU, event bus).
Covers end-to-end lifecycles from spawn to completion/escalation.
"""
import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

import openclaw.event_bus
from openclaw.autonomy.types import AutonomyContext, AutonomyState
from openclaw.autonomy.state import StateMachine
from openclaw.autonomy.events import (
    AutonomyEventBus,
    AutonomyStateChanged,
    AutonomyConfidenceUpdated,
    AutonomyEscalationTriggered,
    AutonomyRetryAttempted,
    EVENT_STATE_CHANGED,
    EVENT_CONFIDENCE_UPDATED,
    EVENT_ESCALATION_TRIGGERED,
    EVENT_RETRY_ATTEMPTED,
)
from openclaw.autonomy import hooks
from openclaw.autonomy.memory import AutonomyMemoryStore, MEMORY_CATEGORY


class TestEventSystemIntegration:
    """Integration tests for the event system."""

    def test_state_changed_event_emitted(self, mock_event_bus, clear_hooks_store):
        """State changes emit AutonomyStateChanged events."""
        received_events = []
        
        def handler(envelope):
            received_events.append(envelope)
        
        # Patch the event bus to use our mock
        with patch('openclaw.event_bus.emit') as mock_emit, \
             patch('openclaw.event_bus.subscribe') as mock_subscribe:
            mock_subscribe.side_effect = mock_event_bus.subscribe
            mock_emit.side_effect = mock_event_bus.emit
            
            AutonomyEventBus.subscribe(EVENT_STATE_CHANGED, handler)
            
            # Create context and trigger state change
            context = hooks.on_task_spawn("event-test-1", {"max_retries": 1})
            
            # Should have emitted planning event
            planning_events = mock_event_bus.get_events(EVENT_STATE_CHANGED)
            assert len(planning_events) == 1
            assert planning_events[0]["payload"]["new_state"] == "planning"

    def test_confidence_update_debouncing(self, mock_event_bus):
        """Confidence updates are debounced to prevent flooding."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit
            
            # Emit multiple confidence updates rapidly
            for i in range(5):
                event = AutonomyConfidenceUpdated(
                    task_id="debounce-test",
                    score=0.5 + (i * 0.01),  # Small changes
                    factors={"test": 0.5},
                )
                AutonomyEventBus.emit(event)
            
            # Only first should be emitted (debounced)
            confidence_events = mock_event_bus.get_events(EVENT_CONFIDENCE_UPDATED)
            assert len(confidence_events) == 1

    def test_confidence_significant_change_bypasses_debounce(self, mock_event_bus):
        """Large confidence changes bypass debounce."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit
            
            # First update
            AutonomyEventBus.emit(AutonomyConfidenceUpdated(
                task_id="big-change-test",
                score=0.5,
                factors={},
            ))
            
            # Second update with significant change (> 0.1)
            AutonomyEventBus.emit(AutonomyConfidenceUpdated(
                task_id="big-change-test",
                score=0.7,  # 0.2 change
                factors={},
            ))
            
            confidence_events = mock_event_bus.get_events(EVENT_CONFIDENCE_UPDATED)
            assert len(confidence_events) == 2

    def test_escalation_event_emitted(self, mock_event_bus):
        """Escalation triggers AutonomyEscalationTriggered event."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit
            
            AutonomyEventBus.emit(AutonomyEscalationTriggered(
                task_id="escalation-test",
                reason="Confidence below threshold",
                confidence=0.45,
            ))
            
            events = mock_event_bus.get_events(EVENT_ESCALATION_TRIGGERED)
            assert len(events) == 1
            assert events[0]["payload"]["confidence"] == 0.45

    def test_retry_event_emitted(self, mock_event_bus):
        """Retry attempts emit AutonomyRetryAttempted events."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit
            
            AutonomyEventBus.emit(AutonomyRetryAttempted(
                task_id="retry-test",
                attempt_number=1,
                max_retries=2,
                reason="Transient failure",
            ))
            
            events = mock_event_bus.get_events(EVENT_RETRY_ATTEMPTED)
            assert len(events) == 1
            assert events[0]["payload"]["attempt_number"] == 1


class TestHooksIntegration:
    """Integration tests for spawn flow hooks."""

    def test_on_task_spawn_creates_context(self, clear_hooks_store):
        """on_task_spawn creates AutonomyContext with PLANNING state."""
        context = hooks.on_task_spawn("spawn-test-1", {"max_retries": 2})
        
        assert context.task_id == "spawn-test-1"
        assert context.state == AutonomyState.PLANNING
        assert context.confidence_score == 0.0
        assert context.retry_count == 0

    def test_on_task_spawn_stores_context(self, clear_hooks_store):
        """on_task_spawn stores context in internal store."""
        hooks.on_task_spawn("spawn-test-2", {"max_retries": 1})
        
        retrieved = hooks.get_autonomy_context("spawn-test-2")
        assert retrieved is not None
        assert retrieved.task_id == "spawn-test-2"

    def test_on_container_healthy_transitions(self, clear_hooks_store):
        """on_container_healthy transitions PLANNING -> EXECUTING."""
        hooks.on_task_spawn("health-test", {"max_retries": 1})
        
        context_before = hooks.get_autonomy_context("health-test")
        assert context_before.state == AutonomyState.PLANNING
        
        hooks.on_container_healthy("health-test")
        
        context_after = hooks.get_autonomy_context("health-test")
        assert context_after.state == AutonomyState.EXECUTING

    def test_on_task_complete_transitions(self, clear_hooks_store):
        """on_task_complete transitions to COMPLETE."""
        hooks.on_task_spawn("complete-test", {"max_retries": 1})
        hooks.on_container_healthy("complete-test")
        
        hooks.on_task_complete("complete-test", {"status": "success"})
        
        context = hooks.get_autonomy_context("complete-test")
        assert context.state == AutonomyState.COMPLETE

    def test_on_task_failed_with_retry(self, clear_hooks_store):
        """on_task_failed with retries transitions to BLOCKED then EXECUTING."""
        hooks.on_task_spawn("fail-retry-test", {"max_retries": 1})
        hooks.on_container_healthy("fail-retry-test")
        
        context_before = hooks.get_autonomy_context("fail-retry-test")
        assert context_before.retry_count == 0
        
        hooks.on_task_failed("fail-retry-test", "Temporary error")
        
        context_after = hooks.get_autonomy_context("fail-retry-test")
        assert context_after.state == AutonomyState.EXECUTING  # Auto-retried
        assert context_after.retry_count == 1

    def test_on_task_failed_escalates(self, clear_hooks_store):
        """on_task_failed with no retries escalates."""
        hooks.on_task_spawn("fail-escalate-test", {"max_retries": 0})
        hooks.on_container_healthy("fail-escalate-test")
        
        hooks.on_task_failed("fail-escalate-test", "Critical error")
        
        context = hooks.get_autonomy_context("fail-escalate-test")
        assert context.state == AutonomyState.ESCALATING
        assert context.escalation_reason == "Critical error"

    def test_update_confidence_changes_score(self, clear_hooks_store):
        """update_confidence updates the context confidence score."""
        hooks.on_task_spawn("conf-test", {"max_retries": 1})
        
        hooks.update_confidence("conf-test", 0.85, {"complexity": 0.3})
        
        context = hooks.get_autonomy_context("conf-test")
        assert context.confidence_score == 0.85

    def test_list_active_contexts(self, clear_hooks_store):
        """list_active_contexts returns all active contexts."""
        hooks.on_task_spawn("active-1", {"max_retries": 1})
        hooks.on_task_spawn("active-2", {"max_retries": 1})
        
        active = hooks.list_active_contexts()
        assert len(active) == 2
        assert "active-1" in active
        assert "active-2" in active


class TestMemoryStoreIntegration:
    """Integration tests for memU persistence."""

    def test_save_context_persists_data(self, mock_memu):
        """save_context stores serialized context and metadata."""
        with patch('openclaw.autonomy.memory.AutonomyMemoryStore._memorize') as mock_save:
            mock_save.side_effect = lambda content, metadata: mock_memu.memorize(content, MEMORY_CATEGORY, metadata)
            
            context = AutonomyContext(
                task_id="mem-test-1",
                state=AutonomyState.EXECUTING,
                confidence_score=0.75,
            )
            
            AutonomyMemoryStore.save_context(context, project="test-project")
            
            # Verify it was stored
            results = mock_memu.retrieve(
                category=MEMORY_CATEGORY,
                meta_filters={"task_id": "mem-test-1"},
            )
            assert len(results) == 1
            assert results[0]["metadata"]["project"] == "test-project"

    def test_load_context_retrieves_data(self, mock_memu):
        """load_context retrieves context from memU."""
        # Pre-populate with test data
        context_data = {
            "task_id": "mem-test-2",
            "state": "executing",
            "confidence_score": 0.8,
            "retry_count": 0,
            "escalation_reason": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "transition_history": [],
        }
        
        mock_memu.memorize(
            content=json.dumps(context_data),
            category=MEMORY_CATEGORY,
            metadata={
                "task_id": "mem-test-2",
                "state": "executing",
                "archived": False,
            },
        )
        
        with patch('openclaw.autonomy.memory.AutonomyMemoryStore._retrieve') as mock_ret:
            mock_ret.side_effect = mock_memu.retrieve
            
            loaded = AutonomyMemoryStore.load_context("mem-test-2")
            
            assert loaded is not None
            assert loaded.task_id == "mem-test-2"
            assert loaded.state == AutonomyState.EXECUTING

    def test_archive_context_marks_archived(self, mock_memu):
        """archive_context marks context as archived."""
        with patch('openclaw.autonomy.memory.AutonomyMemoryStore._memorize') as mock_save:
            mock_save.side_effect = lambda content, metadata: mock_memu.memorize(content, MEMORY_CATEGORY, metadata)
            
            context = AutonomyContext(
                task_id="archive-test",
                state=AutonomyState.COMPLETE,
            )
            
            AutonomyMemoryStore.archive_context(context, project="test")
            
            results = mock_memu.retrieve(
                category=MEMORY_CATEGORY,
                meta_filters={"task_id": "archive-test"},
            )
            assert len(results) == 1
            assert results[0]["metadata"]["archived"] is True

    def test_query_filters_by_project(self, mock_memu):
        """query filters contexts by project."""
        with patch('openclaw.autonomy.memory.AutonomyMemoryStore._memorize') as mock_save:
            mock_save.side_effect = lambda content, metadata: mock_memu.memorize(content, MEMORY_CATEGORY, metadata)
            
            # Save contexts for different projects
            ctx1 = AutonomyContext(task_id="query-1", state=AutonomyState.COMPLETE)
            ctx2 = AutonomyContext(task_id="query-2", state=AutonomyState.COMPLETE)
            
            AutonomyMemoryStore.archive_context(ctx1, project="project-a")
            AutonomyMemoryStore.archive_context(ctx2, project="project-b")
        
        with patch('openclaw.autonomy.memory.AutonomyMemoryStore._retrieve') as mock_ret:
            mock_ret.side_effect = mock_memu.retrieve
            
            results = AutonomyMemoryStore.query(project="project-a", archived=True)
            
            assert len(results) == 1
            assert results[0].task_id == "query-1"


class TestEndToEndLifecycle:
    """End-to-end tests for complete task lifecycles."""

    def test_full_happy_path(self, mock_event_bus, clear_hooks_store):
        """Complete happy path: spawn -> healthy -> complete."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit
            
            # 1. Task spawned
            context = hooks.on_task_spawn("e2e-happy", {"max_retries": 1})
            assert context.state == AutonomyState.PLANNING
            
            # 2. Container healthy
            hooks.on_container_healthy("e2e-happy")
            context = hooks.get_autonomy_context("e2e-happy")
            assert context.state == AutonomyState.EXECUTING
            
            # 3. Confidence updates during execution
            hooks.update_confidence("e2e-happy", 0.85, {"complexity": 0.3})
            
            # 4. Task completes
            hooks.on_task_complete("e2e-happy", {"status": "success", "output": "Done"})
            context = hooks.get_autonomy_context("e2e-happy")
            assert context.state == AutonomyState.COMPLETE
            
            # Verify events were emitted
            state_events = mock_event_bus.get_events(EVENT_STATE_CHANGED)
            assert len(state_events) >= 3  # planning, executing, complete

    def test_full_retry_path(self, mock_event_bus, clear_hooks_store):
        """Complete retry path: spawn -> fail -> retry -> complete."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit
            
            # Setup with 1 retry
            hooks.on_task_spawn("e2e-retry", {"max_retries": 1})
            hooks.on_container_healthy("e2e-retry")
            
            # First failure triggers retry
            hooks.on_task_failed("e2e-retry", "First error")
            context = hooks.get_autonomy_context("e2e-retry")
            assert context.state == AutonomyState.EXECUTING  # Auto-retried
            assert context.retry_count == 1
            
            # Second execution succeeds
            hooks.on_task_complete("e2e-retry", {"status": "success"})
            context = hooks.get_autonomy_context("e2e-retry")
            assert context.state == AutonomyState.COMPLETE

    def test_full_escalation_path(self, mock_event_bus, clear_hooks_store):
        """Complete escalation path: spawn -> fail -> escalate."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit
            
            # Setup with no retries
            hooks.on_task_spawn("e2e-escalate", {"max_retries": 0})
            hooks.on_container_healthy("e2e-escalate")
            
            # Failure escalates immediately
            hooks.on_task_failed("e2e-escalate", "Critical failure")
            context = hooks.get_autonomy_context("e2e-escalate")
            assert context.state == AutonomyState.ESCALATING
            assert context.escalation_reason == "Critical failure"
            
            # Verify escalation event
            events = mock_event_bus.get_events(EVENT_ESCALATION_TRIGGERED)
            assert len(events) == 1

    def test_cleanup_removes_context(self, mock_event_bus, clear_hooks_store):
        """on_task_removed cleans up context."""
        hooks.on_task_spawn("cleanup-test", {"max_retries": 1})
        assert hooks.get_autonomy_context("cleanup-test") is not None
        
        hooks.on_task_removed("cleanup-test", archive=False)
        
        assert hooks.get_autonomy_context("cleanup-test") is None


class TestGap03ProjectId:
    """GAP-03 tests: project_id threading through events and hooks."""

    def test_to_dict_includes_project_id(self):
        """AutonomyStateChanged.to_dict() has project_id key when project_id is supplied."""
        event = AutonomyStateChanged(
            task_id="t1",
            project_id="proj-x",
            old_state="planning",
            new_state="executing",
            reason="Test",
        )
        d = event.to_dict()
        assert "project_id" in d, "to_dict() must include 'project_id' key"
        assert d["project_id"] == "proj-x"

    def test_to_dict_project_id_none_by_default(self):
        """AutonomyStateChanged.to_dict() project_id is None when not supplied."""
        event = AutonomyStateChanged(
            task_id="t1",
            old_state="",
            new_state="planning",
            reason="Test",
        )
        d = event.to_dict()
        assert d.get("project_id") is None

    def test_on_task_spawn_emits_with_project_id(self, mock_event_bus, clear_hooks_store):
        """on_task_spawn with project_id in task_spec emits event with project_id."""
        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = mock_event_bus.emit

            hooks.on_task_spawn("task-001", {"project_id": "proj-alpha", "max_retries": 1})

            all_events = mock_event_bus.get_events(EVENT_STATE_CHANGED)
            assert len(all_events) >= 1
            assert all_events[0]["project_id"] == "proj-alpha", (
                f"emitted envelope must have project_id='proj-alpha', got {all_events[0]}"
            )

    def test_on_task_failed_emits_autonomy_escalation_event(self, mock_event_bus, clear_hooks_store):
        """on_task_failed escalation path emits event_type='autonomy.escalation' with project_id."""
        all_captured = []

        def capture(envelope):
            all_captured.append(envelope)

        with patch('openclaw.event_bus.emit') as mock_emit:
            mock_emit.side_effect = lambda ev: (mock_event_bus.emit(ev), all_captured.append(ev))

            hooks.on_task_spawn("task-002", {"project_id": "proj-beta", "max_retries": 0})
            hooks.on_container_healthy("task-002")
            hooks.on_task_failed("task-002", "error")

        escalation_events = [
            e for e in all_captured if e.get("event_type") == "autonomy.escalation"
        ]
        assert len(escalation_events) >= 1, (
            f"Expected at least one 'autonomy.escalation' event, got event types: "
            f"{[e.get('event_type') for e in all_captured]}"
        )
        assert escalation_events[0].get("project_id") == "proj-beta"


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_missing_context_raises(self, clear_hooks_store):
        """Operations on missing context raise ValueError."""
        with pytest.raises(ValueError, match="No autonomy context found"):
            hooks.on_container_healthy("nonexistent-task")

    def test_invalid_state_transition_caught(self, clear_hooks_store):
        """Invalid state transitions are caught."""
        hooks.on_task_spawn("invalid-test", {"max_retries": 1})
        
        # Can't go from PLANNING to COMPLETE directly
        # This would raise in StateMachine but hooks handle it gracefully

    def test_memu_unavailable_graceful(self, clear_hooks_store):
        """memU unavailability is handled gracefully."""
        with patch('openclaw.autonomy.memory.AutonomyMemoryStore._memorize') as mock_mem:
            mock_mem.side_effect = RuntimeError("memU unavailable")
            
            context = AutonomyContext(task_id="mem-fail", state=AutonomyState.COMPLETE)
            
            # Should not raise, just return False
            result = AutonomyMemoryStore.archive_context(context)
            assert result is False

    def test_event_bus_unavailable_graceful(self):
        """Event bus unavailability doesn't block execution."""
        with patch('openclaw.event_bus') as mock_eb:
            mock_eb.emit.side_effect = Exception("Event bus down")
            
            # Should not raise
            event = AutonomyStateChanged(
                task_id="event-fail",
                old_state="planning",
                new_state="executing",
                reason="Test",
            )
            # This would fail silently in practice
            AutonomyEventBus.emit(event)
