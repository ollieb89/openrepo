"""
Tests for autonomy state machine module.

Covers state transitions, retry logic, escalation handling, and terminal states.
"""
import pytest
from datetime import datetime

from openclaw.autonomy.types import AutonomyContext, AutonomyState, StateTransition
from openclaw.autonomy.state import StateMachine


class TestStateMachineInitialization:
    """Tests for StateMachine initialization."""

    def test_default_max_retries(self, sample_context):
        """Default max_retries is 1."""
        sm = StateMachine(sample_context)
        assert sm.max_retries == 1

    def test_custom_max_retries(self, sample_context):
        """Custom max_retries is respected."""
        sm = StateMachine(sample_context, max_retries=3)
        assert sm.max_retries == 3

    def test_stores_context_reference(self, sample_context):
        """StateMachine stores reference to context."""
        sm = StateMachine(sample_context)
        assert sm.context is sample_context

    def test_initial_state_accessible(self, sample_context):
        """Current state matches context state."""
        sm = StateMachine(sample_context)
        assert sm.current_state == AutonomyState.PLANNING


class TestValidTransitions:
    """Tests for valid state transitions."""

    def test_planning_to_executing(self, sample_context, state_machine):
        """PLANNING -> EXECUTING is valid."""
        state_machine.transition(AutonomyState.EXECUTING, "Starting execution")
        assert state_machine.current_state == AutonomyState.EXECUTING

    def test_executing_to_blocked(self, sample_context_executing):
        """EXECUTING -> BLOCKED is valid."""
        sm = StateMachine(sample_context_executing)
        sm.transition(AutonomyState.BLOCKED, "Hit obstacle")
        assert sm.current_state == AutonomyState.BLOCKED

    def test_executing_to_complete(self, sample_context_executing):
        """EXECUTING -> COMPLETE is valid."""
        sm = StateMachine(sample_context_executing)
        sm.transition(AutonomyState.COMPLETE, "Task done")
        assert sm.current_state == AutonomyState.COMPLETE

    def test_blocked_to_executing_with_retry(self, sample_context_blocked):
        """BLOCKED -> EXECUTING increments retry count."""
        sm = StateMachine(sample_context_blocked, max_retries=2)
        initial_retries = sm.context.retry_count
        sm.transition(AutonomyState.EXECUTING, "Retrying")
        assert sm.current_state == AutonomyState.EXECUTING
        assert sm.context.retry_count == initial_retries + 1

    def test_blocked_to_escalating(self, sample_context_blocked, state_machine_no_retries):
        """BLOCKED -> ESCALATING when max retries exceeded."""
        # First transition to BLOCKED
        state_machine_no_retries.transition(AutonomyState.EXECUTING)
        state_machine_no_retries.transition(AutonomyState.BLOCKED, "Failed")
        
        # Then escalate
        state_machine_no_retries.transition(AutonomyState.ESCALATING, "Max retries")
        assert state_machine_no_retries.current_state == AutonomyState.ESCALATING


class TestInvalidTransitions:
    """Tests for invalid state transitions."""

    def test_planning_cannot_complete_directly(self, sample_context):
        """PLANNING -> COMPLETE is invalid."""
        sm = StateMachine(sample_context)
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(AutonomyState.COMPLETE)

    def test_planning_cannot_block_directly(self, sample_context):
        """PLANNING -> BLOCKED is invalid."""
        sm = StateMachine(sample_context)
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(AutonomyState.BLOCKED)

    def test_executing_cannot_escalate_directly(self, sample_context_executing):
        """EXECUTING -> ESCALATING is invalid (must go through BLOCKED)."""
        sm = StateMachine(sample_context_executing)
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(AutonomyState.ESCALATING)

    def test_complete_is_terminal(self, sample_context_executing):
        """COMPLETE cannot transition anywhere."""
        sm = StateMachine(sample_context_executing)
        sm.transition(AutonomyState.COMPLETE)
        
        with pytest.raises(ValueError, match="Cannot transition from terminal"):
            sm.transition(AutonomyState.EXECUTING)

    def test_escalating_is_terminal(self, sample_context_executing):
        """ESCALATING cannot transition anywhere."""
        sm = StateMachine(sample_context_executing, max_retries=0)
        # Transition to blocked first
        sm.transition(AutonomyState.BLOCKED)
        # Then escalate
        sm.transition(AutonomyState.ESCALATING)
        
        with pytest.raises(ValueError, match="Cannot transition from terminal"):
            sm.transition(AutonomyState.EXECUTING)


class TestRetryLogic:
    """Tests for retry handling."""

    def test_retry_increments_counter(self, sample_context):
        """Each retry increments the counter."""
        sm = StateMachine(sample_context, max_retries=3)
        
        # PLANNING -> EXECUTING -> BLOCKED -> EXECUTING (retry 1)
        sm.transition(AutonomyState.EXECUTING)
        sm.transition(AutonomyState.BLOCKED, "Failed")
        sm.transition(AutonomyState.EXECUTING, "Retry 1")
        assert sm.context.retry_count == 1

    def test_max_retries_enforced(self, sample_context):
        """Cannot retry beyond max_retries."""
        sm = StateMachine(sample_context, max_retries=1)
        
        # PLANNING -> EXECUTING -> BLOCKED -> EXECUTING (retry 1) -> BLOCKED
        sm.transition(AutonomyState.EXECUTING)
        sm.transition(AutonomyState.BLOCKED, "Failed 1")
        sm.transition(AutonomyState.EXECUTING, "Retry 1")
        sm.transition(AutonomyState.BLOCKED, "Failed 2")
        
        # Now at max retries
        with pytest.raises(ValueError, match="Maximum retries.*exceeded"):
            sm.transition(AutonomyState.EXECUTING)

    def test_can_retry_check(self, sample_context):
        """can_retry() returns correct value."""
        sm = StateMachine(sample_context, max_retries=2)
        
        # Start fresh - not blocked
        assert not sm.can_retry()
        
        # Move to blocked
        sm.transition(AutonomyState.EXECUTING)
        sm.transition(AutonomyState.BLOCKED)
        assert sm.can_retry()
        
        # Use one retry
        sm.transition(AutonomyState.EXECUTING)
        assert not sm.can_retry()  # Not blocked anymore
        
        # Block again
        sm.transition(AutonomyState.BLOCKED)
        assert sm.can_retry()  # One retry remaining
        
        # Use final retry
        sm.transition(AutonomyState.EXECUTING)
        sm.transition(AutonomyState.BLOCKED)
        assert not sm.can_retry()  # Max retries reached


class TestHandleBlocked:
    """Tests for handle_blocked method."""

    def test_handle_blocked_retries_if_available(self, sample_context):
        """handle_blocked retries if retries available."""
        sm = StateMachine(sample_context, max_retries=1)
        sm.transition(AutonomyState.EXECUTING)
        sm.transition(AutonomyState.BLOCKED, "Error")
        
        assert sm.current_state == AutonomyState.BLOCKED
        
        sm.handle_blocked("Retrying")
        assert sm.current_state == AutonomyState.EXECUTING
        assert sm.context.retry_count == 1

    def test_handle_blocked_escalates_if_no_retries(self, sample_context):
        """handle_blocked escalates if no retries left."""
        sm = StateMachine(sample_context, max_retries=0)
        sm.transition(AutonomyState.EXECUTING)
        sm.transition(AutonomyState.BLOCKED, "Error")
        
        sm.handle_blocked("No retries")
        assert sm.current_state == AutonomyState.ESCALATING
        assert sm.context.escalation_reason == "No retries"

    def test_handle_blocked_only_from_blocked_state(self, sample_context):
        """handle_blocked only valid from BLOCKED state."""
        sm = StateMachine(sample_context)
        
        with pytest.raises(ValueError, match="non-blocked state"):
            sm.handle_blocked("Error")


class TestTransitionHistory:
    """Tests for transition history tracking."""

    def test_transition_recorded(self, sample_context, state_machine):
        """Each transition is recorded in history."""
        initial_history_len = len(sample_context.transition_history)
        
        state_machine.transition(AutonomyState.EXECUTING, "Starting")
        
        assert len(sample_context.transition_history) == initial_history_len + 1
        last = sample_context.transition_history[-1]
        assert last.from_state == AutonomyState.PLANNING
        assert last.to_state == AutonomyState.EXECUTING
        assert last.reason == "Starting"

    def test_multiple_transitions_recorded(self, sample_context):
        """Multiple transitions create history trail."""
        sm = StateMachine(sample_context, max_retries=1)
        
        sm.transition(AutonomyState.EXECUTING, "Start")
        sm.transition(AutonomyState.BLOCKED, "Fail")
        sm.transition(AutonomyState.EXECUTING, "Retry")
        sm.transition(AutonomyState.COMPLETE, "Done")
        
        assert len(sample_context.transition_history) == 4

    def test_transition_timestamps(self, sample_context, state_machine):
        """Transitions have timestamps."""
        before = datetime.utcnow()
        state_machine.transition(AutonomyState.EXECUTING)
        after = datetime.utcnow()
        
        last = sample_context.transition_history[-1]
        assert before <= last.timestamp <= after


class TestTimeInState:
    """Tests for time tracking in states."""

    def test_time_in_initial_state(self, sample_context):
        """Time tracked from context creation."""
        sm = StateMachine(sample_context)
        import time
        time.sleep(0.01)  # Small delay
        
        time_in_state = sm.get_time_in_current_state()
        assert time_in_state >= 0.01

    def test_time_reset_on_transition(self, sample_context, state_machine):
        """Time resets after transition."""
        import time
        
        state_machine.transition(AutonomyState.EXECUTING)
        time.sleep(0.01)
        
        time_in_executing = state_machine.get_time_in_current_state()
        assert time_in_executing >= 0.01
        
        # After another transition, time should be minimal
        state_machine.transition(AutonomyState.BLOCKED)
        time_in_blocked = state_machine.get_time_in_current_state()
        assert time_in_blocked < 0.01  # Should be very small


class TestIsComplete:
    """Tests for completion checking."""

    def test_not_complete_initially(self, sample_context, state_machine):
        """PLANNING is not complete."""
        assert not state_machine.is_complete()

    def test_complete_after_completion(self, sample_context_executing):
        """COMPLETE state is complete."""
        sm = StateMachine(sample_context_executing)
        sm.transition(AutonomyState.COMPLETE)
        assert sm.is_complete()

    def test_complete_after_escalation(self, sample_context_executing):
        """ESCALATING state is complete."""
        sm = StateMachine(sample_context_executing, max_retries=0)
        sm.transition(AutonomyState.BLOCKED)
        sm.transition(AutonomyState.ESCALATING)
        assert sm.is_complete()

    def test_not_complete_while_executing(self, sample_context_executing):
        """EXECUTING is not complete."""
        sm = StateMachine(sample_context_executing)
        assert not sm.is_complete()


class TestStateMachineIntegration:
    """Integration tests for complete state lifecycles."""

    def test_happy_path_lifecycle(self):
        """Full happy path: PLANNING -> EXECUTING -> COMPLETE."""
        context = AutonomyContext(
            task_id="happy-task",
            state=AutonomyState.PLANNING,
        )
        sm = StateMachine(context)
        
        # PLANNING -> EXECUTING
        sm.transition(AutonomyState.EXECUTING, "Container healthy")
        assert sm.current_state == AutonomyState.EXECUTING
        
        # EXECUTING -> COMPLETE
        sm.transition(AutonomyState.COMPLETE, "Task finished")
        assert sm.current_state == AutonomyState.COMPLETE
        assert sm.is_complete()

    def test_retry_path_lifecycle(self):
        """Retry path: PLANNING -> EXECUTING -> BLOCKED -> EXECUTING -> COMPLETE."""
        context = AutonomyContext(
            task_id="retry-task",
            state=AutonomyState.PLANNING,
        )
        sm = StateMachine(context, max_retries=1)
        
        # PLANNING -> EXECUTING
        sm.transition(AutonomyState.EXECUTING, "Started")
        
        # EXECUTING -> BLOCKED (failure)
        sm.transition(AutonomyState.BLOCKED, "First failure")
        
        # BLOCKED -> EXECUTING (retry)
        sm.transition(AutonomyState.EXECUTING, "Retrying")
        assert sm.context.retry_count == 1
        
        # EXECUTING -> COMPLETE (success)
        sm.transition(AutonomyState.COMPLETE, "Success after retry")
        assert sm.current_state == AutonomyState.COMPLETE

    def test_escalation_path_lifecycle(self):
        """Escalation path: PLANNING -> EXECUTING -> BLOCKED -> ESCALATING."""
        context = AutonomyContext(
            task_id="escalation-task",
            state=AutonomyState.PLANNING,
        )
        sm = StateMachine(context, max_retries=0)  # No retries
        
        # PLANNING -> EXECUTING
        sm.transition(AutonomyState.EXECUTING, "Started")
        
        # EXECUTING -> BLOCKED -> ESCALATING
        sm.transition(AutonomyState.BLOCKED, "Failed")
        sm.handle_blocked("Critical error")
        
        assert sm.current_state == AutonomyState.ESCALATING
        assert sm.context.escalation_reason == "Critical error"
        assert sm.is_complete()

    def test_double_retry_then_escalation(self):
        """Double retry then escalation."""
        context = AutonomyContext(
            task_id="double-retry",
            state=AutonomyState.PLANNING,
        )
        sm = StateMachine(context, max_retries=2)
        
        # First failure and retry
        sm.transition(AutonomyState.EXECUTING)
        sm.transition(AutonomyState.BLOCKED)
        sm.handle_blocked("First error")
        assert sm.context.retry_count == 1
        assert sm.current_state == AutonomyState.EXECUTING
        
        # Second failure and retry
        sm.transition(AutonomyState.BLOCKED)
        sm.handle_blocked("Second error")
        assert sm.context.retry_count == 2
        assert sm.current_state == AutonomyState.EXECUTING
        
        # Third failure - escalate
        sm.transition(AutonomyState.BLOCKED)
        sm.handle_blocked("Third error - max retries")
        assert sm.current_state == AutonomyState.ESCALATING
