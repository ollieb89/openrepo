"""
Multi-Step Plan E2E Test for OpenClaw Autonomy.

Tests complex multi-step plan execution with partial failures,
demonstrating the full autonomy capabilities in realistic scenarios.
"""

import asyncio
import json
import pytest

from openclaw.autonomy import AutonomyState, AutonomyContext, StateMachine
from openclaw.autonomy.events import (
    AutonomyStateChanged,
    AutonomyPlanGenerated,
    AutonomyProgressUpdated,
    AutonomyCourseCorrection,
    AutonomyEventBus,
)


@pytest.mark.e2e
@pytest.mark.slow
async def test_autonomy_multi_step_with_recovery(autonomy_stack):
    """
    Verify 5-step plan with step 3 failing and recovering.
    
    Plan: [analyze, setup, execute, verify, report]
    - Step 1-2: Success
    - Step 3: Fails, triggers course correction
    - Recovery steps: [diagnose, fix]
    - Continue: Step 4-5
    
    Validates:
    - Multi-step tracking
    - Partial failure handling
    - Dynamic recovery step insertion
    - State preservation through recovery
    """
    stack = autonomy_stack
    
    # Configure mock responses
    stack.mock_llm.configure_response(
        "analyze",
        {"content": "Analysis complete: 5 steps required"},
        priority=100
    )
    stack.mock_llm.configure_response(
        "setup",
        {"content": "Environment configured"},
        priority=90
    )
    stack.mock_llm.configure_response(
        "execute",
        {"content": None, "error": "Execution failed: dependency missing"},
        priority=200
    )
    stack.mock_llm.configure_response(
        "fix",
        {"content": "Dependencies installed, retrying"},
        priority=150
    )
    stack.mock_llm.configure_response(
        "verify",
        {"content": "All checks passed"},
        priority=80
    )
    stack.mock_llm.configure_response(
        "report",
        {"content": "Task completed successfully"},
        priority=70
    )
    
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe("autonomy.*", event_handler)
    
    try:
        # Create plan with 5 steps
        original_plan = {
            "steps": [
                {"number": 1, "name": "analyze", "action": "Analyze requirements", "estimated_duration": 5},
                {"number": 2, "name": "setup", "action": "Setup environment", "estimated_duration": 10},
                {"number": 3, "name": "execute", "action": "Execute main task", "estimated_duration": 30},
                {"number": 4, "name": "verify", "action": "Verify results", "estimated_duration": 5},
                {"number": 5, "name": "report", "action": "Generate report", "estimated_duration": 5},
            ],
            "total_estimated_duration": 55
        }
        
        context = AutonomyContext(
            task_id="multi-step-recovery-test",
            confidence_score=0.9
        )
        state_machine = StateMachine(context, max_retries=1)
        
        # Emit plan generated event
        plan_event = AutonomyPlanGenerated(
            task_id=context.task_id,
            plan=original_plan
        )
        AutonomyEventBus.emit(plan_event)
        
        # Start executing
        state_machine.transition(AutonomyState.EXECUTING, "Beginning multi-step execution")
        
        completed_steps = []
        
        # Execute step 1: Analyze
        progress_1 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=1,
            total_steps=5,
            status="completed",
            duration_seconds=5.0,
            output_snippet="Analysis: 5 steps identified"
        )
        AutonomyEventBus.emit(progress_1)
        completed_steps.append(1)
        
        # Execute step 2: Setup
        progress_2 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=2,
            total_steps=5,
            status="completed",
            duration_seconds=8.0,
            output_snippet="Environment ready"
        )
        AutonomyEventBus.emit(progress_2)
        completed_steps.append(2)
        
        # Execute step 3: Execute (FAILS)
        progress_3 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=3,
            total_steps=5,
            status="failed",
            duration_seconds=12.0,
            output_snippet="Error: dependency missing"
        )
        AutonomyEventBus.emit(progress_3)
        
        # Transition to BLOCKED
        state_machine.transition(AutonomyState.BLOCKED, "Step 3 failed: dependency missing")
        
        # Emit course correction with recovery steps
        recovery_steps = [
            {"number": 1, "name": "diagnose", "action": "Diagnose failure cause", "estimated_duration": 2},
            {"number": 2, "name": "fix", "action": "Install missing dependencies", "estimated_duration": 10},
            {"number": 3, "name": "retry", "action": "Retry step 3", "estimated_duration": 30},
        ]
        
        correction_event = AutonomyCourseCorrection(
            task_id=context.task_id,
            failed_step=original_plan["steps"][2],  # Step 3
            recovery_steps=recovery_steps
        )
        AutonomyEventBus.emit(correction_event)
        
        await asyncio.sleep(0.1)
        
        # Retry - back to EXECUTING
        state_machine.handle_blocked("Applying course correction")
        
        # Execute recovery step 1: Diagnose
        recovery_1 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=1,
            total_steps=3,
            status="completed",
            duration_seconds=1.5,
            output_snippet="Diagnosis: Missing numpy dependency"
        )
        AutonomyEventBus.emit(recovery_1)
        
        # Execute recovery step 2: Fix
        recovery_2 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=2,
            total_steps=3,
            status="completed",
            duration_seconds=8.0,
            output_snippet="Dependencies installed: numpy==1.24.0"
        )
        AutonomyEventBus.emit(recovery_2)
        
        # Execute recovery step 3: Retry original step 3
        recovery_3 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=3,
            total_steps=3,
            status="completed",
            duration_seconds=25.0,
            output_snippet="Step 3 completed successfully after fix"
        )
        AutonomyEventBus.emit(recovery_3)
        
        # Continue with original step 4
        progress_4 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=4,
            total_steps=5,
            status="completed",
            duration_seconds=4.5,
            output_snippet="Verification: all outputs valid"
        )
        AutonomyEventBus.emit(progress_4)
        completed_steps.append(4)
        
        # Execute step 5: Report
        progress_5 = AutonomyProgressUpdated(
            task_id=context.task_id,
            step_number=5,
            total_steps=5,
            status="completed",
            duration_seconds=3.0,
            output_snippet="Report generated: task successful"
        )
        AutonomyEventBus.emit(progress_5)
        completed_steps.append(5)
        
        # Complete
        state_machine.transition(AutonomyState.COMPLETE, "All steps executed including recovery")
        
        await asyncio.sleep(0.1)
        
        # Verify outcomes
        assert context.state == AutonomyState.COMPLETE
        assert state_machine.is_complete()
        
        # Verify all original steps completed (via recovery for step 3)
        assert len(completed_steps) == 4  # Steps 1, 2, 4, 5 directly completed
        assert 3 not in completed_steps  # Step 3 required recovery
        
        # Verify course correction event was emitted
        cc_events = [e for e in received_events if e.get("event_type") == "autonomy.course_correction"]
        assert len(cc_events) == 1
        
        # Verify progress events include both original and recovery
        progress_events = [e for e in received_events if e.get("event_type") == "autonomy.progress_updated"]
        assert len(progress_events) == 8  # 5 original + 3 recovery
        
    finally:
        AutonomyEventBus.clear_buffer("multi-step-recovery-test")


@pytest.mark.e2e
async def test_multi_step_progress_tracking(autonomy_stack):
    """
    Verify progress events accurately track step completion.
    """
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe("autonomy.progress_updated", event_handler)
    
    try:
        task_id = "progress-tracking-test"
        
        # Simulate 3-step plan
        for i in range(1, 4):
            event = AutonomyProgressUpdated(
                task_id=task_id,
                step_number=i,
                total_steps=3,
                status="completed",
                duration_seconds=float(i * 2),
                output_snippet=f"Step {i} output"
            )
            AutonomyEventBus.emit(event)
        
        await asyncio.sleep(0.1)
        
        # Verify sequential progression
        progress_events = [e for e in received_events if e.get("event_type") == "autonomy.progress_updated"]
        assert len(progress_events) == 3
        
        step_numbers = [e["payload"]["step_number"] for e in progress_events]
        assert step_numbers == [1, 2, 3]
        
        # Verify all report same total
        for e in progress_events:
            assert e["payload"]["total_steps"] == 3
            assert e["payload"]["status"] == "completed"
        
    finally:
        AutonomyEventBus.clear_buffer(task_id)


@pytest.mark.e2e
async def test_partial_failure_state_preservation(autonomy_stack):
    """
    Verify state and context are preserved through failure and recovery.
    """
    context = AutonomyContext(
        task_id="state-preservation-test",
        confidence_score=0.85
    )
    state_machine = StateMachine(context, max_retries=1)
    
    # Track state changes
    states_seen = []
    
    def track_transition(from_state, to_state):
        states_seen.append((from_state.value, to_state.value))
    
    # Execute through failure cycle
    state_machine.transition(AutonomyState.EXECUTING, "Start")
    assert context.state == AutonomyState.EXECUTING
    
    # Store reference data
    task_id_before = context.task_id
    created_at_before = context.created_at
    
    # Fail
    state_machine.transition(AutonomyState.BLOCKED, "Step failed")
    assert context.state == AutonomyState.BLOCKED
    
    # Verify context preserved
    assert context.task_id == task_id_before
    assert context.created_at == created_at_before
    assert context.confidence_score == 0.85
    
    # Recover
    state_machine.handle_blocked("Retrying")
    assert context.state == AutonomyState.EXECUTING
    
    # Verify context still preserved
    assert context.task_id == task_id_before
    assert context.created_at == created_at_before
    
    # Complete
    state_machine.transition(AutonomyState.COMPLETE, "Done")
    assert context.state == AutonomyState.COMPLETE
    
    # Verify transition history
    assert len(context.transition_history) == 3
    
    # All transitions captured
    transitions = [(t.from_state.value, t.to_state.value) for t in context.transition_history]
    assert ("planning", "executing") in transitions
    assert ("executing", "blocked") in transitions or ("blocked", "executing") in transitions
    assert any(t[1] == "complete" for t in transitions)


@pytest.mark.e2e
async def test_dynamic_step_injection(autonomy_stack):
    """
    Verify recovery steps can be dynamically injected into execution flow.
    """
    received_events = []
    
    def event_handler(event):
        received_events.append(event)
    
    AutonomyEventBus.subscribe("autonomy.course_correction", event_handler)
    
    try:
        task_id = "dynamic-injection-test"
        
        # Original 3-step plan
        original_steps = [
            {"number": 1, "action": "Prepare"},
            {"number": 2, "action": "Process"},
            {"number": 3, "action": "Cleanup"}
        ]
        
        # Step 2 fails, need recovery
        recovery_steps = [
            {"number": 1, "action": "Analyze failure"},
            {"number": 2, "action": "Apply fix"},
        ]
        
        # Emit course correction with recovery
        correction = AutonomyCourseCorrection(
            task_id=task_id,
            failed_step=original_steps[1],  # Step 2
            recovery_steps=recovery_steps
        )
        AutonomyEventBus.emit(correction)
        
        await asyncio.sleep(0.1)
        
        # Verify recovery steps are available in event
        cc_events = [e for e in received_events if e.get("event_type") == "autonomy.course_correction"]
        assert len(cc_events) == 1
        
        payload = cc_events[0]["payload"]
        assert len(payload["recovery_steps"]) == 2
        assert payload["failed_step"]["number"] == 2
        
    finally:
        AutonomyEventBus.clear_buffer(task_id)
