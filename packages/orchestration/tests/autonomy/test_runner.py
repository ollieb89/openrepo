import json
import pytest
from unittest.mock import patch, MagicMock
from openclaw.autonomy.runner import AutonomyRunner
from openclaw.autonomy.events import (
    AutonomyPlanGenerated, 
    AutonomyProgressUpdated,
    AutonomyConfidenceUpdated,
    AutonomyEscalationTriggered,
    AutonomyToolsSelected,
    AutonomyCourseCorrection
)

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock_run:
        yield mock_run

@pytest.fixture
def mock_event_bus():
    with patch("openclaw.autonomy.runner.AutonomyEventBus.emit") as mock_emit:
        yield mock_emit

@pytest.fixture
def mock_jarvis_state():
    with patch("openclaw.autonomy.runner.JarvisState") as mock_js:
        yield mock_js

def test_planning_phase_success(mock_subprocess, mock_event_bus):
    """planning_phase correctly parses JSON plan and emits event."""
    runner = AutonomyRunner()
    
    # Mock planning output
    plan_json = {
        "steps": [
            {"id": "1", "action": "Test action", "expected_outcome": "Test outcome"}
        ]
    }
    
    # First call: generation, Second call: validation
    mock_subprocess.side_effect = [
        MagicMock(returncode=0, stdout=f"```json\n{json.dumps(plan_json)}\n```"),
        MagicMock(returncode=0, stdout="VALID - plan looks good.")
    ]
    
    steps = runner.planning_phase()
    
    assert len(steps) == 1
    assert steps[0]["action"] == "Test action"
    
    # Verify event emitted
    mock_event_bus.assert_called_once()
    event = mock_event_bus.call_args[0][0]
    assert isinstance(event, AutonomyPlanGenerated)
    assert event.plan == plan_json

def test_planning_phase_revision(mock_subprocess, mock_event_bus):
    """planning_phase falls back to revised plan if validation fails."""
    runner = AutonomyRunner()
    
    initial_plan = {"steps": [{"id": "1", "action": "Bad action"}]}
    revised_plan = {"steps": [{"id": "1", "action": "Good action"}]}
    
    mock_subprocess.side_effect = [
        MagicMock(returncode=0, stdout=json.dumps(initial_plan)),
        MagicMock(returncode=0, stdout=f"Not valid. Here is the revision: ```json\n{json.dumps(revised_plan)}\n```")
    ]
    
    steps = runner.planning_phase()
    
    assert len(steps) == 1
    assert steps[0]["action"] == "Good action"
    
    # Verify event emitted with revised plan
    mock_event_bus.assert_called_once()
    event = mock_event_bus.call_args[0][0]
    assert event.plan == revised_plan

def test_evaluate_confidence_deductions(mock_event_bus):
    """Test confidence score deducts correctly and emits events."""
    runner = AutonomyRunner()
    assert runner.confidence_score == 1.0
    
    # Test failure deduction
    runner._evaluate_confidence(success=False, output="")
    assert runner.confidence_score == 0.7  # 1.0 - 0.3
    
    event = mock_event_bus.call_args[0][0]
    assert isinstance(event, AutonomyConfidenceUpdated)
    assert event.score == 0.7
    assert event.factors["step_failure"] == -0.3
    
    # Test tool error deduction
    runner._evaluate_confidence(success=True, output="Something failed. SyntaxError: invalid syntax")
    assert round(runner.confidence_score, 2) == 0.55  # 0.7 - 0.15
    
    event = mock_event_bus.call_args[0][0]
    assert isinstance(event, AutonomyConfidenceUpdated)
    assert round(event.score, 2) == 0.55
    assert event.factors["tool_error"] == -0.15
    
    # Test unclear requirements deduction
    runner._evaluate_confidence(success=True, output="I need more context to proceed")
    assert round(runner.confidence_score, 2) == 0.05  # 0.55 - 0.5
    
    event = mock_event_bus.call_args[0][0]
    assert isinstance(event, AutonomyConfidenceUpdated)
    assert round(event.score, 2) == 0.05
    assert event.factors["unclear_requirements"] == -0.5

@pytest.mark.asyncio
async def test_execution_phase_success(mock_subprocess, mock_event_bus, mock_jarvis_state):
    """execution_phase iterates steps and emits progress."""
    runner = AutonomyRunner()
    
    steps = [
        {"id": "1", "action": "Action 1"},
        {"id": "2", "action": "Action 2"}
    ]
    
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="Step output")
    
    with pytest.raises(SystemExit) as e:
        await runner.execution_phase(steps)
    
    assert e.value.code == 0
    # Two completions
    events = [call.args[0] for call in mock_event_bus.call_args_list]
    progress_events = [ev for ev in events if isinstance(ev, AutonomyProgressUpdated)]
    assert len(progress_events) == 2
    assert progress_events[0].status == "completed"

@pytest.mark.asyncio
async def test_execution_phase_fallback(mock_subprocess, mock_event_bus, mock_jarvis_state):
    """execution_phase attempts course correction when deviation detected."""
    runner = AutonomyRunner()
    # Set threshold low so confidence-based escalation doesn't interfere
    runner.confidence_threshold = 0.0
    
    steps = [{"id": "1", "action": "Action 1"}]
    
    # Step fails, then reflection returns invalid JSON (no recovery steps)
    mock_subprocess.side_effect = [
        MagicMock(returncode=1, stderr="Error!"),  # Step execution fails
        MagicMock(returncode=0, stdout="Invalid JSON response")  # Reflection fails to parse
    ]
    
    with pytest.raises(SystemExit) as e:
        await runner.execution_phase(steps)
        
    # With no recovery steps, execution continues but step marked as failed
    # All steps processed, so exit code is 0 (completed, not blocked)
    assert e.value.code == 0
    
    # Verify deviation was detected and reflection was attempted
    events = [call.args[0] for call in mock_event_bus.call_args_list]
    progress_events = [ev for ev in events if isinstance(ev, AutonomyProgressUpdated)]
    # Should have a "failed" status event for the step
    failed_events = [ev for ev in progress_events if ev.status == "failed"]
    assert len(failed_events) >= 1

@pytest.mark.asyncio
async def test_execution_phase_escalation(mock_subprocess, mock_event_bus, mock_jarvis_state):
    """execution_phase triggers escalation when confidence drops below threshold."""
    runner = AutonomyRunner()
    runner.confidence_threshold = 0.8
    runner.confidence_score = 1.0
    
    steps = [{"id": "1", "action": "Action 1"}]
    
    # Make it fail -> score goes to 0.7 -> triggers escalation
    mock_subprocess.return_value = MagicMock(returncode=1, stderr="Failed!")
    
    with patch.object(runner, '_escalation_pause_loop') as mock_pause:
        # Mock pause loop to exit so test doesn't hang
        mock_pause.side_effect = SystemExit(1)
        
        with pytest.raises(SystemExit) as e:
            await runner.execution_phase(steps)
            
        # Verify pause loop was called
        mock_pause.assert_called_once()
        assert e.value.code == 1
    
    # Verify escalation event was emitted
    events = [call.args[0] for call in mock_event_bus.call_args_list]
    escalation_events = [ev for ev in events if isinstance(ev, AutonomyEscalationTriggered)]
    
    assert len(escalation_events) == 1
    assert escalation_events[0].confidence == 0.7
    assert "Confidence dropped below threshold" in escalation_events[0].reason

@pytest.mark.asyncio
async def test_escalation_pause_loop():
    """_escalation_pause_loop polls state and exits when status changes."""
    runner = AutonomyRunner()
    runner.state_file = "dummy_state.json"
    runner.task_id = "test_task"
    
    with patch("openclaw.autonomy.runner.JarvisState") as mock_js, \
         patch("openclaw.autonomy.runner.asyncio.sleep") as mock_sleep:
        
        mock_js_instance = MagicMock()
        mock_js.return_value = mock_js_instance
        
        # Sequence of state returns: escalating, escalating, executing (which should break the loop)
        mock_js_instance.get_task.side_effect = [
            {"status": "escalating"},
            {"status": "escalating"},
            {"status": "executing"}
        ]
        
        # This will exit the loop after 3 iterations
        await runner._escalation_pause_loop()
        
        assert mock_sleep.call_count == 3
        assert mock_js_instance.get_task.call_count == 3
        
        # Test terminal states
        mock_js_instance.get_task.side_effect = [{"status": "failed"}]
        with pytest.raises(SystemExit) as e:
            await runner._escalation_pause_loop()
        assert e.value.code == 1

def test_analyze_tool_requirements_success(mock_subprocess, mock_event_bus):
    """_analyze_tool_requirements successfully parses tools and emits event."""
    runner = AutonomyRunner()
    
    mock_subprocess.return_value = MagicMock(returncode=0, stdout='```json\n["file_read", "shell_execution"]\n```')
    tools = runner._analyze_tool_requirements()
    
    assert tools == ["file_read", "shell_execution"]
    mock_event_bus.assert_called_once()
    event = mock_event_bus.call_args[0][0]
    assert isinstance(event, AutonomyToolsSelected)
    assert event.selected_tools == ["file_read", "shell_execution"]

def test_analyze_tool_requirements_fallback(mock_subprocess, mock_event_bus):
    """_analyze_tool_requirements falls back to ['all'] on invalid output."""
    runner = AutonomyRunner()
    
    mock_subprocess.return_value = MagicMock(returncode=0, stdout='This is not a valid json array.')
    tools = runner._analyze_tool_requirements()
    
    assert tools == ["all"]
    mock_event_bus.assert_called_once()
    event = mock_event_bus.call_args[0][0]
    assert event.selected_tools == ["all"]

def test_build_tool_constraint_prompt():
    """_build_tool_constraint_prompt generates correct strings."""
    runner = AutonomyRunner()
    
    assert runner._build_tool_constraint_prompt([]) == ""
    assert runner._build_tool_constraint_prompt(["all"]) == ""
    
    prompt = runner._build_tool_constraint_prompt(["file_read", "file_write"])
    assert "CRITICAL INSTRUCTION" in prompt
    assert "file_read, file_write" in prompt


def test_detect_deviation_explicit_failure():
    """_detect_deviation returns True on explicit failure."""
    runner = AutonomyRunner()
    
    result = runner._detect_deviation(success=False, output="", duration=10)
    assert result is True


def test_detect_deviation_timeout():
    """_detect_deviation returns True when duration exceeds threshold."""
    runner = AutonomyRunner()
    
    # Duration > 180 seconds should trigger deviation
    result = runner._detect_deviation(success=True, output="Success", duration=200)
    assert result is True


def test_detect_deviation_error_density():
    """_detect_deviation returns True on high error keyword density."""
    runner = AutonomyRunner()
    
    # More than 3 error keywords should trigger deviation
    output_with_errors = "Error occurred. Traceback shows exception. Another error found. Fourth error here."
    result = runner._detect_deviation(success=True, output=output_with_errors, duration=10)
    assert result is True


def test_detect_deviation_no_deviation():
    """_detect_deviation returns False when everything looks normal."""
    runner = AutonomyRunner()
    
    result = runner._detect_deviation(success=True, output="Everything worked fine", duration=10)
    assert result is False


def test_reflect_and_correct_success(mock_subprocess):
    """_reflect_and_correct successfully parses recovery steps."""
    runner = AutonomyRunner()
    
    failed_step = {"id": "1", "action": "Test action", "expected_outcome": "Test outcome"}
    output = "Error occurred"
    
    recovery_plan = {
        "steps": [
            {"id": "1a", "action": "Recovery step 1", "expected_outcome": "Fix issue"}
        ]
    }
    
    mock_subprocess.return_value = MagicMock(
        returncode=0, 
        stdout=f"```json\n{json.dumps(recovery_plan)}\n```"
    )
    
    result = runner._reflect_and_correct(failed_step, output)
    
    assert len(result) == 1
    assert result[0]["action"] == "Recovery step 1"


def test_reflect_and_correct_fallback(mock_subprocess):
    """_reflect_and_correct returns empty list on invalid response."""
    runner = AutonomyRunner()
    
    failed_step = {"id": "1", "action": "Test action"}
    output = "Error occurred"
    
    # Invalid response (not valid JSON)
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="Invalid response")
    
    result = runner._reflect_and_correct(failed_step, output)
    
    assert result == []


@pytest.mark.asyncio
async def test_execution_phase_course_correction(mock_subprocess, mock_event_bus):
    """execution_phase performs course correction when deviation detected."""
    runner = AutonomyRunner()
    runner.confidence_threshold = 0.3  # Lower to prevent immediate escalation
    
    steps = [
        {"id": "1", "action": "Failing action"}
    ]
    
    recovery_plan = {
        "steps": [
            {"id": "1a", "action": "Recovery step", "expected_outcome": "Fix the issue"}
        ]
    }
    
    # First call: step execution fails, Second call: reflection generates recovery
    mock_subprocess.side_effect = [
        MagicMock(returncode=1, stderr="Error!"),  # Step fails
        MagicMock(returncode=0, stdout=f"```json\n{json.dumps(recovery_plan)}\n```"),  # Reflection
        MagicMock(returncode=0, stdout="Recovery succeeded")  # Recovery step succeeds
    ]
    
    with pytest.raises(SystemExit) as e:
        await runner.execution_phase(steps)
    
    # Should exit successfully after course correction
    assert e.value.code == 0
    
    # Verify course correction event was emitted
    events = [call.args[0] for call in mock_event_bus.call_args_list]
    correction_events = [ev for ev in events if isinstance(ev, AutonomyCourseCorrection)]
    assert len(correction_events) == 1
    assert correction_events[0].failed_step["id"] == "1"
    assert len(correction_events[0].recovery_steps) == 1
