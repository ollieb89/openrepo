"""
Tests for the openclaw-propose CLI entry point.

Tests focus on argument parsing, error handling, importability, and the
interactive session loop (soft correction, hard correction, approval, quit,
cycle limit).

LLM calls are not invoked — no real API calls.
"""

import sys
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Tests: importability
# ---------------------------------------------------------------------------

class TestCliImportable:
    def test_main_function_importable(self):
        """from openclaw.cli.propose import main should succeed."""
        from openclaw.cli.propose import main
        assert callable(main)

    def test_colors_class_importable(self):
        """Colors class with ANSI codes should be importable."""
        from openclaw.cli.propose import Colors
        assert hasattr(Colors, "RED")
        assert hasattr(Colors, "GREEN")
        assert hasattr(Colors, "RESET")

    def test_is_interactive_importable(self):
        """_is_interactive() helper should be importable."""
        from openclaw.cli.propose import _is_interactive
        assert callable(_is_interactive)

    def test_to_pm_proposals_importable(self):
        """_to_pm_proposals() conversion helper should be importable."""
        from openclaw.cli.propose import _to_pm_proposals
        assert callable(_to_pm_proposals)

    def test_parse_selection_importable(self):
        """_parse_selection() helper should be importable."""
        from openclaw.cli.propose import _parse_selection
        assert callable(_parse_selection)


# ---------------------------------------------------------------------------
# Tests: argument parsing
# ---------------------------------------------------------------------------

class TestCliArgparse:
    def _parse(self, argv: list):
        """Parse arguments using argparse directly (without calling main)."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("outcome", nargs="?")
        parser.add_argument("--project", dest="project", type=str, default=None)
        parser.add_argument("--fresh", dest="fresh", action="store_true")
        parser.add_argument("--json", dest="json", action="store_true")
        parser.add_argument("--edit", dest="edit", action="store_true")
        return parser.parse_args(argv)

    def test_cli_parse_args_outcome(self):
        """Positional outcome argument is parsed correctly."""
        args = self._parse(["build a chat app"])
        assert args.outcome == "build a chat app"

    def test_cli_parse_args_no_outcome(self):
        """Missing outcome results in None (handled at runtime)."""
        args = self._parse([])
        assert args.outcome is None

    def test_cli_parse_args_project_flag(self):
        """--project flag is parsed correctly."""
        args = self._parse(["build something", "--project", "myproj"])
        assert args.project == "myproj"

    def test_cli_parse_args_fresh_flag(self):
        """--fresh flag is parsed as True when present."""
        args = self._parse(["--fresh", "build something"])
        assert args.fresh is True

    def test_cli_parse_args_fresh_false_by_default(self):
        """--fresh flag defaults to False."""
        args = self._parse(["build something"])
        assert args.fresh is False

    def test_cli_parse_args_json_flag(self):
        """--json flag is parsed as True when present."""
        args = self._parse(["build something", "--json"])
        assert args.json is True

    def test_cli_parse_args_json_false_by_default(self):
        """--json flag defaults to False."""
        args = self._parse(["build something"])
        assert args.json is False

    def test_cli_parse_args_edit_flag(self):
        """--edit flag is parsed as True when present."""
        args = self._parse(["build something", "--edit"])
        assert args.edit is True

    def test_cli_parse_args_edit_false_by_default(self):
        """--edit flag defaults to False."""
        args = self._parse(["build something"])
        assert args.edit is False

    def test_cli_parse_args_all_flags(self):
        """All flags can be combined."""
        args = self._parse(["--fresh", "--json", "--project", "proj1", "deploy"])
        assert args.fresh is True
        assert args.json is True
        assert args.project == "proj1"
        assert args.outcome == "deploy"


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------

class TestCliErrorHandling:
    def test_cli_no_outcome_returns_error(self):
        """main() returns 1 when no outcome is provided in non-interactive mode."""
        from openclaw.cli.propose import main

        # Mock: non-interactive + empty stdin + active project
        with patch("sys.argv", ["openclaw-propose"]):
            with patch("openclaw.cli.propose._is_interactive", return_value=False):
                with patch("sys.stdin") as mock_stdin:
                    mock_stdin.read.return_value = ""
                    with patch("openclaw.cli.propose.get_active_project_id", return_value="testproj"):
                        ret = main()
        assert ret == 1

    def test_cli_no_project_returns_error(self):
        """main() returns 1 when no project can be resolved."""
        from openclaw.cli.propose import main

        with patch("sys.argv", ["openclaw-propose", "build something"]):
            with patch("openclaw.cli.propose._is_interactive", return_value=False):
                with patch("openclaw.cli.propose.get_active_project_id", return_value=None):
                    ret = main()
        assert ret == 1


# ---------------------------------------------------------------------------
# Tests: proposal conversion helper
# ---------------------------------------------------------------------------

class TestToPmProposals:
    def test_converts_proposer_proposals_to_pm_format(self):
        """_to_pm_proposals returns unified TopologyProposal objects with .graph field.

        Since proposer.build_proposals() now returns canonical proposal_models.TopologyProposal
        objects directly, _to_pm_proposals is a pass-through that returns the same objects.
        """
        from openclaw.cli.propose import _to_pm_proposals
        from openclaw.topology.models import TopologyGraph, TopologyNode
        from openclaw.topology.proposal_models import TopologyProposal

        # Create a real TopologyProposal (as build_proposals() now returns)
        mock_graph = TopologyGraph(
            project_id="test",
            nodes=[TopologyNode(id="pm", level=2, intent="test", risk_level="low")],
            edges=[],
        )
        proposal = TopologyProposal(
            archetype="lean",
            graph=mock_graph,
            delegation_boundaries="L2 only",
            coordination_model="sequential",
            risk_assessment="low",
            justification="simple",
        )

        result = _to_pm_proposals([proposal])

        assert len(result) == 1
        assert result[0].archetype == "lean"
        assert result[0].graph is mock_graph
        assert result[0].delegation_boundaries == "L2 only"
        assert result[0].rubric_score is None  # Not scored yet

    def test_converts_empty_list(self):
        """_to_pm_proposals handles empty input gracefully."""
        from openclaw.cli.propose import _to_pm_proposals
        result = _to_pm_proposals([])
        assert result == []


# ---------------------------------------------------------------------------
# Fixtures: helpers for interactive session tests
# ---------------------------------------------------------------------------

def _make_proposal_set(archetype="lean"):
    """Create a minimal ProposalSet for testing."""
    from openclaw.topology.models import TopologyGraph, TopologyNode
    from openclaw.topology.proposal_models import ProposalSet, RubricScore, TopologyProposal

    node = TopologyNode(id="pm", level=2, intent="test", risk_level="low")
    graph = TopologyGraph(project_id="testproj", nodes=[node], edges=[])
    score = RubricScore(
        complexity=7,
        coordination_overhead=6,
        risk_containment=5,
        time_to_first_output=8,
        cost_estimate=7,
        preference_fit=5,
        overall_confidence=7,
    )
    proposal = TopologyProposal(
        archetype=archetype,
        graph=graph,
        delegation_boundaries="L2 only",
        coordination_model="sequential",
        risk_assessment="low",
        justification="Simple approach.",
        rubric_score=score,
    )
    return ProposalSet(
        proposals=[proposal],
        assumptions=["risk: low"],
        outcome="build something",
    )


def _make_main_patches(interactive=True, input_side_effect=None):
    """Return a context manager stack for mocking the full main() pipeline."""
    from openclaw.topology.models import TopologyGraph, TopologyNode
    from openclaw.topology.proposal_models import ProposalSet, RubricScore, TopologyProposal

    proposal_set = _make_proposal_set("lean")
    # Mock proposer proposals (proposer format uses .graph not .topology)
    mock_proposer_prop = MagicMock()
    mock_proposer_prop.archetype = "lean"
    mock_proposer_prop.graph = proposal_set.proposals[0].graph
    mock_proposer_prop.delegation_boundaries = "L2 only"
    mock_proposer_prop.coordination_model = "sequential"
    mock_proposer_prop.risk_assessment = "low"
    mock_proposer_prop.justification = "Simple approach."

    return mock_proposer_prop, proposal_set


# ---------------------------------------------------------------------------
# Tests: _parse_selection helper
# ---------------------------------------------------------------------------

class TestParseSelection:
    def test_parse_by_index_1(self):
        """'approve 1' selects the first proposal by 1-based index."""
        from openclaw.cli.propose import _parse_selection

        proposal_set = _make_proposal_set("lean")
        result = _parse_selection("approve 1", proposal_set)
        assert result is not None
        assert result.archetype == "lean"

    def test_parse_by_archetype_name(self):
        """'approve lean' selects by archetype name."""
        from openclaw.cli.propose import _parse_selection

        proposal_set = _make_proposal_set("lean")
        result = _parse_selection("approve lean", proposal_set)
        assert result is not None
        assert result.archetype == "lean"

    def test_parse_approve_bare(self):
        """'approve' without number selects first proposal."""
        from openclaw.cli.propose import _parse_selection

        proposal_set = _make_proposal_set("lean")
        result = _parse_selection("approve", proposal_set)
        assert result is not None
        assert result.archetype == "lean"

    def test_parse_invalid_returns_none(self):
        """'approve 99' with out-of-range index returns None."""
        from openclaw.cli.propose import _parse_selection

        proposal_set = _make_proposal_set("lean")
        result = _parse_selection("approve 99", proposal_set)
        assert result is None

    def test_parse_edit_by_index(self):
        """'edit 1' selects first proposal."""
        from openclaw.cli.propose import _parse_selection

        proposal_set = _make_proposal_set("lean")
        result = _parse_selection("edit 1", proposal_set)
        assert result is not None
        assert result.archetype == "lean"


# ---------------------------------------------------------------------------
# Tests: interactive session loop
# ---------------------------------------------------------------------------

class TestInteractiveSessionLoop:
    """Tests for the interactive correction/approval loop in main()."""

    def _run_main_interactive(self, argv, input_responses):
        """
        Run main() with mocked interactive environment.

        Mocks: _is_interactive=True, generate_proposals_sync, input builtin,
        save_pending_proposals, approve_topology, apply_soft_correction.
        """
        from openclaw.cli.propose import main
        from openclaw.topology.models import TopologyGraph, TopologyNode

        node = TopologyNode(id="pm", level=2, intent="test", risk_level="low")
        graph = TopologyGraph(project_id="testproj", nodes=[node], edges=[])

        mock_proposer_prop = MagicMock()
        mock_proposer_prop.archetype = "lean"
        mock_proposer_prop.graph = graph
        mock_proposer_prop.delegation_boundaries = "L2 only"
        mock_proposer_prop.coordination_model = "sequential"
        mock_proposer_prop.risk_assessment = "low"
        mock_proposer_prop.justification = "Simple approach."

        with patch("sys.argv", argv):
            with patch("openclaw.cli.propose._is_interactive", return_value=True):
                with patch("openclaw.cli.propose.get_active_project_id", return_value="testproj"):
                    with patch("openclaw.cli.propose.AgentRegistry") as mock_reg:
                        mock_reg.return_value._agents = {}
                        with patch("openclaw.cli.propose.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.propose.ask_clarifications", return_value={}):
                                with patch("openclaw.cli.propose.generate_proposals_sync", return_value={
                                    "lean": {"roles": [], "edges": [], "assumptions": []},
                                }):
                                    with patch("openclaw.cli.propose._build_proposer_proposals",
                                               return_value=[mock_proposer_prop]):
                                        with patch("openclaw.cli.propose.ConstraintLinter") as mock_linter:
                                            lint_result = MagicMock()
                                            lint_result.valid = True
                                            lint_result.adjusted = False
                                            lint_result.rejected_roles = []
                                            mock_linter.return_value.lint.return_value = lint_result
                                            with patch("openclaw.cli.propose.score_proposal") as mock_score:
                                                from openclaw.topology.proposal_models import RubricScore
                                                mock_score.return_value = RubricScore(
                                                    complexity=7, coordination_overhead=6,
                                                    risk_containment=5, time_to_first_output=8,
                                                    cost_estimate=7, preference_fit=5,
                                                    overall_confidence=7,
                                                )
                                                with patch("openclaw.cli.propose.find_key_differentiators", return_value=[]):
                                                    with patch("openclaw.cli.propose.ArchetypeClassifier") as mock_cls:
                                                        mock_cls.return_value.classify.return_value = MagicMock(archetype="lean")
                                                        with patch("openclaw.cli.propose.save_pending_proposals") as mock_save:
                                                            with patch("openclaw.cli.propose.approve_topology") as mock_approve:
                                                                with patch("openclaw.cli.propose.apply_soft_correction") as mock_soft:
                                                                    with patch("builtins.input", side_effect=input_responses):
                                                                        ret = main()
                                                                        return ret, mock_save, mock_approve, mock_soft

    def test_non_interactive_no_loop(self):
        """Non-interactive mode: main() returns 0 without entering session loop."""
        from openclaw.cli.propose import main
        from openclaw.topology.models import TopologyGraph, TopologyNode

        node = TopologyNode(id="pm", level=2, intent="test", risk_level="low")
        graph = TopologyGraph(project_id="testproj", nodes=[node], edges=[])
        mock_prop = MagicMock()
        mock_prop.archetype = "lean"
        mock_prop.graph = graph
        mock_prop.delegation_boundaries = "L2 only"
        mock_prop.coordination_model = "sequential"
        mock_prop.risk_assessment = "low"
        mock_prop.justification = "Simple."

        input_called = []

        def mock_input(prompt=""):
            input_called.append(prompt)
            return "approve 1"

        with patch("sys.argv", ["openclaw-propose", "build something"]):
            with patch("openclaw.cli.propose._is_interactive", return_value=False):
                with patch("openclaw.cli.propose.get_active_project_id", return_value="testproj"):
                    with patch("openclaw.cli.propose.AgentRegistry") as mock_reg:
                        mock_reg.return_value._agents = {}
                        with patch("openclaw.cli.propose.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.propose.ask_clarifications", return_value={}):
                                with patch("openclaw.cli.propose.generate_proposals_sync", return_value={
                                    "lean": {"roles": [], "edges": [], "assumptions": []},
                                }):
                                    with patch("openclaw.cli.propose._build_proposer_proposals",
                                               return_value=[mock_prop]):
                                        with patch("openclaw.cli.propose.ConstraintLinter") as mock_linter:
                                            lr = MagicMock()
                                            lr.valid = True
                                            lr.adjusted = False
                                            lr.rejected_roles = []
                                            mock_linter.return_value.lint.return_value = lr
                                            with patch("openclaw.cli.propose.score_proposal") as mock_score:
                                                from openclaw.topology.proposal_models import RubricScore
                                                mock_score.return_value = RubricScore(
                                                    complexity=7, coordination_overhead=6,
                                                    risk_containment=5, time_to_first_output=8,
                                                    cost_estimate=7, preference_fit=5,
                                                    overall_confidence=7,
                                                )
                                                with patch("openclaw.cli.propose.find_key_differentiators", return_value=[]):
                                                    with patch("openclaw.cli.propose.ArchetypeClassifier") as mock_cls:
                                                        mock_cls.return_value.classify.return_value = MagicMock(archetype="lean")
                                                        with patch("builtins.input", side_effect=mock_input):
                                                            ret = main()

        # Non-interactive: should not enter session loop
        # input() called at most once during outcome prompt resolution
        # (but since outcome provided via argv, no input call for outcome)
        # The session loop should never call input()
        assert ret == 0
        # input should NOT have been called for the session loop
        # (it might have been called for clarifications but not session)
        assert len(input_called) == 0

    def test_interactive_approve(self):
        """Interactive: 'approve 1' calls approve_topology and returns 0."""
        ret, mock_save, mock_approve, mock_soft = self._run_main_interactive(
            ["openclaw-propose", "build something"],
            ["approve 1"],  # immediate approve
        )
        assert ret == 0
        mock_approve.assert_called_once()
        # First call arg: project_id
        call_args = mock_approve.call_args
        assert call_args[0][0] == "testproj"

    def test_interactive_quit(self):
        """Interactive: 'quit' saves pending proposals and returns 0."""
        ret, mock_save, mock_approve, mock_soft = self._run_main_interactive(
            ["openclaw-propose", "build something"],
            ["quit"],
        )
        assert ret == 0
        mock_approve.assert_not_called()
        # save_pending_proposals called (at least for initial save + quit save)
        assert mock_save.call_count >= 1

    def test_interactive_feedback_then_approve(self):
        """Interactive: feedback text triggers soft correction, then 'approve 1' approves."""
        from openclaw.cli.propose import main
        from openclaw.topology.models import TopologyGraph, TopologyNode
        from openclaw.topology.proposal_models import ProposalSet, RubricScore, TopologyProposal

        node = TopologyNode(id="pm", level=2, intent="test", risk_level="low")
        graph = TopologyGraph(project_id="testproj", nodes=[node], edges=[])

        mock_proposer_prop = MagicMock()
        mock_proposer_prop.archetype = "lean"
        mock_proposer_prop.graph = graph
        mock_proposer_prop.delegation_boundaries = "L2 only"
        mock_proposer_prop.coordination_model = "sequential"
        mock_proposer_prop.risk_assessment = "low"
        mock_proposer_prop.justification = "Simple approach."

        score = RubricScore(
            complexity=7, coordination_overhead=6,
            risk_containment=5, time_to_first_output=8,
            cost_estimate=7, preference_fit=5,
            overall_confidence=7,
        )
        proposal = TopologyProposal(
            archetype="lean",
            graph=graph,
            delegation_boundaries="L2 only",
            coordination_model="sequential",
            risk_assessment="low",
            justification="Simple.",
            rubric_score=score,
        )
        new_proposal_set = ProposalSet(
            proposals=[proposal],
            assumptions=[],
            outcome="build something",
        )

        with patch("sys.argv", ["openclaw-propose", "build something"]):
            with patch("openclaw.cli.propose._is_interactive", return_value=True):
                with patch("openclaw.cli.propose.get_active_project_id", return_value="testproj"):
                    with patch("openclaw.cli.propose.AgentRegistry") as mock_reg:
                        mock_reg.return_value._agents = {}
                        with patch("openclaw.cli.propose.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.propose.ask_clarifications", return_value={}):
                                with patch("openclaw.cli.propose.generate_proposals_sync", return_value={
                                    "lean": {"roles": [], "edges": [], "assumptions": []},
                                }):
                                    with patch("openclaw.cli.propose._build_proposer_proposals",
                                               return_value=[mock_proposer_prop]):
                                        with patch("openclaw.cli.propose.ConstraintLinter") as mock_linter:
                                            lr = MagicMock()
                                            lr.valid = True
                                            lr.adjusted = False
                                            lr.rejected_roles = []
                                            mock_linter.return_value.lint.return_value = lr
                                            with patch("openclaw.cli.propose.score_proposal") as mock_score:
                                                mock_score.return_value = score
                                                with patch("openclaw.cli.propose.find_key_differentiators", return_value=[]):
                                                    with patch("openclaw.cli.propose.ArchetypeClassifier") as mock_cls:
                                                        mock_cls.return_value.classify.return_value = MagicMock(archetype="lean")
                                                        with patch("openclaw.cli.propose.save_pending_proposals"):
                                                            with patch("openclaw.cli.propose.approve_topology") as mock_approve:
                                                                with patch("openclaw.cli.propose.apply_soft_correction",
                                                                           return_value=new_proposal_set) as mock_soft:
                                                                    with patch("openclaw.cli.propose.render_diff_summary", return_value="diff"):
                                                                        with patch("builtins.input", side_effect=["flatten hierarchy", "approve 1"]):
                                                                            ret = main()

        assert ret == 0
        mock_soft.assert_called_once()
        feedback_arg = mock_soft.call_args[0][1]
        assert feedback_arg == "flatten hierarchy"
        mock_approve.assert_called_once()

    def test_interactive_cycle_limit(self):
        """After max_cycles feedbacks, system shows best proposals."""
        from openclaw.cli.propose import main
        from openclaw.topology.models import TopologyGraph, TopologyNode
        from openclaw.topology.proposal_models import ProposalSet, RubricScore, TopologyProposal

        node = TopologyNode(id="pm", level=2, intent="test", risk_level="low")
        graph = TopologyGraph(project_id="testproj", nodes=[node], edges=[])

        mock_proposer_prop = MagicMock()
        mock_proposer_prop.archetype = "lean"
        mock_proposer_prop.graph = graph
        mock_proposer_prop.delegation_boundaries = "L2 only"
        mock_proposer_prop.coordination_model = "sequential"
        mock_proposer_prop.risk_assessment = "low"
        mock_proposer_prop.justification = "Simple approach."

        score = RubricScore(
            complexity=7, coordination_overhead=6,
            risk_containment=5, time_to_first_output=8,
            cost_estimate=7, preference_fit=5,
            overall_confidence=7,
        )
        proposal = TopologyProposal(
            archetype="lean", graph=graph,
            delegation_boundaries="L2 only", coordination_model="sequential",
            risk_assessment="low", justification="Simple.", rubric_score=score,
        )
        new_set = ProposalSet(proposals=[proposal], assumptions=[], outcome="build something")

        printed_lines = []

        with patch("sys.argv", ["openclaw-propose", "build something"]):
            with patch("openclaw.cli.propose._is_interactive", return_value=True):
                with patch("openclaw.cli.propose.get_active_project_id", return_value="testproj"):
                    with patch("openclaw.cli.propose.AgentRegistry") as mock_reg:
                        mock_reg.return_value._agents = {}
                        with patch("openclaw.cli.propose.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.propose.ask_clarifications", return_value={}):
                                with patch("openclaw.cli.propose.generate_proposals_sync", return_value={
                                    "lean": {"roles": [], "edges": [], "assumptions": []},
                                }):
                                    with patch("openclaw.cli.propose._build_proposer_proposals",
                                               return_value=[mock_proposer_prop]):
                                        with patch("openclaw.cli.propose.ConstraintLinter") as mock_linter:
                                            lr = MagicMock()
                                            lr.valid = True
                                            lr.adjusted = False
                                            lr.rejected_roles = []
                                            mock_linter.return_value.lint.return_value = lr
                                            with patch("openclaw.cli.propose.score_proposal", return_value=score):
                                                with patch("openclaw.cli.propose.find_key_differentiators", return_value=[]):
                                                    with patch("openclaw.cli.propose.ArchetypeClassifier") as mock_cls:
                                                        mock_cls.return_value.classify.return_value = MagicMock(archetype="lean")
                                                        with patch("openclaw.cli.propose.save_pending_proposals"):
                                                            with patch("openclaw.cli.propose.approve_topology"):
                                                                def soft_correction_side_effect(session, feedback, weights):
                                                                    session.cycle_count += 1
                                                                    return new_set

                                                                with patch("openclaw.cli.propose.apply_soft_correction",
                                                                           side_effect=soft_correction_side_effect) as mock_soft:
                                                                    with patch("openclaw.cli.propose.render_diff_summary", return_value="diff"):
                                                                        with patch("builtins.print", side_effect=lambda *a, **k: printed_lines.append(" ".join(str(x) for x in a))):
                                                                            with patch("builtins.input", side_effect=[
                                                                                "feedback 1",
                                                                                "feedback 2",
                                                                                "feedback 3",
                                                                                "approve 1",
                                                                            ]):
                                                                                ret = main()

        # 3 soft corrections applied (max_cycles=3)
        assert mock_soft.call_count == 3
        # cycle limit message should appear in printed output
        cycle_msg_found = any("refined" in line.lower() or "best" in line.lower()
                              for line in printed_lines)
        assert cycle_msg_found, f"Expected cycle limit message. Got: {printed_lines}"

    def test_interactive_edit_flow(self):
        """Interactive: 'edit 1' then 'done' runs import_draft, approves with 'hard' type."""
        from openclaw.cli.propose import main
        from openclaw.topology.models import TopologyGraph, TopologyNode
        from openclaw.topology.proposal_models import RubricScore

        node = TopologyNode(id="pm", level=2, intent="test", risk_level="low")
        graph = TopologyGraph(project_id="testproj", nodes=[node], edges=[])

        mock_proposer_prop = MagicMock()
        mock_proposer_prop.archetype = "lean"
        mock_proposer_prop.graph = graph
        mock_proposer_prop.delegation_boundaries = "L2 only"
        mock_proposer_prop.coordination_model = "sequential"
        mock_proposer_prop.risk_assessment = "low"
        mock_proposer_prop.justification = "Simple approach."

        score = RubricScore(
            complexity=7, coordination_overhead=6,
            risk_containment=5, time_to_first_output=8,
            cost_estimate=7, preference_fit=5,
            overall_confidence=7,
        )

        # Mock import_draft returns a valid graph with lint result
        imported_graph = TopologyGraph(project_id="testproj", nodes=[node], edges=[])
        mock_lint = MagicMock()
        mock_lint.valid = True
        mock_lint.adjusted = False
        mock_lint.adjustments = []

        with patch("sys.argv", ["openclaw-propose", "build something"]):
            with patch("openclaw.cli.propose._is_interactive", return_value=True):
                with patch("openclaw.cli.propose.get_active_project_id", return_value="testproj"):
                    with patch("openclaw.cli.propose.AgentRegistry") as mock_reg:
                        mock_reg.return_value._agents = {}
                        with patch("openclaw.cli.propose.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.propose.ask_clarifications", return_value={}):
                                with patch("openclaw.cli.propose.generate_proposals_sync", return_value={
                                    "lean": {"roles": [], "edges": [], "assumptions": []},
                                }):
                                    with patch("openclaw.cli.propose._build_proposer_proposals",
                                               return_value=[mock_proposer_prop]):
                                        with patch("openclaw.cli.propose.ConstraintLinter") as mock_linter:
                                            lr = MagicMock()
                                            lr.valid = True
                                            lr.adjusted = False
                                            lr.rejected_roles = []
                                            mock_linter.return_value.lint.return_value = lr
                                            with patch("openclaw.cli.propose.score_proposal", return_value=score):
                                                with patch("openclaw.cli.propose.find_key_differentiators", return_value=[]):
                                                    with patch("openclaw.cli.propose.ArchetypeClassifier") as mock_cls:
                                                        mock_cls.return_value.classify.return_value = MagicMock(archetype="lean")
                                                        with patch("openclaw.cli.propose.save_pending_proposals"):
                                                            with patch("openclaw.cli.propose.approve_topology") as mock_approve:
                                                                with patch("openclaw.cli.propose.export_draft") as mock_export:
                                                                    mock_export.return_value = "/tmp/draft.json"
                                                                    with patch("openclaw.cli.propose.import_draft",
                                                                               return_value=(imported_graph, mock_lint)) as mock_import:
                                                                        with patch("openclaw.cli.propose.render_diff_summary", return_value="diff"):
                                                                            with patch("openclaw.cli.propose.compute_pushback_note", return_value=""):
                                                                                with patch("builtins.input", side_effect=["edit 1", "done"]):
                                                                                    ret = main()

        assert ret == 0
        mock_export.assert_called_once()
        mock_import.assert_called_once()
        mock_approve.assert_called_once()
        # Should approve with "hard" correction type
        call_args = mock_approve.call_args
        assert call_args[0][2] == "hard"
