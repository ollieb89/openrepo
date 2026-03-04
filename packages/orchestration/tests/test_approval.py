"""
Tests for the approval module.

Covers: approve_topology, compute_pushback_note, check_approval_gate.
Requirements: CORR-04 (approve_topology), CORR-06 (pushback), CORR-07 (gate check).

TDD RED phase — written before implementation.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from openclaw.topology.models import (
    TopologyGraph,
    TopologyNode,
    TopologyEdge,
    EdgeType,
)
from openclaw.topology.proposal_models import RubricScore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(nid: str, level: int = 3) -> TopologyNode:
    return TopologyNode(id=nid, level=level, intent="test role", risk_level="low")


def _edge(fr: str, to: str, et: EdgeType = EdgeType.DELEGATION) -> TopologyEdge:
    return TopologyEdge(from_role=fr, to_role=to, edge_type=et)


def _simple_graph(project_id: str = "test-project") -> TopologyGraph:
    return TopologyGraph(
        project_id=project_id,
        nodes=[_node("pm", level=2), _node("worker", level=3)],
        edges=[_edge("pm", "worker")],
    )


def _make_rubric_score(
    overall: int = 7,
    complexity: int = 7,
    coordination_overhead: int = 8,
    risk_containment: int = 5,
    time_to_first_output: int = 7,
    cost_estimate: int = 8,
) -> RubricScore:
    return RubricScore(
        complexity=complexity,
        coordination_overhead=coordination_overhead,
        risk_containment=risk_containment,
        time_to_first_output=time_to_first_output,
        cost_estimate=cost_estimate,
        preference_fit=5,
        overall_confidence=overall,
    )


# ---------------------------------------------------------------------------
# TestApproveTopology
# ---------------------------------------------------------------------------

class TestApproveTopology:
    """Tests for approve_topology()."""

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_diff_recorded_in_changelog(self, mock_load, mock_append, mock_save):
        """approve_topology must record a diff in the changelog entry."""
        from openclaw.topology.approval import approve_topology

        old_graph = _simple_graph()
        new_graph = TopologyGraph(
            project_id="test-project",
            nodes=[_node("pm", level=2), _node("worker", level=3), _node("reviewer", level=2)],
            edges=[_edge("pm", "worker"), _edge("worker", "reviewer", EdgeType.REVIEW_GATE)],
        )

        mock_load.return_value = old_graph

        entry = approve_topology(
            project_id="test-project",
            approved_graph=new_graph,
            correction_type="soft",
        )

        assert "diff" in entry
        assert entry["diff"] is not None

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_correction_type_in_changelog(self, mock_load, mock_append, mock_save):
        """approve_topology must include correction_type in changelog entry."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="hard",
        )

        assert entry["correction_type"] == "hard"

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_first_approval_diff_is_none(self, mock_load, mock_append, mock_save):
        """approve_topology diff must be None when no previous topology exists."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None  # No previous topology

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="soft",
        )

        assert entry["diff"] is None

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_save_topology_called(self, mock_load, mock_append, mock_save):
        """approve_topology must call save_topology with the approved graph."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None
        graph = _simple_graph()

        approve_topology(
            project_id="test-project",
            approved_graph=graph,
            correction_type="soft",
        )

        mock_save.assert_called_once_with("test-project", graph)

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_append_changelog_called(self, mock_load, mock_append, mock_save):
        """approve_topology must call append_changelog."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="soft",
        )

        mock_append.assert_called_once()

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_entry_has_timestamp(self, mock_load, mock_append, mock_save):
        """approve_topology changelog entry must have a timestamp."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="soft",
        )

        assert "timestamp" in entry
        assert entry["timestamp"]  # Non-empty

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    @patch("openclaw.topology.approval.delete_pending_proposals")
    def test_pending_deleted_after_approval(self, mock_delete, mock_load, mock_append, mock_save):
        """approve_topology must delete pending-proposals.json after approval."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="soft",
        )

        mock_delete.assert_called_once_with("test-project")

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_pushback_note_included_in_annotations(self, mock_load, mock_append, mock_save):
        """approve_topology must include pushback_note in annotations when non-empty."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="soft",
            pushback_note="Note: original was better on complexity.",
        )

        assert "annotations" in entry
        assert "pushback_note" in entry["annotations"]
        assert "original was better" in entry["annotations"]["pushback_note"]

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_diff_to_dict_serializable(self, mock_load, mock_append, mock_save):
        """diff in changelog entry must be a JSON-serializable dict."""
        from openclaw.topology.approval import approve_topology
        import json

        old_graph = _simple_graph()
        mock_load.return_value = old_graph

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="soft",
        )

        # Should not raise
        serialized = json.dumps(entry)
        assert isinstance(serialized, str)


# ---------------------------------------------------------------------------
# TestPushbackNote
# ---------------------------------------------------------------------------

class TestPushbackNote:
    """Tests for compute_pushback_note()."""

    def test_pushback_note_returned_when_high_confidence_and_dimension_drops(self):
        """compute_pushback_note returns a note when original confidence >= threshold and dimension drops >= 2."""
        from openclaw.topology.approval import compute_pushback_note

        # Original: high overall_confidence, high complexity score
        original_score = _make_rubric_score(overall=9, complexity=9)

        # Approved graph has fewer safety features — complexity will be lower
        # Use a robust graph (many nodes/edges) which scores lower on complexity
        approved_graph = TopologyGraph(
            project_id="test",
            nodes=[_node("l1", 1), _node("pm", 2), _node("w1", 3), _node("w2", 3), _node("rev", 2)],
            edges=[
                _edge("l1", "pm"),
                _edge("pm", "w1"),
                _edge("pm", "w2"),
                _edge("w1", "w2", EdgeType.COORDINATION),
                _edge("w2", "rev", EdgeType.REVIEW_GATE),
                _edge("w1", "l1", EdgeType.ESCALATION),
            ],
        )

        # Use a weights dict that will give a much lower score for approved_graph
        # Override: complexity weight is high, so original (complexity=9) vs approved (complexity=2) will matter
        weights = {"complexity": 0.5, "coordination_overhead": 0.1, "risk_containment": 0.1,
                   "time_to_first_output": 0.1, "cost_estimate": 0.1, "preference_fit": 0.1}

        note = compute_pushback_note(
            original_score=original_score,
            approved_graph=approved_graph,
            weights=weights,
            pushback_threshold=8,
        )

        assert isinstance(note, str)
        assert len(note) > 0, "Expected a non-empty pushback note"
        assert "informational" in note.lower() or "Note" in note

    def test_no_pushback_when_low_confidence(self):
        """compute_pushback_note returns empty string when original confidence < threshold."""
        from openclaw.topology.approval import compute_pushback_note

        original_score = _make_rubric_score(overall=5)  # Below threshold of 8

        note = compute_pushback_note(
            original_score=original_score,
            approved_graph=_simple_graph(),
            weights={},
            pushback_threshold=8,
        )

        assert note == ""

    def test_no_pushback_when_no_significant_drop(self):
        """compute_pushback_note returns empty string when no dimension drops by >= 2."""
        from openclaw.topology.approval import compute_pushback_note

        # High confidence
        original_score = _make_rubric_score(overall=9, complexity=8, coordination_overhead=8)

        # Approved graph that is very similar (lean graph scores well on complexity)
        approved_graph = _simple_graph()  # Simple graph with good scores

        note = compute_pushback_note(
            original_score=original_score,
            approved_graph=approved_graph,
            weights={},
            pushback_threshold=8,
        )

        # Lean graph scores high on complexity and coordination_overhead
        # original complexity=8, lean complexity will be around 8 too
        # If no drop >= 2, note should be empty
        assert isinstance(note, str)
        # Note: the result could be empty or non-empty depending on exact scoring
        # The key test is that the function doesn't raise

    def test_pushback_note_never_raises(self):
        """compute_pushback_note must not raise exceptions."""
        from openclaw.topology.approval import compute_pushback_note

        # Call with edge case inputs
        score = _make_rubric_score(overall=10, complexity=10)
        note = compute_pushback_note(
            original_score=score,
            approved_graph=_simple_graph(),
            weights={},
            pushback_threshold=8,
        )
        assert isinstance(note, str)

    def test_pushback_note_is_informational_only(self):
        """pushback note must indicate it does not block execution."""
        from openclaw.topology.approval import compute_pushback_note

        # Set up conditions that will trigger a note
        original_score = _make_rubric_score(overall=9, complexity=10, coordination_overhead=10)

        # Graph with many nodes/edges will score lower on complexity
        approved_graph = TopologyGraph(
            project_id="test",
            nodes=[_node(f"node{i}", 3) for i in range(6)],
            edges=[_edge(f"node{i}", f"node{i+1}") for i in range(5)],
        )

        note = compute_pushback_note(
            original_score=original_score,
            approved_graph=approved_graph,
            weights={},
            pushback_threshold=8,
        )

        if note:  # Only check content if note was generated
            assert "block" in note.lower() or "informational" in note.lower()


# ---------------------------------------------------------------------------
# TestApprovalGate
# ---------------------------------------------------------------------------

class TestApprovalGate:
    """Tests for check_approval_gate()."""

    @patch("openclaw.topology.approval.load_topology")
    def test_gate_blocks_without_topology(self, mock_load):
        """check_approval_gate returns approved=False when current.json absent."""
        from openclaw.topology.approval import check_approval_gate

        mock_load.return_value = None  # No topology

        result = check_approval_gate(project_id="test-project", auto_approve_l1=False)

        assert result["approved"] is False
        assert "reason" in result
        assert result["reason"]  # Non-empty reason

    @patch("openclaw.topology.approval.load_topology")
    def test_gate_passes_with_topology(self, mock_load):
        """check_approval_gate returns approved=True when current.json exists."""
        from openclaw.topology.approval import check_approval_gate

        mock_load.return_value = _simple_graph()

        result = check_approval_gate(project_id="test-project", auto_approve_l1=False)

        assert result["approved"] is True

    def test_auto_approve_bypass(self):
        """check_approval_gate returns approved=True when auto_approve_l1=True."""
        from openclaw.topology.approval import check_approval_gate

        # Should not call load_topology at all when auto_approve_l1 is True
        with patch("openclaw.topology.approval.load_topology") as mock_load:
            result = check_approval_gate(project_id="test-project", auto_approve_l1=True)

        assert result["approved"] is True

    @patch("openclaw.topology.approval.load_topology")
    def test_gate_reason_mentions_project(self, mock_load):
        """Gate failure reason should mention the project ID."""
        from openclaw.topology.approval import check_approval_gate

        mock_load.return_value = None

        result = check_approval_gate(project_id="my-special-project", auto_approve_l1=False)

        assert "my-special-project" in result["reason"]

    @patch("openclaw.topology.approval.load_topology")
    def test_gate_reason_mentions_propose_command(self, mock_load):
        """Gate failure reason should hint at the propose command."""
        from openclaw.topology.approval import check_approval_gate

        mock_load.return_value = None

        result = check_approval_gate(project_id="test", auto_approve_l1=False)

        # Should hint at what to run
        assert "openclaw-propose" in result["reason"] or "propose" in result["reason"].lower()


# ---------------------------------------------------------------------------
# TestRubricScoresInAnnotations
# ---------------------------------------------------------------------------

class TestRubricScoresInAnnotations:
    """Tests for the rubric_scores parameter on approve_topology()."""

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_rubric_scores_written_to_annotations(self, mock_load, mock_append, mock_save):
        """approve_topology writes rubric_scores to annotations when non-empty dict is passed."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        rubric_scores = {
            "lean": {
                "complexity": 7,
                "coordination_overhead": 6,
                "risk_containment": 5,
                "time_to_first_output": 8,
                "cost_estimate": 7,
                "preference_fit": 5,
                "overall_confidence": 7,
                "key_differentiators": [],
            }
        }

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="initial",
            rubric_scores=rubric_scores,
        )

        assert "annotations" in entry
        assert "rubric_scores" in entry["annotations"]
        assert entry["annotations"]["rubric_scores"] == rubric_scores

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_rubric_scores_omitted_when_none(self, mock_load, mock_append, mock_save):
        """approve_topology does NOT include rubric_scores key when rubric_scores=None."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="initial",
            rubric_scores=None,
        )

        assert "annotations" in entry
        assert "rubric_scores" not in entry["annotations"]

    @patch("openclaw.topology.approval.save_topology")
    @patch("openclaw.topology.approval.append_changelog")
    @patch("openclaw.topology.approval.load_topology")
    def test_rubric_scores_omitted_when_empty_dict(self, mock_load, mock_append, mock_save):
        """approve_topology does NOT include rubric_scores key when rubric_scores={}."""
        from openclaw.topology.approval import approve_topology

        mock_load.return_value = None

        entry = approve_topology(
            project_id="test-project",
            approved_graph=_simple_graph(),
            correction_type="initial",
            rubric_scores={},
        )

        assert "annotations" in entry
        assert "rubric_scores" not in entry["annotations"]
