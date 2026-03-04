"""
Tests for the openclaw-approve CLI entry point.

openclaw-approve loads pending proposals and prompts for approval selection.
Tests cover: success path, no pending, non-interactive, invalid selection reprompt.
"""

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proposal_set_dict():
    """Return a minimal ProposalSet-compatible dict for mocking load_pending_proposals."""
    return {
        "proposals": [
            {
                "archetype": "lean",
                "topology": {
                    "project_id": "testproj",
                    "nodes": [
                        {"id": "pm", "level": 2, "intent": "manage", "risk_level": "low"}
                    ],
                    "edges": [],
                },
                "delegation_boundaries": "L2 only",
                "coordination_model": "sequential",
                "risk_assessment": "low",
                "justification": "Simple approach.",
                "rubric_score": {
                    "complexity": 7,
                    "coordination_overhead": 6,
                    "risk_containment": 5,
                    "time_to_first_output": 8,
                    "cost_estimate": 7,
                    "preference_fit": 5,
                    "overall_confidence": 7,
                    "key_differentiators": [],
                },
            }
        ],
        "assumptions": ["risk: low"],
        "outcome": "build something",
    }


# ---------------------------------------------------------------------------
# Tests: importability
# ---------------------------------------------------------------------------

class TestApproveCliImportable:
    def test_main_importable(self):
        """from openclaw.cli.approve import main should succeed."""
        from openclaw.cli.approve import main
        assert callable(main)


# ---------------------------------------------------------------------------
# Tests: no pending proposals
# ---------------------------------------------------------------------------

class TestNoPendingProposals:
    def test_no_pending_returns_1(self):
        """Returns exit code 1 when no pending proposals exist."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals", return_value=None):
                    ret = main()

        assert ret == 1

    def test_no_pending_prints_message(self, capsys):
        """Prints helpful message when no pending proposals found."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals", return_value=None):
                    main()

        captured = capsys.readouterr()
        assert "pending" in captured.out.lower() or "pending" in captured.err.lower()


# ---------------------------------------------------------------------------
# Tests: non-interactive mode
# ---------------------------------------------------------------------------

class TestNonInteractive:
    def test_non_interactive_returns_1(self):
        """Returns exit code 1 in non-interactive mode (approval requires user selection)."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()):
                    with patch("openclaw.cli.approve._is_interactive", return_value=False):
                        ret = main()

        assert ret == 1


# ---------------------------------------------------------------------------
# Tests: success path
# ---------------------------------------------------------------------------

class TestApproveSuccess:
    def test_approve_success_returns_0(self):
        """Returns 0 on successful approval selection."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()):
                    with patch("openclaw.cli.approve._is_interactive", return_value=True):
                        with patch("openclaw.cli.approve.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.approve.approve_topology") as mock_approve:
                                with patch("openclaw.cli.approve.compute_pushback_note", return_value=""):
                                    with patch("builtins.input", return_value="1"):
                                        ret = main()

        assert ret == 0

    def test_approve_calls_approve_topology(self):
        """approve_topology is called with correct project_id."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()):
                    with patch("openclaw.cli.approve._is_interactive", return_value=True):
                        with patch("openclaw.cli.approve.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.approve.approve_topology") as mock_approve:
                                with patch("openclaw.cli.approve.compute_pushback_note", return_value=""):
                                    with patch("builtins.input", return_value="1"):
                                        main()

        mock_approve.assert_called_once()
        assert mock_approve.call_args[0][0] == "testproj"

    def test_approve_project_flag(self):
        """--project flag overrides active project."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve", "--project", "myproj"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()) as mock_load:
                    with patch("openclaw.cli.approve._is_interactive", return_value=True):
                        with patch("openclaw.cli.approve.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.approve.approve_topology"):
                                with patch("openclaw.cli.approve.compute_pushback_note", return_value=""):
                                    with patch("builtins.input", return_value="1"):
                                        main()

        # Should use "myproj" not "testproj"
        mock_load.assert_called_once_with("myproj")

    def test_approve_correction_type_is_initial(self):
        """Approval through openclaw-approve uses correction_type='initial'."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()):
                    with patch("openclaw.cli.approve._is_interactive", return_value=True):
                        with patch("openclaw.cli.approve.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.approve.approve_topology") as mock_approve:
                                with patch("openclaw.cli.approve.compute_pushback_note", return_value=""):
                                    with patch("builtins.input", return_value="1"):
                                        main()

        # correction_type arg (3rd positional) should be "initial"
        assert mock_approve.call_args[0][2] == "initial"

    def test_approve_passes_rubric_scores_kwarg(self):
        """approve_topology is called with rubric_scores kwarg containing proposal scores."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()):
                    with patch("openclaw.cli.approve._is_interactive", return_value=True):
                        with patch("openclaw.cli.approve.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.approve.approve_topology") as mock_approve:
                                with patch("openclaw.cli.approve.compute_pushback_note", return_value=""):
                                    with patch("builtins.input", return_value="1"):
                                        main()

        # rubric_scores kwarg must be present in the call
        call_kwargs = mock_approve.call_args[1]
        assert "rubric_scores" in call_kwargs, "rubric_scores kwarg must be passed to approve_topology"
        rubric_scores = call_kwargs["rubric_scores"]
        # The fixture has a "lean" proposal with rubric_score — expect rubric_scores["lean"]["complexity"] == 7
        assert isinstance(rubric_scores, dict), "rubric_scores must be a dict"
        assert "lean" in rubric_scores, "rubric_scores must contain the 'lean' archetype key"
        assert rubric_scores["lean"]["complexity"] == 7


# ---------------------------------------------------------------------------
# Tests: invalid selection reprompt
# ---------------------------------------------------------------------------

class TestInvalidSelectionReprompt:
    def test_invalid_then_valid_reprompts(self):
        """Invalid input (out of range) triggers reprompt; valid input then succeeds."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()):
                    with patch("openclaw.cli.approve._is_interactive", return_value=True):
                        with patch("openclaw.cli.approve.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.approve.approve_topology") as mock_approve:
                                with patch("openclaw.cli.approve.compute_pushback_note", return_value=""):
                                    with patch("builtins.input", side_effect=["99", "1"]):
                                        ret = main()

        assert ret == 0
        mock_approve.assert_called_once()

    def test_archetype_name_selection(self):
        """Selecting by archetype name 'lean' works."""
        from openclaw.cli.approve import main

        with patch("sys.argv", ["openclaw-approve"]):
            with patch("openclaw.cli.approve.get_active_project_id", return_value="testproj"):
                with patch("openclaw.cli.approve.load_pending_proposals",
                           return_value=_make_proposal_set_dict()):
                    with patch("openclaw.cli.approve._is_interactive", return_value=True):
                        with patch("openclaw.cli.approve.get_topology_config", return_value={
                            "proposal_confidence_warning_threshold": 6,
                            "rubric_weights": {"complexity": 1.0},
                        }):
                            with patch("openclaw.cli.approve.approve_topology") as mock_approve:
                                with patch("openclaw.cli.approve.compute_pushback_note", return_value=""):
                                    with patch("builtins.input", return_value="lean"):
                                        ret = main()

        assert ret == 0
        mock_approve.assert_called_once()
