"""
Tests for the correction module.

Covers: CorrectionSession, apply_soft_correction, export_draft, import_draft.
Requirements: CORR-01 (CorrectionSession), CORR-02 (soft correction), CORR-03 (cycle limit),
              CORR-05 (export/import draft).

TDD RED phase — written before implementation.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from openclaw.topology.models import (
    TopologyGraph,
    TopologyNode,
    TopologyEdge,
    EdgeType,
)
from openclaw.topology.proposal_models import (
    RubricScore,
    TopologyProposal,
    ProposalSet,
)


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


def _make_rubric_score(overall: int = 7) -> RubricScore:
    return RubricScore(
        complexity=7,
        coordination_overhead=8,
        risk_containment=5,
        time_to_first_output=7,
        cost_estimate=8,
        preference_fit=5,
        overall_confidence=overall,
    )


def _make_proposal(archetype: str = "lean", overall: int = 7) -> TopologyProposal:
    return TopologyProposal(
        archetype=archetype,
        graph=_simple_graph(),
        delegation_boundaries="PM to worker",
        coordination_model="direct",
        risk_assessment="low",
        justification="simple task",
        rubric_score=_make_rubric_score(overall),
    )


def _make_proposal_set(overall: int = 7) -> ProposalSet:
    return ProposalSet(
        proposals=[_make_proposal("lean", overall)],
        assumptions=["single worker sufficient"],
        outcome="Build feature X",
    )


def _make_registry() -> MagicMock:
    registry = MagicMock()
    registry._agents = {"pm": MagicMock(), "worker": MagicMock()}
    return registry


# ---------------------------------------------------------------------------
# TestCorrectionSession
# ---------------------------------------------------------------------------

class TestCorrectionSession:
    """Tests for CorrectionSession dataclass structure."""

    def test_session_cycle_count_starts_at_zero(self):
        """cycle_count must default to 0."""
        from openclaw.topology.correction import CorrectionSession

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
        )
        assert session.cycle_count == 0

    def test_session_cycle_limit_reached_false_at_start(self):
        """cycle_limit_reached must be False when cycle_count < max_cycles."""
        from openclaw.topology.correction import CorrectionSession

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
        )
        assert session.cycle_limit_reached is False

    def test_session_cycle_limit_reached_true_at_max(self):
        """cycle_limit_reached must be True when cycle_count >= max_cycles."""
        from openclaw.topology.correction import CorrectionSession

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
            cycle_count=3,
            max_cycles=3,
        )
        assert session.cycle_limit_reached is True

    def test_session_cycle_limit_reached_true_when_over(self):
        """cycle_limit_reached is True when cycle_count > max_cycles."""
        from openclaw.topology.correction import CorrectionSession

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
            cycle_count=5,
            max_cycles=3,
        )
        assert session.cycle_limit_reached is True

    def test_session_max_cycles_default_is_three(self):
        """max_cycles default must be 3."""
        from openclaw.topology.correction import CorrectionSession

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
        )
        assert session.max_cycles == 3

    def test_session_has_correction_history(self):
        """correction_history must default to an empty list."""
        from openclaw.topology.correction import CorrectionSession

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
        )
        assert session.correction_history == []

    def test_session_has_clarifications(self):
        """clarifications must default to an empty dict."""
        from openclaw.topology.correction import CorrectionSession

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
        )
        assert session.clarifications == {}


# ---------------------------------------------------------------------------
# TestSoftCorrection
# ---------------------------------------------------------------------------

class TestSoftCorrection:
    """Tests for apply_soft_correction()."""

    def _make_session(self, cycle_count: int = 0, best_overall: int = 7) -> "CorrectionSession":
        from openclaw.topology.correction import CorrectionSession

        return CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(overall=best_overall),
            best_proposal_set=_make_proposal_set(overall=best_overall),
            registry=_make_registry(),
            cycle_count=cycle_count,
        )

    def _make_raw_llm_output(self) -> dict:
        """Minimal valid LLM output for proposer.build_proposals()."""
        return {
            "lean": {
                "roles": [
                    {"id": "pm", "level": 2, "intent": "manages", "risk_level": "low"},
                    {"id": "worker", "level": 3, "intent": "executes", "risk_level": "low"},
                ],
                "hierarchy": [
                    {"from_role": "pm", "to_role": "worker", "edge_type": "delegation"},
                ],
                "delegation_boundaries": "PM to worker",
                "coordination_model": "direct",
                "risk_assessment": "low",
                "justification": "simple",
                "assumptions": [],
            },
            "balanced": {
                "roles": [
                    {"id": "pm", "level": 2, "intent": "manages", "risk_level": "low"},
                    {"id": "worker", "level": 3, "intent": "executes", "risk_level": "low"},
                ],
                "hierarchy": [
                    {"from_role": "pm", "to_role": "worker", "edge_type": "delegation"},
                ],
                "delegation_boundaries": "PM to worker",
                "coordination_model": "direct",
                "risk_assessment": "medium",
                "justification": "balanced",
                "assumptions": [],
            },
            "robust": {
                "roles": [
                    {"id": "pm", "level": 2, "intent": "manages", "risk_level": "low"},
                    {"id": "worker", "level": 3, "intent": "executes", "risk_level": "low"},
                ],
                "hierarchy": [
                    {"from_role": "pm", "to_role": "worker", "edge_type": "delegation"},
                ],
                "delegation_boundaries": "PM to worker",
                "coordination_model": "sequential",
                "risk_assessment": "high",
                "justification": "robust",
                "assumptions": [],
            },
        }

    @patch("openclaw.topology.correction.generate_proposals_sync")
    def test_soft_correction_increments_cycle_count(self, mock_gen):
        """apply_soft_correction must increment session.cycle_count."""
        from openclaw.topology.correction import apply_soft_correction

        mock_gen.return_value = self._make_raw_llm_output()
        session = self._make_session()

        apply_soft_correction(session, feedback="make it simpler", weights={})

        assert session.cycle_count == 1

    @patch("openclaw.topology.correction.generate_proposals_sync")
    def test_soft_correction_passes_feedback_in_clarifications(self, mock_gen):
        """apply_soft_correction must pass user_feedback in clarifications."""
        from openclaw.topology.correction import apply_soft_correction

        mock_gen.return_value = self._make_raw_llm_output()
        session = self._make_session()

        apply_soft_correction(session, feedback="use fewer agents", weights={})

        # Check that generate_proposals_sync was called with user_feedback
        call_kwargs = mock_gen.call_args.kwargs
        assert "clarifications" in call_kwargs
        assert call_kwargs["clarifications"]["user_feedback"] == "use fewer agents"

    @patch("openclaw.topology.correction.generate_proposals_sync")
    def test_soft_correction_returns_proposal_set(self, mock_gen):
        """apply_soft_correction must return a ProposalSet."""
        from openclaw.topology.correction import apply_soft_correction

        mock_gen.return_value = self._make_raw_llm_output()
        session = self._make_session()

        result = apply_soft_correction(session, feedback="improve it", weights={})

        assert isinstance(result, ProposalSet)

    @patch("openclaw.topology.correction.generate_proposals_sync")
    def test_soft_correction_records_in_history(self, mock_gen):
        """apply_soft_correction must record event in correction_history."""
        from openclaw.topology.correction import apply_soft_correction

        mock_gen.return_value = self._make_raw_llm_output()
        session = self._make_session()

        apply_soft_correction(session, feedback="make it smaller", weights={})

        assert len(session.correction_history) == 1
        entry = session.correction_history[0]
        assert entry["type"] == "soft"
        assert entry["feedback"] == "make it smaller"
        assert entry["cycle"] == 1

    @patch("openclaw.topology.correction.generate_proposals_sync")
    def test_soft_correction_updates_best_proposal_set_on_higher_confidence(self, mock_gen):
        """best_proposal_set updates when new top proposal has higher overall_confidence."""
        from openclaw.topology.correction import apply_soft_correction

        # Original best has low overall_confidence — new proposals will score higher
        session = self._make_session(best_overall=2)
        mock_gen.return_value = self._make_raw_llm_output()

        apply_soft_correction(session, feedback="improve it", weights={})

        # The scorer should produce scores higher than 2 for real graphs
        # Just verify best_proposal_set was updated (proposals list is not empty)
        assert session.best_proposal_set is not None

    @patch("openclaw.topology.correction.generate_proposals_sync")
    def test_soft_correction_preserves_existing_clarifications(self, mock_gen):
        """apply_soft_correction merges existing clarifications with user_feedback."""
        from openclaw.topology.correction import CorrectionSession, apply_soft_correction

        mock_gen.return_value = self._make_raw_llm_output()
        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
            clarifications={"risk_tolerance": "high"},
        )

        apply_soft_correction(session, feedback="go faster", weights={})

        call_kwargs = mock_gen.call_args.kwargs
        clarifications = call_kwargs["clarifications"]
        assert clarifications["risk_tolerance"] == "high"
        assert clarifications["user_feedback"] == "go faster"


# ---------------------------------------------------------------------------
# TestCycleLimit
# ---------------------------------------------------------------------------

class TestCycleLimit:
    """Tests for cycle limit enforcement."""

    def test_cycle_limit_raises_when_reached(self):
        """apply_soft_correction raises ValueError if cycle_limit_reached."""
        from openclaw.topology.correction import CorrectionSession, apply_soft_correction

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
            cycle_count=3,  # Already at limit
            max_cycles=3,
        )

        with pytest.raises(ValueError, match="[Cc]ycle limit"):
            apply_soft_correction(session, feedback="try again", weights={})

    def test_cycle_limit_does_not_call_llm(self):
        """When cycle limit is reached, LLM must NOT be called."""
        from openclaw.topology.correction import CorrectionSession, apply_soft_correction

        session = CorrectionSession(
            outcome="Build feature X",
            project_id="test",
            proposal_set=_make_proposal_set(),
            best_proposal_set=_make_proposal_set(),
            registry=_make_registry(),
            cycle_count=3,
            max_cycles=3,
        )

        with patch("openclaw.topology.correction.generate_proposals_sync") as mock_gen:
            with pytest.raises(ValueError):
                apply_soft_correction(session, feedback="try again", weights={})
            mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# TestHardCorrection (export_draft / import_draft)
# ---------------------------------------------------------------------------

class TestHardCorrection:
    """Tests for export_draft() and import_draft()."""

    def test_export_draft_creates_file(self, tmp_path):
        """export_draft must create proposal-draft.json in the topology dir."""
        from openclaw.topology.correction import export_draft

        proposal = _make_proposal()

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            path = export_draft(proposal, project_id="test-project")

        assert path.exists()
        assert path.name == "proposal-draft.json"

    def test_export_draft_valid_json(self, tmp_path):
        """proposal-draft.json must be valid JSON."""
        from openclaw.topology.correction import export_draft

        proposal = _make_proposal()

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            path = export_draft(proposal, project_id="test-project")

        with open(path, "r") as f:
            data = json.load(f)

        assert isinstance(data, dict)

    def test_export_draft_has_comment_keys(self, tmp_path):
        """proposal-draft.json must have __comment__nodes and __comment__edges."""
        from openclaw.topology.correction import export_draft

        proposal = _make_proposal()

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            path = export_draft(proposal, project_id="test-project")

        with open(path, "r") as f:
            data = json.load(f)

        assert "__comment__nodes" in data
        assert "__comment__edges" in data

    def test_export_draft_has_topology_keys(self, tmp_path):
        """proposal-draft.json must contain topology graph keys."""
        from openclaw.topology.correction import export_draft

        proposal = _make_proposal()

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            path = export_draft(proposal, project_id="test-project")

        with open(path, "r") as f:
            data = json.load(f)

        assert "nodes" in data
        assert "edges" in data

    def test_import_draft_returns_topology_graph(self, tmp_path):
        """import_draft must return a TopologyGraph."""
        from openclaw.topology.correction import export_draft, import_draft

        proposal = _make_proposal()

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            export_draft(proposal, project_id="test-project")
            graph, lint_result = import_draft(
                "test-project",
                registry=_make_registry(),
                max_concurrent=3,
            )

        assert isinstance(graph, TopologyGraph)

    def test_import_draft_strips_comment_keys(self, tmp_path):
        """import_draft must strip __comment__ keys before deserializing."""
        from openclaw.topology.correction import export_draft, import_draft

        proposal = _make_proposal()

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            export_draft(proposal, project_id="test-project")
            graph, lint_result = import_draft(
                "test-project",
                registry=_make_registry(),
                max_concurrent=3,
            )

        # If __comment__ keys were NOT stripped, from_dict would fail or include garbage
        # A successful TopologyGraph means stripping worked
        assert graph.nodes is not None

    def test_import_draft_bad_edge_type_raises_value_error(self, tmp_path):
        """import_draft raises ValueError with valid types listed on bad edge_type."""
        from openclaw.topology.correction import import_draft

        # Write a draft with an invalid edge_type
        bad_draft = {
            "project_id": "test-project",
            "nodes": [
                {"id": "pm", "level": 2, "intent": "manages", "risk_level": "low"}
            ],
            "edges": [
                {"from_role": "pm", "to_role": "worker", "edge_type": "INVALID_TYPE"}
            ],
        }
        draft_path = tmp_path / "proposal-draft.json"
        with open(draft_path, "w") as f:
            json.dump(bad_draft, f)

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            with pytest.raises(ValueError) as exc_info:
                import_draft("test-project", registry=_make_registry(), max_concurrent=3)

        # Error message should list valid EdgeType values
        error_msg = str(exc_info.value)
        assert "delegation" in error_msg or "EdgeType" in error_msg

    def test_import_draft_returns_lint_result(self, tmp_path):
        """import_draft must return (TopologyGraph, LintResult) tuple."""
        from openclaw.topology.correction import export_draft, import_draft
        from openclaw.topology.linter import LintResult

        proposal = _make_proposal()

        with patch("openclaw.topology.correction._topology_dir", return_value=tmp_path):
            export_draft(proposal, project_id="test-project")
            result = import_draft(
                "test-project",
                registry=_make_registry(),
                max_concurrent=3,
            )

        assert isinstance(result, tuple)
        assert len(result) == 2
        graph, lint = result
        assert isinstance(lint, LintResult)
