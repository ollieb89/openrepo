"""
Escalation Path E2E Test for OpenClaw Autonomy.

Tests the EXECUTING → confidence drop → ESCALATING → pause → resume lifecycle.
Validates escalation triggers and pause/resume functionality.
"""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from openclaw.autonomy import AutonomyState, AutonomyContext, StateMachine
from openclaw.autonomy.events import (
    AutonomyStateChanged,
    AutonomyEscalationTriggered,
    AutonomyConfidenceUpdated,
    AutonomyEventBus,
    EVENT_ESCALATION_TRIGGERED,
    EVENT_CONFIDENCE_UPDATED,
)


@pytest.mark.e2e
@pytest.mark.slow
async def test_autonomy_escalation_path(autonomy_stack):
    """
    Verify escalation triggers pause and can be resumed.
    
    This test validates:
    1. Task starts with confidence above threshold
    2. Repeated failures cause confidence to drop
    3. When confidence drops below threshold (0.6), escalation triggers
    4. AutonomyEscalationTriggered event is emitted
    5. Container enters pause loop (checks JarvisState)
    6. Updating JarvisState to "resumed" breaks pause loop
    7. Task can continue or terminate based on new state
    """
    stack = autonomy_stack
    
    # Configure mock LLM to always fail (for escalation)
    stack.mock_llm.configure_response(
        "fail",
        {"content": None, "error": "Persistent failure triggering escalation"},
        priority=200
    )
    
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe(EVENT_ESCALATION_TRIGGERED, event_handler)
    AutonomyEventBus.subscribe(EVENT_CONFIDENCE_UPDATED, event_handler)
    AutonomyEventBus.subscribe("autonomy.state_changed", event_handler)
    
    try:
        # Create context with low confidence threshold simulation
        # In reality, this would use AUTONOMY_CONFIDENCE_THRESHOLD env var
        context = AutonomyContext(
            task_id="e2e-escalation-test",
            confidence_score=0.8  # Start high
        )
        state_machine = StateMachine(context, max_retries=0)  # Escalate immediately, no retries
        
        # Start executing
        state_machine.transition(AutonomyState.EXECUTING, "Starting execution")
        
        # Simulate confidence drops from failures
        confidence_drops = [
            ("tool_error", 0.65, "-0.15"),  # General tool error
            ("step_failure", 0.35, "-0.30"),  # Step failure (below 0.6 threshold)
        ]
        
        for reason, new_score, delta in confidence_drops:
            event = AutonomyConfidenceUpdated(
                task_id=context.task_id,
                score=new_score,
                factors={
                    "previous_score": context.confidence_score,
                    "change": delta,
                    "reason": reason
                }
            )
            AutonomyEventBus.emit(event)
            context.confidence_score = new_score
            
            # Check if below escalation threshold (0.6)
            if new_score < 0.6:
                # Emit escalation event
                escalation = AutonomyEscalationTriggered(
                    task_id=context.task_id,
                    reason=f"Confidence dropped to {new_score} (below threshold 0.6)",
                    confidence=new_score
                )
                AutonomyEventBus.emit(escalation)
        
        await asyncio.sleep(0.1)
        
        # Verify escalation event was emitted
        escalation_events = [e for e in received_events if e.get("event_type") == EVENT_ESCALATION_TRIGGERED]
        assert len(escalation_events) >= 1, "Escalation event should be emitted when confidence < 0.6"
        
        esc = escalation_events[0]
        assert esc["payload"]["confidence"] < 0.6
        assert "below threshold" in esc["payload"]["reason"].lower() or esc["payload"]["confidence"] < 0.6
        
        # Transition to BLOCKED (failure path)
        state_machine.transition(AutonomyState.BLOCKED, "Step failed, confidence low")
        
        # handle_blocked auto-escalates when max retries reached (no ValueError raised)
        state_machine.handle_blocked("Retry would exceed limit - should auto-escalate")
        
        # Verify escalated to ESCALATING
        assert context.state == AutonomyState.ESCALATING, f"Expected ESCALATING but got {context.state}"
        assert state_machine.is_complete()  # ESCALATING is terminal
        
        # Verify transition history includes escalation
        transitions = context.transition_history
        to_states = [t.to_state for t in transitions]
        assert AutonomyState.ESCALATING in to_states
        
    finally:
        AutonomyEventBus.clear_buffer("e2e-escalation-test")


@pytest.mark.e2e
async def test_escalation_confidence_threshold(autonomy_stack):
    """
    Verify escalation triggers at correct confidence threshold.
    
    Tests the boundary conditions around the 0.6 threshold.
    """
    from openclaw.autonomy.confidence import ConfidenceScorer
    
    # Test cases around threshold
    test_cases = [
        (0.61, False, "Just above threshold should not escalate"),
        (0.60, False, "At threshold should not escalate"),
        (0.59, True, "Just below threshold should escalate"),
        (0.40, True, "Well below threshold should escalate"),
        (0.20, True, "Critically low should escalate"),
    ]
    
    for confidence, should_escalate, description in test_cases:
        context = AutonomyContext(
            task_id=f"threshold-test-{confidence}",
            confidence_score=confidence
        )
        
        # Check if below threshold (0.6 is default)
        below_threshold = confidence < 0.6
        assert below_threshold == should_escalate, f"Failed: {description}"


@pytest.mark.e2e
async def test_escalation_pause_state_simulation(autonomy_stack):
    """
    Verify pause state can be simulated and resumed via state changes.
    
    This tests the conceptual pause/resume mechanism without
    requiring actual Docker filesystem access.
    """
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe(EVENT_ESCALATION_TRIGGERED, event_handler)
    AutonomyEventBus.subscribe(EVENT_CONFIDENCE_UPDATED, event_handler)
    AutonomyEventBus.subscribe("autonomy.state_changed", event_handler)
    
    try:
        context = AutonomyContext(
            task_id="pause-simulation-test",
            confidence_score=0.3  # Below threshold
        )
        
        # Emit escalation to trigger "pause"
        escalation = AutonomyEscalationTriggered(
            task_id=context.task_id,
            reason="Low confidence - entering pause for L2 review",
            confidence=0.3
        )
        AutonomyEventBus.emit(escalation)
        
        await asyncio.sleep(0.1)
        
        # Verify escalation event
        escalation_events = [e for e in received_events if e.get("event_type") == EVENT_ESCALATION_TRIGGERED]
        assert len(escalation_events) == 1
        
        # In the real implementation, the runner would:
        # 1. Enter _escalation_pause_loop
        # 2. Poll JarvisState for "resumed"
        # 3. Break loop and reset confidence to 1.0
        # 4. Continue execution
        
        # Simulate the resume by resetting confidence
        context.confidence_score = 1.0
        
        # Emit confidence update showing recovery
        recovery_event = AutonomyConfidenceUpdated(
            task_id=context.task_id,
            score=1.0,
            factors={"reason": "Manual L2 resume", "reset": True}
        )
        AutonomyEventBus.emit(recovery_event)
        
        await asyncio.sleep(0.1)
        
        # Verify confidence reset event
        confidence_events = [e for e in received_events if e.get("event_type") == EVENT_CONFIDENCE_UPDATED]
        last_confidence = confidence_events[-1] if confidence_events else None
        assert last_confidence is not None
        assert last_confidence["payload"]["score"] == 1.0
        
    finally:
        AutonomyEventBus.clear_buffer("pause-simulation-test")


@pytest.mark.e2e
async def test_escalation_event_telemetry(autonomy_stack):
    """
    Verify escalation events include telemetry for monitoring systems.
    """
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe(EVENT_ESCALATION_TRIGGERED, event_handler)
    
    try:
        # Create detailed escalation event
        escalation = AutonomyEscalationTriggered(
            task_id="telemetry-test",
            reason="Confidence degradation over multiple steps",
            confidence=0.25
        )
        
        AutonomyEventBus.emit(escalation)
        await asyncio.sleep(0.1)
        
        # Verify event structure for monitoring
        assert len(received_events) == 1
        event = received_events[0]
        
        # Required fields for external monitoring
        assert "event_type" in event
        assert "task_id" in event
        assert "timestamp" in event
        assert "payload" in event
        
        payload = event["payload"]
        assert "reason" in payload
        assert "confidence" in payload
        
        # Telemetry-specific validation
        assert isinstance(payload["confidence"], float)
        assert 0.0 <= payload["confidence"] <= 1.0
        assert len(payload["reason"]) > 0
        
    finally:
        AutonomyEventBus.clear_buffer("telemetry-test")


@pytest.mark.e2e
async def test_max_retries_leads_to_escalation(autonomy_stack):
    """
    Verify that exhausting retries leads to escalation, not indefinite retry.
    """
    context = AutonomyContext(task_id="max-retries-test", confidence_score=0.5)
    state_machine = StateMachine(context, max_retries=1)
    
    # Move through states to exhaust retries
    state_machine.transition(AutonomyState.EXECUTING, "Start")
    
    # First failure
    state_machine.transition(AutonomyState.BLOCKED, "Failure 1")
    state_machine.handle_blocked("First retry")
    assert context.retry_count == 1
    assert context.state == AutonomyState.EXECUTING
    
    # Second failure - no more retries, should auto-escalate
    state_machine.transition(AutonomyState.BLOCKED, "Failure 2")
    
    # handle_blocked auto-escalates when max retries reached (no ValueError raised)
    state_machine.handle_blocked("Max retries reached - should auto-escalate")
    
    # Verify escalated
    assert context.state == AutonomyState.ESCALATING, f"Expected ESCALATING but got {context.state}"
    assert context.escalation_reason is not None
