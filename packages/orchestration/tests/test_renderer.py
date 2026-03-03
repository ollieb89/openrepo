"""
Tests for topology renderer — ASCII DAG and comparative matrix formatter.

TDD RED phase: tests written before implementation.
"""

import pytest
from unittest.mock import patch

from openclaw.topology.models import (
    TopologyGraph, TopologyNode, TopologyEdge, EdgeType,
)
from openclaw.topology.proposal_models import (
    RubricScore, TopologyProposal, ProposalSet,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(nid: str, level: int = 2) -> TopologyNode:
    return TopologyNode(id=nid, level=level, intent="test role", risk_level="low")


def _simple_chain() -> TopologyGraph:
    """Two nodes: clawdia_prime -> l3_worker (delegation)."""
    return TopologyGraph(
        project_id="test",
        nodes=[_node("clawdia_prime", level=1), _node("l3_worker", level=3)],
        edges=[
            TopologyEdge(
                from_role="clawdia_prime",
                to_role="l3_worker",
                edge_type=EdgeType.DELEGATION,
            )
        ],
    )


def _tree_with_multiple_children() -> TopologyGraph:
    """Three nodes: pm -> worker_a, pm -> worker_b (delegation), worker_a -> worker_b (coordination)."""
    return TopologyGraph(
        project_id="test",
        nodes=[
            _node("pm", level=2),
            _node("worker_a", level=3),
            _node("worker_b", level=3),
        ],
        edges=[
            TopologyEdge(from_role="pm", to_role="worker_a", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="pm", to_role="worker_b", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="worker_a", to_role="worker_b", edge_type=EdgeType.COORDINATION),
        ],
    )


def _make_proposal(archetype: str, topology: TopologyGraph, confidence: int = 5) -> TopologyProposal:
    score = RubricScore(
        complexity=5,
        coordination_overhead=5,
        risk_containment=5,
        time_to_first_output=5,
        cost_estimate=5,
        preference_fit=5,
        overall_confidence=confidence,
    )
    return TopologyProposal(
        archetype=archetype,
        topology=topology,
        delegation_boundaries=f"{archetype} boundaries",
        coordination_model="sequential",
        risk_assessment="low risk",
        justification=f"This is the {archetype} topology justification.",
        rubric_score=score,
    )


def _three_proposals() -> list:
    lean_graph = TopologyGraph(
        project_id="test",
        nodes=[_node("pm", level=2), _node("worker", level=3)],
        edges=[TopologyEdge(from_role="pm", to_role="worker", edge_type=EdgeType.DELEGATION)],
    )
    balanced_graph = _tree_with_multiple_children()
    robust_graph = TopologyGraph(
        project_id="test",
        nodes=[
            _node("l1", level=1), _node("pm", level=2),
            _node("worker_a", level=3), _node("worker_b", level=3),
        ],
        edges=[
            TopologyEdge(from_role="l1", to_role="pm", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="pm", to_role="worker_a", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="pm", to_role="worker_b", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="worker_b", to_role="l1", edge_type=EdgeType.REVIEW_GATE),
        ],
    )
    return [
        _make_proposal("lean", lean_graph, confidence=8),
        _make_proposal("balanced", balanced_graph, confidence=6),
        _make_proposal("robust", robust_graph, confidence=4),
    ]


# ---------------------------------------------------------------------------
# Tests: render_dag
# ---------------------------------------------------------------------------

class TestRenderDag:
    def test_render_dag_simple_chain(self):
        """Two nodes, one delegation edge — root node shown, child indented."""
        from openclaw.topology.renderer import render_dag
        graph = _simple_chain()
        output = render_dag(graph)
        assert "clawdia_prime" in output
        assert "l3_worker" in output
        # Child should appear after root with indentation or arrow
        lines = output.splitlines()
        root_line = next((i for i, l in enumerate(lines) if "clawdia_prime" in l), None)
        child_line = next((i for i, l in enumerate(lines) if "l3_worker" in l), None)
        assert root_line is not None
        assert child_line is not None
        assert child_line > root_line

    def test_render_dag_simple_chain_has_edge_label(self):
        """Edge type label appears in the rendered output."""
        from openclaw.topology.renderer import render_dag
        graph = _simple_chain()
        output = render_dag(graph)
        # "delegation" should appear somewhere in the edge rendering
        assert "delegation" in output.lower()

    def test_render_dag_tree_with_multiple_children(self):
        """Three nodes: pm has two children — both appear in output."""
        from openclaw.topology.renderer import render_dag
        graph = _tree_with_multiple_children()
        output = render_dag(graph)
        assert "pm" in output
        assert "worker_a" in output
        assert "worker_b" in output

    def test_render_dag_returns_string(self):
        """render_dag always returns a string."""
        from openclaw.topology.renderer import render_dag
        graph = _simple_chain()
        result = render_dag(graph)
        assert isinstance(result, str)

    def test_render_dag_empty_graph(self):
        """Empty graph returns a non-crashing string (may be empty or placeholder)."""
        from openclaw.topology.renderer import render_dag
        graph = TopologyGraph(project_id="test", nodes=[], edges=[])
        result = render_dag(graph)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tests: render_matrix
# ---------------------------------------------------------------------------

class TestRenderMatrix:
    def test_render_matrix_three_proposals_contains_dimension_names(self):
        """Matrix output includes all 6 rubric dimension names."""
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        output = render_matrix(proposals, key_differentiators=[])
        for dim in ["complexity", "coordination", "risk", "time", "cost", "preference"]:
            assert dim.lower() in output.lower(), f"Dimension '{dim}' missing from matrix"

    def test_render_matrix_three_proposals_contains_archetype_names(self):
        """Matrix output includes all archetype names as column headers."""
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        output = render_matrix(proposals, key_differentiators=[])
        assert "lean" in output.lower()
        assert "balanced" in output.lower()
        assert "robust" in output.lower()

    def test_render_matrix_key_differentiators_marked(self):
        """Dimensions in key_differentiators are marked with * in the matrix."""
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        output = render_matrix(proposals, key_differentiators=["complexity"])
        assert "*" in output

    def test_render_matrix_preference_fit_has_tilde(self):
        """Preference fit cells get ~ suffix (no correction history yet)."""
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        output = render_matrix(proposals, key_differentiators=[])
        assert "~" in output

    def test_render_matrix_returns_string(self):
        """render_matrix always returns a string."""
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        result = render_matrix(proposals, key_differentiators=[])
        assert isinstance(result, str)

    def test_stacked_layout_when_narrow(self):
        """When terminal width < 100, stacked layout is used (no side-by-side columns)."""
        from unittest.mock import MagicMock
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        mock_size = MagicMock()
        mock_size.columns = 80
        with patch("shutil.get_terminal_size", return_value=mock_size):
            output = render_matrix(proposals, key_differentiators=[])
        # Stacked layout: each archetype appears as a separate section
        assert "lean" in output.lower()
        assert isinstance(output, str)

    def test_wide_layout_when_wide_terminal(self):
        """When terminal width >= 100, wide side-by-side layout is used."""
        from unittest.mock import MagicMock
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        mock_size = MagicMock()
        mock_size.columns = 120
        with patch("shutil.get_terminal_size", return_value=mock_size):
            output = render_matrix(proposals, key_differentiators=[])
        assert "lean" in output.lower()
        assert isinstance(output, str)


# ---------------------------------------------------------------------------
# Tests: render_assumptions
# ---------------------------------------------------------------------------

class TestRenderAssumptions:
    def test_render_assumptions_format(self):
        """Assumptions block has ASSUMPTIONS header and bullet items."""
        from openclaw.topology.renderer import render_assumptions
        assumptions = ["risk tolerance: medium", "timeline pressure: moderate"]
        output = render_assumptions(assumptions)
        assert "ASSUMPTIONS" in output.upper()
        assert "risk tolerance" in output.lower()
        assert "timeline pressure" in output.lower()

    def test_render_assumptions_empty_list(self):
        """Empty assumptions returns a string without crashing."""
        from openclaw.topology.renderer import render_assumptions
        output = render_assumptions([])
        assert isinstance(output, str)

    def test_render_assumptions_returns_string(self):
        """render_assumptions always returns a string."""
        from openclaw.topology.renderer import render_assumptions
        result = render_assumptions(["a", "b"])
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Tests: proposals ordered by confidence descending
# ---------------------------------------------------------------------------

class TestProposalOrdering:
    def test_proposals_ordered_by_confidence_descending(self):
        """
        render_full_output must present proposals with highest confidence first.
        The three_proposals fixture has lean=8, balanced=6, robust=4.
        So in the output, lean should appear before balanced, which should appear before robust.
        """
        from openclaw.topology.renderer import render_matrix
        proposals = _three_proposals()
        # Sort externally to simulate what CLI does
        sorted_proposals = sorted(
            proposals,
            key=lambda p: (p.rubric_score.overall_confidence if p.rubric_score else 0),
            reverse=True,
        )
        output = render_matrix(sorted_proposals, key_differentiators=[])
        # In wide layout, lean should appear as first column
        # In stacked layout, lean section should appear first
        lean_pos = output.lower().find("lean")
        balanced_pos = output.lower().find("balanced")
        assert lean_pos < balanced_pos, (
            f"lean (pos={lean_pos}) should appear before balanced (pos={balanced_pos})"
        )


# ---------------------------------------------------------------------------
# Tests: render_low_confidence_warning
# ---------------------------------------------------------------------------

class TestLowConfidenceWarning:
    def test_warning_shown_when_confidence_below_threshold(self):
        """Low confidence warning appears when any proposal < threshold."""
        from openclaw.topology.renderer import render_low_confidence_warning
        proposals = _three_proposals()  # robust has confidence=4, threshold=5
        output = render_low_confidence_warning(proposals, threshold=5)
        assert len(output) > 0  # Warning text present

    def test_no_warning_when_all_above_threshold(self):
        """No warning when all proposals are above threshold."""
        from openclaw.topology.renderer import render_low_confidence_warning
        lean_graph = TopologyGraph(
            project_id="test",
            nodes=[_node("pm")],
            edges=[],
        )
        proposals = [_make_proposal("lean", lean_graph, confidence=8)]
        output = render_low_confidence_warning(proposals, threshold=5)
        assert output == ""


# ---------------------------------------------------------------------------
# Tests: render_full_output
# ---------------------------------------------------------------------------

class TestRenderFullOutput:
    def test_render_full_output_returns_string(self):
        """render_full_output returns a non-empty string."""
        from openclaw.topology.renderer import render_full_output
        lean_graph = TopologyGraph(
            project_id="test",
            nodes=[_node("pm")],
            edges=[],
        )
        proposal_set = ProposalSet(
            proposals=[_make_proposal("lean", lean_graph, confidence=8)],
            assumptions=["Risk: medium"],
            outcome="Build a chat app",
        )
        output = render_full_output(proposal_set, threshold=5)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_render_full_output_includes_assumptions(self):
        """Full output includes the assumptions section."""
        from openclaw.topology.renderer import render_full_output
        lean_graph = TopologyGraph(
            project_id="test",
            nodes=[_node("pm")],
            edges=[],
        )
        proposal_set = ProposalSet(
            proposals=[_make_proposal("lean", lean_graph, confidence=7)],
            assumptions=["Risk tolerance: medium"],
            outcome="Build something",
        )
        output = render_full_output(proposal_set, threshold=5)
        assert "risk tolerance" in output.lower()
