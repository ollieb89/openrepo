"""
Tests for the ConstraintLinter.

TDD RED phase: tests are written before the linter implementation.

Uses a mock AgentRegistry with known agent IDs to avoid filesystem dependencies.
"""

import pytest
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal mock AgentRegistry (mirrors the real API)
# ---------------------------------------------------------------------------

@dataclass
class _MockAgentSpec:
    id: str
    level: int = 3


class _MockAgentRegistry:
    """
    Lightweight stand-in for AgentRegistry for testing the linter.

    Provides `_agents` dict and `get()` method to match the real interface.
    """

    def __init__(self, agent_ids: List[str]):
        self._agents: Dict[str, _MockAgentSpec] = {
            aid: _MockAgentSpec(id=aid) for aid in agent_ids
        }

    def get(self, agent_id: str) -> Optional[_MockAgentSpec]:
        return self._agents.get(agent_id)


# Known agents used in test proposals
KNOWN_AGENTS = ["clawdia_prime", "pumplai_pm", "l3_specialist", "docs_pm", "nextjs_pm"]

# A minimal valid proposal dict
def _make_proposal(roles=None, edges=None) -> dict:
    if roles is None:
        roles = [
            {"id": "pumplai_pm", "level": 2},
            {"id": "l3_specialist", "level": 3},
        ]
    if edges is None:
        edges = [
            {"from": "pumplai_pm", "to": "l3_specialist", "type": "delegation"}
        ]
    return {"roles": roles, "edges": edges}


def _make_registry(extra_agents: List[str] = None) -> _MockAgentRegistry:
    agents = list(KNOWN_AGENTS)
    if extra_agents:
        agents.extend(extra_agents)
    return _MockAgentRegistry(agents)


# ---------------------------------------------------------------------------
# Tests: LintResult structure
# ---------------------------------------------------------------------------

class TestLintResultStructure:
    def test_lint_result_has_required_fields(self):
        """LintResult must have valid, adjusted, rejected_roles, adjustments, proposal."""
        from openclaw.topology.linter import LintResult
        result = LintResult(
            valid=True, adjusted=False,
            rejected_roles=[], adjustments=[],
            proposal={"roles": [], "edges": []},
        )
        assert result.valid is True
        assert result.adjusted is False
        assert result.rejected_roles == []
        assert result.adjustments == []


class TestConstraintLinterInit:
    def test_linter_requires_registry_and_max_concurrent(self):
        """ConstraintLinter should accept registry and max_concurrent."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry()
        linter = ConstraintLinter(registry=registry, max_concurrent=3)
        assert linter.max_concurrent == 3

    def test_max_retries_constant(self):
        """MAX_RETRIES should be 2 (3 total attempts)."""
        from openclaw.topology.linter import MAX_RETRIES
        assert MAX_RETRIES == 2


# ---------------------------------------------------------------------------
# Tests: clean proposals
# ---------------------------------------------------------------------------

class TestCleanProposal:
    def test_clean_proposal_passes(self):
        """All known roles, within L3 pool — should be valid, not adjusted."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry()
        linter = ConstraintLinter(registry=registry, max_concurrent=3)
        proposal = _make_proposal()
        result = linter.lint("lean", proposal)
        assert result.valid is True
        assert result.adjusted is False
        assert result.rejected_roles == []
        assert result.adjustments == []

    def test_clean_proposal_returns_proposal_unchanged(self):
        """Clean proposal should be returned unchanged."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry()
        linter = ConstraintLinter(registry=registry, max_concurrent=3)
        proposal = _make_proposal()
        result = linter.lint("lean", proposal)
        assert result.proposal == proposal


# ---------------------------------------------------------------------------
# Tests: unknown role rejection
# ---------------------------------------------------------------------------

class TestUnknownRoleRejection:
    def test_unknown_role_rejected(self):
        """A role not in the registry should return valid=False."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry()
        linter = ConstraintLinter(registry=registry, max_concurrent=3)
        proposal = _make_proposal(roles=[
            {"id": "pumplai_pm", "level": 2},
            {"id": "unknown_agent_xyz", "level": 3},
        ])
        result = linter.lint("lean", proposal)
        assert result.valid is False
        assert "unknown_agent_xyz" in result.rejected_roles
        assert result.adjusted is False

    def test_multiple_unknown_roles_all_listed(self):
        """All unknown roles should appear in rejected_roles."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry()
        linter = ConstraintLinter(registry=registry, max_concurrent=3)
        proposal = _make_proposal(roles=[
            {"id": "pumplai_pm", "level": 2},
            {"id": "ghost_a", "level": 3},
            {"id": "ghost_b", "level": 3},
        ])
        result = linter.lint("lean", proposal)
        assert result.valid is False
        assert "ghost_a" in result.rejected_roles
        assert "ghost_b" in result.rejected_roles
        assert len(result.rejected_roles) == 2

    def test_unknown_role_does_not_attempt_auto_constrain(self):
        """When roles are unknown, adjusted should be False (no auto-constrain)."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry()
        linter = ConstraintLinter(registry=registry, max_concurrent=3)
        proposal = _make_proposal(roles=[
            {"id": "bad_agent", "level": 3},
            {"id": "another_bad", "level": 3},
            {"id": "yet_another", "level": 3},
            {"id": "fourth_bad", "level": 3},
        ])
        result = linter.lint("lean", proposal)
        # Should be rejected for unknown roles, not adjusted for pool size
        assert result.valid is False
        assert result.adjusted is False


# ---------------------------------------------------------------------------
# Tests: pool violation auto-constraining
# ---------------------------------------------------------------------------

class TestPoolViolationConstraining:
    def test_pool_violation_auto_constrained(self):
        """5 L3 roles with max_concurrent=3 → valid=True, adjusted=True."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry(["extra_l3_a", "extra_l3_b", "extra_l3_c"])
        linter = ConstraintLinter(registry=registry, max_concurrent=3)
        proposal = _make_proposal(roles=[
            {"id": "pumplai_pm", "level": 2},
            {"id": "l3_specialist", "level": 3},
            {"id": "docs_pm", "level": 3},
            {"id": "extra_l3_a", "level": 3},
            {"id": "extra_l3_b", "level": 3},
            {"id": "extra_l3_c", "level": 3},
        ])
        result = linter.lint("balanced", proposal)
        assert result.valid is True
        assert result.adjusted is True
        # Adjusted proposal should have at most max_concurrent L3 roles
        adjusted_l3s = [r for r in result.proposal["roles"] if r.get("level") == 3]
        assert len(adjusted_l3s) <= 3

    def test_lint_result_has_adjustment_description(self):
        """Adjustments list should describe what was changed."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry(["extra_l3_a", "extra_l3_b"])
        linter = ConstraintLinter(registry=registry, max_concurrent=2)
        proposal = _make_proposal(roles=[
            {"id": "pumplai_pm", "level": 2},
            {"id": "l3_specialist", "level": 3},
            {"id": "extra_l3_a", "level": 3},
            {"id": "extra_l3_b", "level": 3},
        ])
        result = linter.lint("balanced", proposal)
        assert result.adjusted is True
        assert len(result.adjustments) >= 1
        # At least one adjustment message should mention the pool limit
        combined = " ".join(result.adjustments)
        assert "3" in combined or "2" in combined or "max" in combined.lower() or "concurrent" in combined.lower()

    def test_auto_constrain_preserves_review_gates(self):
        """Auto-constraining should prefer removing coordination-only roles over review-gate-connected ones."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry(["coord_only_a", "coord_only_b"])
        linter = ConstraintLinter(registry=registry, max_concurrent=2)

        # 4 L3 roles: 2 connected to review gate, 2 coordination-only
        proposal = {
            "roles": [
                {"id": "pumplai_pm", "level": 2},
                {"id": "l3_specialist", "level": 3},   # review gate connected
                {"id": "docs_pm", "level": 3},          # review gate connected
                {"id": "coord_only_a", "level": 3},     # coordination-only
                {"id": "coord_only_b", "level": 3},     # coordination-only
            ],
            "edges": [
                {"from": "pumplai_pm", "to": "l3_specialist", "type": "delegation"},
                {"from": "pumplai_pm", "to": "docs_pm", "type": "delegation"},
                {"from": "pumplai_pm", "to": "coord_only_a", "type": "delegation"},
                {"from": "pumplai_pm", "to": "coord_only_b", "type": "delegation"},
                {"from": "coord_only_a", "to": "coord_only_b", "type": "coordination"},
                # review gate edges to review-gate-connected roles
                {"from": "l3_specialist", "to": "pumplai_pm", "type": "review_gate"},
                {"from": "docs_pm", "to": "pumplai_pm", "type": "review_gate"},
            ],
        }

        result = linter.lint("balanced", proposal)
        assert result.valid is True
        assert result.adjusted is True

        # The coordination-only roles (coord_only_a, coord_only_b) should be removed
        # not the review-gate-connected ones (l3_specialist, docs_pm)
        adjusted_role_ids = {r["id"] for r in result.proposal["roles"] if r.get("level") == 3}
        # Review-gate roles should be preserved (they have high removal cost)
        assert "l3_specialist" in adjusted_role_ids or "docs_pm" in adjusted_role_ids, (
            f"Expected review-gate-connected roles to be preserved, got: {adjusted_role_ids}"
        )

    def test_auto_constrain_warns_if_review_gates_lost(self):
        """If removing roles eliminates all review gates, an adjustment warning is logged."""
        from openclaw.topology.linter import ConstraintLinter
        registry = _make_registry(["l3_b", "l3_c", "l3_d"])
        linter = ConstraintLinter(registry=registry, max_concurrent=1)

        # 4 L3 roles all connected to review gate → removing any loses review gate
        proposal = {
            "roles": [
                {"id": "pumplai_pm", "level": 2},
                {"id": "l3_specialist", "level": 3},
                {"id": "l3_b", "level": 3},
                {"id": "l3_c", "level": 3},
                {"id": "l3_d", "level": 3},
            ],
            "edges": [
                {"from": "pumplai_pm", "to": "l3_specialist", "type": "delegation"},
                {"from": "l3_specialist", "to": "pumplai_pm", "type": "review_gate"},
                {"from": "pumplai_pm", "to": "l3_b", "type": "delegation"},
                {"from": "l3_b", "to": "pumplai_pm", "type": "review_gate"},
                {"from": "pumplai_pm", "to": "l3_c", "type": "delegation"},
                {"from": "l3_c", "to": "pumplai_pm", "type": "review_gate"},
                {"from": "pumplai_pm", "to": "l3_d", "type": "delegation"},
                {"from": "l3_d", "to": "pumplai_pm", "type": "review_gate"},
            ],
        }

        result = linter.lint("robust", proposal)
        assert result.valid is True
        assert result.adjusted is True
        # Warning should be present in adjustments
        combined = " ".join(result.adjustments).lower()
        assert "warning" in combined or "review" in combined or "gate" in combined, (
            f"Expected review gate warning in adjustments: {result.adjustments}"
        )
