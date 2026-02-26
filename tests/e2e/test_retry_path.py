"""
Retry Path E2E Test for OpenClaw Autonomy.

Tests the EXECUTING → BLOCKED → course correction → EXECUTING → COMPLETE lifecycle.
Validates failure recovery through course correction mechanisms.
"""

import asyncio
import json
import pytest

from openclaw.autonomy import AutonomyState, AutonomyContext, StateMachine
from openclaw.autonomy.events import (
    AutonomyStateChanged,
    AutonomyCourseCorrection,
    AutonomyRetryAttempted,
    AutonomyProgressUpdated,
    AutonomyEventBus,
    EVENT_COURSE_CORRECTION,
    EVENT_RETRY_ATTEMPTED,
)


@pytest.mark.e2e
@pytest.mark.slow
async def test_autonomy_retry_path(autonomy_stack):
    """
    Verify course correction recovers from blocked state.
    
    This test validates:
    1. Task enters EXECUTING state
    2. Step failure causes transition to BLOCKED
    3. AutonomyCourseCorrection event is emitted with recovery steps
    4. Recovery steps are executed
    5. Task transitions back to EXECUTING
    6. Task eventually reaches COMPLETE state
    """
    stack = autonomy_stack
    
    # Configure mock LLM to simulate step failure then recovery
    stack.mock_llm.configure_response(
        "fail",
        {"content": None, "error": "Step 2 failed: simulated failure"},
        priority=200
    )
    stack.mock_llm.configure_response(
        "recover",
        {
            "content": json.dumps({
                "recovery_steps": [
                    {"step": 1, "action": "Analyze failure cause", "tool": "none"},
                    {"step": 2, "action": "Apply recovery action", "tool": "code_executor"}
                ]
            })
        },
        priority=150
    )
    stack.mock_llm.configure_response(
        "execute",
        {"content": "Recovery step completed successfully"},
        priority=100
    )
    
    # Set up event capture
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe(EVENT_COURSE_CORRECTION, event_handler)
    AutonomyEventBus.subscribe(EVENT_RETRY_ATTEMPTED, event_handler)
    AutonomyEventBus.subscribe("autonomy.state_changed", event_handler)
    
    try:
        # Create context and state machine (max 1 retry)
        context = AutonomyContext(task_id="e2e-retry-test", confidence_score=0.8)
        state_machine = StateMachine(context, max_retries=1)
        
        # Start at EXECUTING (simulating planning already done)
        # Simulate: PLANNING -> EXECUTING transition already occurred
        state_machine.transition(AutonomyState.EXECUTING, "Starting execution")
        
        assert context.state == AutonomyState.EXECUTING
        
        # Simulate step failure - transition to BLOCKED
        state_machine.transition(
            AutonomyState.BLOCKED,
            "Step 2 failed: mock tool error"
        )
        
        assert context.state == AutonomyState.BLOCKED
        assert context.retry_count == 0
        
        # Emit course correction event (normally done by runner._reflect_and_correct)
        course_correction = AutonomyCourseCorrection(
            task_id=context.task_id,
            failed_step={
                "step_number": 2,
                "action": "Process data",
                "tool": "code_executor",
                "error": "Tool execution failed"
            },
            recovery_steps=[
                {"step": 1, "action": "Diagnose failure", "tool": "none"},
                {"step": 2, "action": "Retry with corrected parameters", "tool": "code_executor"}
            ]
        )
        AutonomyEventBus.emit(course_correction)
        
        await asyncio.sleep(0.1)
        
        # Verify course correction event was emitted
        cc_events = [e for e in received_events if e.get("event_type") == EVENT_COURSE_CORRECTION]
        assert len(cc_events) == 1, "Course correction event should be emitted"
        
        cc_payload = cc_events[0]["payload"]
        assert "failed_step" in cc_payload
        assert "recovery_steps" in cc_payload
        assert len(cc_payload["recovery_steps"]) > 0
        
        # Emit retry attempted event
        retry_event = AutonomyRetryAttempted(
            task_id=context.task_id,
            attempt_number=1,
            max_retries=1,
            reason="Course correction applied, retrying execution"
        )
        AutonomyEventBus.emit(retry_event)
        
        await asyncio.sleep(0.1)
        
        # Verify retry event
        retry_events = [e for e in received_events if e.get("event_type") == EVENT_RETRY_ATTEMPTED]
        assert len(retry_events) == 1
        assert retry_events[0]["payload"]["attempt_number"] == 1
        
        # Simulate retry - transition back to EXECUTING
        state_machine.handle_blocked("Retrying after course correction")
        
        assert context.state == AutonomyState.EXECUTING
        assert context.retry_count == 1
        
        # Emit progress for recovery steps
        for i, step in enumerate(course_correction.recovery_steps, 1):
            progress = AutonomyProgressUpdated(
                task_id=context.task_id,
                step_number=i,
                total_steps=len(course_correction.recovery_steps),
                status="completed",
                duration_seconds=1.0,
                output_snippet=f"Recovery step {i} completed: {step['action']}"
            )
            AutonomyEventBus.emit(progress)
        
        await asyncio.sleep(0.1)
        
        # Complete the task
        state_machine.transition(AutonomyState.COMPLETE, "Recovery successful, task complete")
        
        assert context.state == AutonomyState.COMPLETE
        assert state_machine.is_complete()
        
        # Verify transition history shows the full cycle
        transitions = context.transition_history
        states_traveled = [t.from_state.value for t in transitions] + [transitions[-1].to_state.value]
        
        assert "planning" in states_traveled or "executing" in states_traveled
        assert "blocked" in states_traveled
        assert "complete" in states_traveled
        
    finally:
        AutonomyEventBus.clear_buffer("e2e-retry-test")


@pytest.mark.e2e
async def test_retry_count_tracking(autonomy_stack):
    """
    Verify retry count is properly tracked and limits are enforced.
    """
    context = AutonomyContext(task_id="retry-count-test", confidence_score=0.5)
    state_machine = StateMachine(context, max_retries=2)
    
    # Move to EXECUTING first
    state_machine.transition(AutonomyState.EXECUTING, "Start")
    
    # First failure and retry
    state_machine.transition(AutonomyState.BLOCKED, "First failure")
    assert context.retry_count == 0
    
    state_machine.handle_blocked("First retry")
    assert context.state == AutonomyState.EXECUTING
    assert context.retry_count == 1
    
    # Second failure and retry
    state_machine.transition(AutonomyState.BLOCKED, "Second failure")
    state_machine.handle_blocked("Second retry")
    assert context.state == AutonomyState.EXECUTING
    assert context.retry_count == 2
    
    # Third failure should escalate (max_retries=2)
    state_machine.transition(AutonomyState.BLOCKED, "Third failure")
    
    with pytest.raises(ValueError, match="Maximum retries.*exceeded"):
        state_machine.handle_blocked("Should fail - max retries reached")
    
    # Should escalate instead
    state_machine.transition(AutonomyState.ESCALATING, "Max retries exceeded")
    assert context.state == AutonomyState.ESCALATING


@pytest.mark.e2e
async def test_course_correction_event_payload(autonomy_stack):
    """
    Verify AutonomyCourseCorrection event has complete payload for monitoring.
    """
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe(EVENT_COURSE_CORRECTION, event_handler)
    
    try:
        # Create comprehensive course correction event
        failed_step = {
            "step_number": 3,
            "action": "Deploy service",
            "tool": "docker_exec",
            "input": {"command": "docker run app"},
            "error": "Container failed to start: port 8080 already in use",
            "duration_seconds": 5.2,
            "output": "Error: bind: address already in use"
        }
        
        recovery_steps = [
            {
                "step": 1,
                "action": "Check port availability",
                "tool": "shell",
                "expected_output": "Port status"
            },
            {
                "step": 2,
                "action": "Kill process using port 8080 or use alternative port",
                "tool": "docker_exec",
                "command": "docker run -p 8081:8080 app"
            },
            {
                "step": 3,
                "action": "Verify deployment success",
                "tool": "http_check",
                "endpoint": "http://localhost:8081/health"
            }
        ]
        
        event = AutonomyCourseCorrection(
            task_id="course-correction-payload-test",
            failed_step=failed_step,
            recovery_steps=recovery_steps
        )
        
        AutonomyEventBus.emit(event)
        await asyncio.sleep(0.1)
        
        # Verify complete event structure
        assert len(received_events) == 1
        event_data = received_events[0]
        
        assert event_data["event_type"] == EVENT_COURSE_CORRECTION
        assert event_data["task_id"] == "course-correction-payload-test"
        assert "timestamp" in event_data
        
        payload = event_data["payload"]
        assert "failed_step" in payload
        assert "recovery_steps" in payload
        
        # Verify failed_step structure
        fs = payload["failed_step"]
        assert fs["step_number"] == 3
        assert fs["action"] == "Deploy service"
        assert fs["tool"] == "docker_exec"
        assert "error" in fs
        assert "duration_seconds" in fs
        
        # Verify recovery_steps structure
        rs = payload["recovery_steps"]
        assert len(rs) == 3
        for i, step in enumerate(rs, 1):
            assert step["step"] == i
            assert "action" in step
            assert "tool" in step
        
    finally:
        AutonomyEventBus.clear_buffer("course-correction-payload-test")
