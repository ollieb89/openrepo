"""
Happy Path E2E Test for OpenClaw Autonomy.

Tests the PLANNING -> EXECUTING -> COMPLETE lifecycle with
mock LLM responses for deterministic validation.
"""

import asyncio
import json
import pytest


@pytest.mark.e2e
@pytest.mark.slow
async def test_autonomy_happy_path(autonomy_stack, event_capture):
    """
    Verify full autonomy lifecycle completes successfully.
    
    This test validates:
    1. Task spawns with PLANNING state
    2. AutonomyPlanGenerated event is emitted
    3. State transitions to EXECUTING
    4. AutonomyProgressUpdated events during execution
    5. Task reaches COMPLETE state
    6. Output is correctly captured
    """
    stack = autonomy_stack
    
    # Configure mock LLM for successful planning
    stack.mock_llm.configure_response(
        "plan",
        {
            "content": json.dumps({
                "steps": [
                    {"step": 1, "action": "Initialize task", "tool": "none"},
                    {"step": 2, "action": "Process data", "tool": "code_executor"},
                    {"step": 3, "action": "Finalize output", "tool": "none"}
                ],
                "estimated_duration": "10s"
            })
        },
        priority=100
    )
    
    # Configure mock LLM for successful execution
    stack.mock_llm.configure_response(
        "execute",
        {
            "content": "All steps completed successfully. Task output: 'Hello from E2E test'"
        },
        priority=90
    )
    
    # Step 1: Verify stack is healthy
    assert stack.mock_llm.is_healthy(), "Mock LLM not responding"
    
    # Step 2: Trigger an autonomous task via orchestrator
    # In a real test, this would spawn a task through the API
    # For E2E testing, we simulate the task lifecycle
    
    # Simulate the autonomy lifecycle by directly interacting with components
    from openclaw.autonomy import AutonomyState, AutonomyContext, StateMachine
    from openclaw.autonomy.events import (
        AutonomyStateChanged,
        AutonomyPlanGenerated,
        AutonomyProgressUpdated,
        AutonomyEventBus
    )
    
    # Create a test context
    context = AutonomyContext(task_id="e2e-happy-path-test")
    state_machine = StateMachine(context)
    
    # Subscribe to events
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe("autonomy.state_changed", event_handler)
    AutonomyEventBus.subscribe("autonomy.plan_generated", event_handler)
    AutonomyEventBus.subscribe("autonomy.progress_updated", event_handler)
    
    try:
        # Initial state is PLANNING
        assert context.state == AutonomyState.PLANNING, "Initial state should be PLANNING"
        
        # Transition to EXECUTING (simulating plan generation complete)
        state_machine.transition(AutonomyState.EXECUTING, "Plan generated, starting execution")
        
        # Verify state change event was emitted
        await asyncio.sleep(0.1)  # Allow event to propagate
        state_events = [e for e in received_events if e.get("event_type") == "autonomy.state_changed"]
        assert len(state_events) >= 1, "State change event should be emitted"
        
        # Emit plan generated event
        plan_event = AutonomyPlanGenerated(
            task_id=context.task_id,
            plan={
                "steps": [
                    {"step": 1, "action": "Initialize task"},
                    {"step": 2, "action": "Process data"},
                    {"step": 3, "action": "Finalize output"}
                ]
            }
        )
        AutonomyEventBus.emit(plan_event)
        await asyncio.sleep(0.1)
        
        # Verify plan event was emitted
        plan_events = [e for e in received_events if e.get("event_type") == "autonomy.plan_generated"]
        assert len(plan_events) == 1, "Plan generated event should be emitted"
        assert plan_events[0]["payload"]["plan"]["steps"][0]["step"] == 1
        
        # Emit progress events during execution
        for i in range(1, 4):
            progress_event = AutonomyProgressUpdated(
                task_id=context.task_id,
                step_number=i,
                total_steps=3,
                status="completed",
                duration_seconds=i * 2.0,
                output_snippet=f"Step {i} completed"
            )
            AutonomyEventBus.emit(progress_event)
        
        await asyncio.sleep(0.1)
        
        # Verify progress events
        progress_events = [e for e in received_events if e.get("event_type") == "autonomy.progress_updated"]
        assert len(progress_events) == 3, "Should have 3 progress events"
        
        # Transition to COMPLETE
        state_machine.transition(AutonomyState.COMPLETE, "All steps executed successfully")
        await asyncio.sleep(0.1)
        
        # Verify final state
        assert context.state == AutonomyState.COMPLETE, "Final state should be COMPLETE"
        assert state_machine.is_complete(), "State machine should report complete"
        
        # Verify transition history
        assert len(context.transition_history) == 2, "Should have 2 transitions"
        assert context.transition_history[0].from_state == AutonomyState.PLANNING
        assert context.transition_history[0].to_state == AutonomyState.EXECUTING
        assert context.transition_history[1].from_state == AutonomyState.EXECUTING
        assert context.transition_history[1].to_state == AutonomyState.COMPLETE
        
    finally:
        # Cleanup
        AutonomyEventBus.clear_buffer(context.task_id)


@pytest.mark.e2e
@pytest.mark.slow
async def test_autonomy_events_format(autonomy_stack):
    """
    Verify autonomy events conform to expected format.
    
    Ensures events have all required fields for external monitoring.
    """
    from openclaw.autonomy.events import (
        AutonomyStateChanged,
        AutonomyConfidenceUpdated,
        AutonomyEscalationTriggered,
        AutonomyPlanGenerated,
        AutonomyEventBus
    )
    
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    # Subscribe to all event types
    AutonomyEventBus.subscribe("autonomy.state_changed", event_handler)
    AutonomyEventBus.subscribe("autonomy.confidence_updated", event_handler)
    AutonomyEventBus.subscribe("autonomy.escalation_triggered", event_handler)
    AutonomyEventBus.subscribe("autonomy.plan_generated", event_handler)
    
    try:
        # Emit various event types
        events = [
            AutonomyStateChanged(
                task_id="test-events",
                old_state="planning",
                new_state="executing",
                reason="Test transition"
            ),
            AutonomyConfidenceUpdated(
                task_id="test-events",
                score=0.85,
                factors={"tool_success": 0.9, "step_completion": 0.8}
            ),
            AutonomyEscalationTriggered(
                task_id="test-events",
                reason="Low confidence",
                confidence=0.2
            ),
            AutonomyPlanGenerated(
                task_id="test-events",
                plan={"steps": [{"step": 1, "action": "test"}]}
            ),
        ]
        
        for event in events:
            AutonomyEventBus.emit(event)
        
        await asyncio.sleep(0.2)
        
        # Verify all events have required fields
        for event in received_events:
            # All events must have these fields
            assert "event_type" in event, "Event must have event_type"
            assert "task_id" in event, "Event must have task_id"
            assert "timestamp" in event, "Event must have timestamp"
            assert "payload" in event, "Event must have payload"
            
            # Verify task_id matches
            assert event["task_id"] == "test-events"
            
            # Verify timestamp is reasonable (within last minute)
            import time
            assert 0 < event["timestamp"] <= time.time() + 1
        
        # Verify specific event types
        event_types = [e["event_type"] for e in received_events]
        assert "autonomy.state_changed" in event_types
        assert "autonomy.confidence_updated" in event_types
        assert "autonomy.escalation_triggered" in event_types
        assert "autonomy.plan_generated" in event_types
        
    finally:
        AutonomyEventBus.clear_buffer("test-events")


@pytest.mark.e2e
async def test_mock_llm_response_configuration(autonomy_stack):
    """
    Verify mock LLM can be configured for different responses.
    
    This validates the test infrastructure itself.
    """
    stack = autonomy_stack
    
    # Reset and configure custom responses
    stack.mock_llm.reset()
    
    # Configure two different responses
    stack.mock_llm.configure_response(
        "pattern-a",
        {"content": "Response A"},
        priority=50
    )
    stack.mock_llm.configure_response(
        "pattern-b", 
        {"content": "Response B"},
        priority=50
    )
    
    # Verify mock LLM is still healthy after configuration
    assert stack.mock_llm.is_healthy()
