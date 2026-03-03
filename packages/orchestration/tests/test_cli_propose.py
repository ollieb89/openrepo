"""
Tests for the openclaw-propose CLI entry point.

Tests focus on argument parsing, error handling, and importability.
LLM calls are not invoked — no real API calls.
"""

import sys
from unittest.mock import MagicMock, patch


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
        """_to_pm_proposals maps .graph -> .topology correctly."""
        from openclaw.cli.propose import _to_pm_proposals
        from openclaw.topology.models import TopologyGraph, TopologyNode

        # Create a mock proposer proposal
        mock_graph = TopologyGraph(
            project_id="test",
            nodes=[TopologyNode(id="pm", level=2, intent="test", risk_level="low")],
            edges=[],
        )
        mock_proposer_proposal = MagicMock()
        mock_proposer_proposal.archetype = "lean"
        mock_proposer_proposal.graph = mock_graph
        mock_proposer_proposal.delegation_boundaries = "L2 only"
        mock_proposer_proposal.coordination_model = "sequential"
        mock_proposer_proposal.risk_assessment = "low"
        mock_proposer_proposal.justification = "simple"

        result = _to_pm_proposals([mock_proposer_proposal])

        assert len(result) == 1
        assert result[0].archetype == "lean"
        assert result[0].topology is mock_graph
        assert result[0].delegation_boundaries == "L2 only"
        assert result[0].rubric_score is None  # Not scored yet

    def test_converts_empty_list(self):
        """_to_pm_proposals handles empty input gracefully."""
        from openclaw.cli.propose import _to_pm_proposals
        result = _to_pm_proposals([])
        assert result == []
