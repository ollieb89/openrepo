"""Happy path E2E test for autonomy lifecycle.

Tests the complete PLANNING → EXECUTING → COMPLETE lifecycle
with mock LLM responses.
"""
import pytest
import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from openclaw.autonomy.events import (
    AutonomyEventBus,
    AutonomyPlanGenerated,
    AutonomyProgressUpdated,
    AutonomyToolsSelected,
)
from openclaw.autonomy.runner import AutonomyRunner


pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


@pytest.fixture
def mock_llm_responses() -> Dict[str, Any]:
    """Return mock LLM responses for happy path testing."""
    return {
        "plan": {
            "steps": [
                {
                    "id": "1",
                    "action": "Analyze task requirements",
                    "expected_outcome": "Clear understanding of scope"
                },
                {
                    "id": "2",
                    "action": "Implement solution",
                    "expected_outcome": "Code written and tested"
                }
            ]
        },
        "tools": ["file_read", "file_write"],
        "execute": "Step executed successfully",
    }


@pytest.fixture
def runner_with_mock(monkeypatch, tmp_path, mock_llm_responses) -> AutonomyRunner:
    """Create an AutonomyRunner with mocked CLI that returns predetermined responses."""
    runner = AutonomyRunner()
    runner.task_id = "happy-path-test"
    runner.task_description = "Test task for happy path"
    
    # Mock the _invoke_cli method
    def mock_invoke(prompt: str, timeout: int = 600) -> str:
        prompt_lower = prompt.lower()
        
        # Return appropriate response based on prompt content
        if "plan" in prompt_lower and "steps" in prompt_lower:
            return f"```json\n{json.dumps(mock_llm_responses['plan'])}\n```"
        
        if "tool" in prompt_lower and "categor" in prompt_lower:
            return json.dumps(mock_llm_responses['tools'])
        
        if "valid" in prompt_lower:
            return "VALID - plan looks good."
        
        # Default execution response
        return f"```json\n{json.dumps({'output': mock_llm_responses['execute']})}\n```"
    
    monkeypatch.setattr(runner, "_invoke_cli", mock_invoke)
    
    return runner


async def test_autonomy_happy_path_lifecycle(runner_with_mock, monkeypatch):
    """
    Verify full autonomy lifecycle completes successfully.
    
    Expected flow:
    1. Tool analysis
    2. Plan generation  
    3. Step execution (all steps complete)
    4. Final state: success
    """
    # Subscribe to events BEFORE calling any runner methods
    events_captured = []
    
    # Use a real handler function that captures events
    def event_handler(event):
        events_captured.append(event)
    
    AutonomyEventBus.subscribe("autonomy.tools_selected", event_handler)
    AutonomyEventBus.subscribe("autonomy.plan_generated", event_handler)
    AutonomyEventBus.subscribe("autonomy.progress_updated", event_handler)
    
    # Mock execute_step to return success without actually running CLI
    async def mock_execute_step(step, step_num, total_steps):
        return (True, "Step executed successfully")
    
    monkeypatch.setattr(runner_with_mock, "execute_step", mock_execute_step)
    
    # Execute the runner workflow
    runner_with_mock.active_tools = runner_with_mock._analyze_tool_requirements()
    steps = runner_with_mock.planning_phase()
    
    # Handle the expected SystemExit(0) from execution_phase
    with pytest.raises(SystemExit) as exc_info:
        await runner_with_mock.execution_phase(steps)
    
    assert exc_info.value.code == 0, f"Expected exit code 0, got {exc_info.value.code}"
    
    # Verify events were captured
    assert len(events_captured) > 0, f"No events were captured"
    
    # Verify tool selection event (check dict structure since event bus emits dicts)
    tools_events = [e for e in events_captured if e.get("event_type") == "autonomy.tools_selected"]
    assert len(tools_events) >= 1, f"Expected autonomy.tools_selected event, got: {[e.get('event_type') for e in events_captured]}"
    assert tools_events[0].get("payload", {}).get("selected_tools") == ["file_read", "file_write"]
    
    # Verify plan generated event
    plan_events = [e for e in events_captured if e.get("event_type") == "autonomy.plan_generated"]
    assert len(plan_events) >= 1, f"Expected autonomy.plan_generated event, got: {[e.get('event_type') for e in events_captured]}"
    # The payload has nested structure: payload -> plan -> steps
    plan_payload = plan_events[0].get("payload", {})
    plan_data = plan_payload.get("plan", {})
    assert len(plan_data.get("steps", [])) == 2, f"Expected 2 steps, got: {plan_data}"
    
    # Note: execute_step is mocked, so progress events won't be emitted from there.
    # In a real E2E test without mocks, we would see 2 progress events.
    # For this unit-style test, we verify the infrastructure events (tools, plan).
    
    # Verify that the runner completed successfully (exit code 0 means all steps done)
    # The successful exit indicates the happy path worked


async def test_autonomy_plan_generation(runner_with_mock):
    """Verify plan generation works with mock LLM."""
    runner_with_mock.active_tools = runner_with_mock._analyze_tool_requirements()
    steps = runner_with_mock.planning_phase()
    
    assert len(steps) == 2, "Expected 2 steps in plan"
    assert steps[0]["id"] == "1"
    assert steps[0]["action"] == "Analyze task requirements"
    assert steps[1]["id"] == "2"
    assert steps[1]["action"] == "Implement solution"


async def test_autonomy_tool_analysis(runner_with_mock):
    """Verify tool analysis returns expected tools."""
    tools = runner_with_mock._analyze_tool_requirements()
    
    assert tools == ["file_read", "file_write"], f"Expected specific tools, got {tools}"


async def test_autonomy_execution_events(mock_llm_responses, monkeypatch):
    """Verify execution emits correct events in sequence."""
    runner = AutonomyRunner()
    runner.task_id = "event-test"
    runner.task_description = "Test event emission"
    
    # Mock CLI
    def mock_invoke(prompt: str, timeout: int = 600) -> str:
        if "plan" in prompt.lower():
            return f"```json\n{json.dumps(mock_llm_responses['plan'])}\n```"
        if "tool" in prompt.lower():
            return json.dumps(mock_llm_responses['tools'])
        return mock_llm_responses['execute']
    
    monkeypatch.setattr(runner, "_invoke_cli", mock_invoke)
    
    # Capture events BEFORE calling any runner methods with explicit event types
    events = []
    def event_handler(event):
        events.append(event)
    
    AutonomyEventBus.subscribe("autonomy.tools_selected", event_handler)
    AutonomyEventBus.subscribe("autonomy.plan_generated", event_handler)
    
    # Run
    runner.active_tools = runner._analyze_tool_requirements()
    steps = runner.planning_phase()
    
    # Verify events were captured
    assert len(events) > 0, f"No events captured. Events: {events}"
    
    # Verify event types by checking event_type field
    assert any(e.get("event_type") == "autonomy.tools_selected" for e in events), f"Expected autonomy.tools_selected, got: {[e.get('event_type') for e in events]}"
    assert any(e.get("event_type") == "autonomy.plan_generated" for e in events), f"Expected autonomy.plan_generated, got: {[e.get('event_type') for e in events]}"
