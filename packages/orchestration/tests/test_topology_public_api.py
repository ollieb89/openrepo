"""
Tests that topology package exposes the public API documented in the plan.

INT-01: score_proposal and render_diff_summary must be importable from
        openclaw.topology (not only from submodule paths).
"""
import pytest
import openclaw.topology


def test_import_score_proposal():
    """score_proposal must be importable directly from openclaw.topology."""
    from openclaw.topology import score_proposal  # noqa: F401
    assert callable(score_proposal)


def test_import_render_diff_summary():
    """render_diff_summary must be importable directly from openclaw.topology."""
    from openclaw.topology import render_diff_summary  # noqa: F401
    assert callable(render_diff_summary)


def test_score_proposal_in_all():
    """score_proposal must be listed in __all__."""
    assert "score_proposal" in openclaw.topology.__all__


def test_render_diff_summary_in_all():
    """render_diff_summary must be listed in __all__."""
    assert "render_diff_summary" in openclaw.topology.__all__
