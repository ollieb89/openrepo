"""
Tests for proposal data models and rubric scorer.

TDD RED phase: these tests are written before implementation.
"""

import pytest
from openclaw.topology.models import (
    TopologyGraph, TopologyNode, TopologyEdge, EdgeType,
)


# ---------------------------------------------------------------------------
# Helpers to build test graphs
# ---------------------------------------------------------------------------

def _node(nid: str, level: int = 3) -> TopologyNode:
    return TopologyNode(id=nid, level=level, intent="test", risk_level="low")


def _lean_graph() -> TopologyGraph:
    """Minimal 2-node linear delegation: L2 -> L3."""
    return TopologyGraph(
        project_id="test",
        nodes=[_node("pm", level=2), _node("worker", level=3)],
        edges=[TopologyEdge(from_role="pm", to_role="worker", edge_type=EdgeType.DELEGATION)],
    )


def _balanced_graph() -> TopologyGraph:
    """3-node graph with coordination edge."""
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
            TopologyEdge(from_role="worker_b", to_role="pm", edge_type=EdgeType.REVIEW_GATE),
        ],
    )


def _robust_graph() -> TopologyGraph:
    """Full graph: 5 nodes with review gates and escalation."""
    return TopologyGraph(
        project_id="test",
        nodes=[
            _node("l1", level=1),
            _node("pm", level=2),
            _node("worker_a", level=3),
            _node("worker_b", level=3),
            _node("reviewer", level=2),
        ],
        edges=[
            TopologyEdge(from_role="l1", to_role="pm", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="pm", to_role="worker_a", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="pm", to_role="worker_b", edge_type=EdgeType.DELEGATION),
            TopologyEdge(from_role="worker_a", to_role="worker_b", edge_type=EdgeType.COORDINATION),
            TopologyEdge(from_role="worker_b", to_role="reviewer", edge_type=EdgeType.REVIEW_GATE),
            TopologyEdge(from_role="worker_a", to_role="l1", edge_type=EdgeType.ESCALATION),
        ],
    )


# ---------------------------------------------------------------------------
# Tests: proposal_models
# ---------------------------------------------------------------------------

class TestProposalModels:
    def test_topology_proposal_dataclass_fields(self):
        """TopologyProposal must have all required fields."""
        from openclaw.topology.proposal_models import TopologyProposal, RubricScore
        proposal = TopologyProposal(
            archetype="lean",
            graph=_lean_graph(),
            delegation_boundaries="L2 delegates to L3 only",
            coordination_model="direct",
            risk_assessment="low risk",
            justification="simple task",
        )
        assert proposal.archetype == "lean"
        assert proposal.rubric_score is None  # optional field default

    def test_topology_proposal_with_rubric_score(self):
        """TopologyProposal can hold a RubricScore."""
        from openclaw.topology.proposal_models import TopologyProposal, RubricScore
        score = RubricScore(
            complexity=8, coordination_overhead=9, risk_containment=3,
            time_to_first_output=8, cost_estimate=8, preference_fit=5,
            overall_confidence=7,
        )
        proposal = TopologyProposal(
            archetype="lean",
            graph=_lean_graph(),
            delegation_boundaries="L2 delegates to L3",
            coordination_model="none",
            risk_assessment="low",
            justification="simple",
            rubric_score=score,
        )
        assert proposal.rubric_score.complexity == 8
        assert proposal.rubric_score.preference_fit == 5

    def test_proposal_set_dataclass_fields(self):
        """ProposalSet must hold a list of proposals, assumptions, and outcome."""
        from openclaw.topology.proposal_models import TopologyProposal, ProposalSet
        proposals = [
            TopologyProposal(
                archetype="lean", graph=_lean_graph(),
                delegation_boundaries="", coordination_model="",
                risk_assessment="", justification="",
            )
        ]
        ps = ProposalSet(
            proposals=proposals,
            assumptions=["Single L3 is sufficient"],
            outcome="Build feature X",
        )
        assert len(ps.proposals) == 1
        assert ps.assumptions[0] == "Single L3 is sufficient"

    def test_proposal_models_serialization(self):
        """TopologyProposal round-trips through to_dict/from_dict."""
        from openclaw.topology.proposal_models import TopologyProposal
        proposal = TopologyProposal(
            archetype="balanced",
            graph=_balanced_graph(),
            delegation_boundaries="PM delegates to workers",
            coordination_model="coordination-linked",
            risk_assessment="medium",
            justification="typical",
        )
        data = proposal.to_dict()
        assert data["archetype"] == "balanced"
        assert "graph" in data
        # from_dict round-trip
        proposal2 = TopologyProposal.from_dict(data)
        assert proposal2.archetype == "balanced"
        assert proposal2.delegation_boundaries == "PM delegates to workers"

    def test_proposal_set_serialization(self):
        """ProposalSet round-trips through to_dict."""
        from openclaw.topology.proposal_models import TopologyProposal, ProposalSet
        ps = ProposalSet(
            proposals=[
                TopologyProposal(
                    archetype="lean", graph=_lean_graph(),
                    delegation_boundaries="x", coordination_model="y",
                    risk_assessment="z", justification="q",
                )
            ],
            assumptions=["assumption"],
            outcome="Outcome",
        )
        data = ps.to_dict()
        assert data["outcome"] == "Outcome"
        assert isinstance(data["proposals"], list)


# ---------------------------------------------------------------------------
# Tests: rubric scorer
# ---------------------------------------------------------------------------

class TestRubricScore:
    def test_rubric_score_dataclass_fields(self):
        """RubricScore must have 7 dimension fields + key_differentiators."""
        from openclaw.topology.proposal_models import RubricScore
        score = RubricScore(
            complexity=8, coordination_overhead=9, risk_containment=2,
            time_to_first_output=8, cost_estimate=8, preference_fit=5,
            overall_confidence=7,
        )
        assert hasattr(score, "key_differentiators")
        assert score.key_differentiators == []

    def test_rubric_score_all_fields_0_to_10(self):
        """All numeric fields in RubricScore should be 0-10."""
        from openclaw.topology.rubric import RubricScorer
        scorer = RubricScorer()
        score = scorer.score_proposal(_lean_graph(), weights={})
        for field_name in ["complexity", "coordination_overhead", "risk_containment",
                           "time_to_first_output", "cost_estimate", "preference_fit",
                           "overall_confidence"]:
            val = getattr(score, field_name)
            assert 0 <= val <= 10, f"{field_name}={val} out of range"

    def test_lean_topology_scores_high_on_simplicity(self):
        """Lean graph (few nodes/edges) should score high on complexity and time_to_first_output.

        Lean graph: 2 nodes (pm->worker), depth=2.
        Formula: time_to_first_output = max(0, 10 - depth*2) = 10 - 4 = 6.
        Lean scores higher on these dimensions than balanced/robust, so we
        verify it is above the midpoint (5) and above robust's score.
        """
        from openclaw.topology.rubric import RubricScorer
        scorer = RubricScorer()
        lean_score = scorer.score_proposal(_lean_graph(), weights={})
        robust_score = scorer.score_proposal(_robust_graph(), weights={})
        # Lean: 2 nodes, 1 delegation edge — should score higher on simplicity than robust
        assert lean_score.complexity >= 7, f"Expected complexity >= 7, got {lean_score.complexity}"
        # Lean depth=2, robust depth=3 → lean scores higher on time_to_first_output
        assert lean_score.time_to_first_output > robust_score.time_to_first_output, (
            f"Lean time_to_first_output={lean_score.time_to_first_output} should exceed "
            f"robust={robust_score.time_to_first_output}"
        )
        # Lean time_to_first_output should be above neutral (formula gives 6 for depth=2)
        assert lean_score.time_to_first_output >= 6, (
            f"Expected time_to_first_output >= 6, got {lean_score.time_to_first_output}"
        )

    def test_robust_topology_scores_high_on_risk_containment(self):
        """Robust graph (review gates + escalation) should score high on risk_containment."""
        from openclaw.topology.rubric import RubricScorer
        scorer = RubricScorer()
        score = scorer.score_proposal(_robust_graph(), weights={})
        assert score.risk_containment >= 5, f"Expected risk_containment >= 5, got {score.risk_containment}"

    def test_preference_fit_always_five(self):
        """preference_fit must be 5 regardless of topology (pre-Phase 64)."""
        from openclaw.topology.rubric import RubricScorer
        scorer = RubricScorer()
        for graph in [_lean_graph(), _balanced_graph(), _robust_graph()]:
            score = scorer.score_proposal(graph, weights={})
            assert score.preference_fit == 5, f"preference_fit should be 5, got {score.preference_fit}"

    def test_overall_confidence_is_weighted_average(self):
        """overall_confidence should be a weighted average of the 6 scored dimensions."""
        from openclaw.topology.proposal_models import RubricScore
        from openclaw.topology.rubric import RubricScorer, DEFAULT_WEIGHTS
        scorer = RubricScorer()
        score = scorer.score_proposal(_lean_graph(), weights=DEFAULT_WEIGHTS)
        # Manually compute expected
        dims = {
            "complexity": score.complexity,
            "coordination_overhead": score.coordination_overhead,
            "risk_containment": score.risk_containment,
            "time_to_first_output": score.time_to_first_output,
            "cost_estimate": score.cost_estimate,
            "preference_fit": score.preference_fit,
        }
        expected = round(sum(dims[k] * DEFAULT_WEIGHTS[k] for k in DEFAULT_WEIGHTS))
        expected = max(0, min(10, expected))
        assert score.overall_confidence == expected, (
            f"overall_confidence={score.overall_confidence}, expected={expected}"
        )

    def test_key_differentiators_found(self):
        """find_key_differentiators should return dimensions with >= 3 point spread."""
        from openclaw.topology.rubric import RubricScorer, find_key_differentiators
        scorer = RubricScorer()
        scores = [
            scorer.score_proposal(_lean_graph(), weights={}),
            scorer.score_proposal(_balanced_graph(), weights={}),
            scorer.score_proposal(_robust_graph(), weights={}),
        ]
        diffs = find_key_differentiators(scores)
        # Lean vs Robust will differ on risk_containment, complexity, coordination_overhead
        assert isinstance(diffs, list)
        # At least one differentiator should be found between lean and robust
        assert len(diffs) >= 1, f"Expected at least 1 differentiator, got {diffs}"

    def test_key_differentiators_no_spread(self):
        """find_key_differentiators returns empty list when all scores identical."""
        from openclaw.topology.rubric import find_key_differentiators
        from openclaw.topology.proposal_models import RubricScore
        s = RubricScore(
            complexity=5, coordination_overhead=5, risk_containment=5,
            time_to_first_output=5, cost_estimate=5, preference_fit=5,
            overall_confidence=5,
        )
        diffs = find_key_differentiators([s, s, s])
        assert diffs == []


# ---------------------------------------------------------------------------
# Tests: config
# ---------------------------------------------------------------------------

class TestTopologyConfig:
    def test_topology_key_in_schema(self):
        """OPENCLAW_JSON_SCHEMA must include 'topology' key."""
        from openclaw.config import OPENCLAW_JSON_SCHEMA
        assert "topology" in OPENCLAW_JSON_SCHEMA["properties"], (
            "topology key missing from OPENCLAW_JSON_SCHEMA properties"
        )

    def test_topology_config_defaults(self):
        """get_topology_config() should return threshold=5 and 6 rubric weights."""
        from openclaw.config import get_topology_config
        tc = get_topology_config()
        assert tc["proposal_confidence_warning_threshold"] == 5
        assert "rubric_weights" in tc
        weights = tc["rubric_weights"]
        assert set(weights.keys()) == {
            "complexity", "coordination_overhead", "risk_containment",
            "time_to_first_output", "cost_estimate", "preference_fit"
        }
        # Weights should sum to approximately 1.0
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"

    def test_auto_approve_l1_default_is_false(self):
        """get_topology_config() must return auto_approve_l1=False by default (CORR-07)."""
        from openclaw.config import get_topology_config
        tc = get_topology_config()
        assert "auto_approve_l1" in tc, "auto_approve_l1 key missing from get_topology_config() return"
        assert tc["auto_approve_l1"] is False

    def test_pushback_threshold_default_is_8(self):
        """get_topology_config() must return pushback_threshold=8 by default (CORR-05)."""
        from openclaw.config import get_topology_config
        tc = get_topology_config()
        assert "pushback_threshold" in tc, "pushback_threshold key missing from get_topology_config() return"
        assert tc["pushback_threshold"] == 8

    def test_auto_approve_l1_in_schema(self):
        """OPENCLAW_JSON_SCHEMA topology properties must include auto_approve_l1 boolean."""
        from openclaw.config import OPENCLAW_JSON_SCHEMA
        topology_props = OPENCLAW_JSON_SCHEMA["properties"]["topology"]["properties"]
        assert "auto_approve_l1" in topology_props, "auto_approve_l1 missing from topology schema"
        assert topology_props["auto_approve_l1"]["type"] == "boolean"

    def test_pushback_threshold_in_schema(self):
        """OPENCLAW_JSON_SCHEMA topology properties must include pushback_threshold number 0-10."""
        from openclaw.config import OPENCLAW_JSON_SCHEMA
        topology_props = OPENCLAW_JSON_SCHEMA["properties"]["topology"]["properties"]
        assert "pushback_threshold" in topology_props, "pushback_threshold missing from topology schema"
        prop = topology_props["pushback_threshold"]
        assert prop["type"] == "number"
        assert prop["minimum"] == 0
        assert prop["maximum"] == 10

    def test_schema_accepts_auto_approve_l1_true(self):
        """Validator must accept openclaw.json with topology.auto_approve_l1=true."""
        import json
        from openclaw.config_validator import validate_openclaw_config
        config = {
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "topology": {"auto_approve_l1": True, "pushback_threshold": 5},
        }
        fatal, warnings = validate_openclaw_config(config, "test-config.json")
        assert fatal == [], f"Unexpected fatal errors: {fatal}"

    def test_topology_config_reflects_override(self, monkeypatch, tmp_path):
        """get_topology_config() returns user-configured auto_approve_l1 and pushback_threshold."""
        import json
        config_file = tmp_path / "openclaw.json"
        config_file.write_text(json.dumps({
            "gateway": {"port": 18789},
            "agents": {"list": []},
            "topology": {
                "auto_approve_l1": True,
                "pushback_threshold": 3,
            },
        }))
        monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))
        # Reload config module to pick up new env var
        from openclaw.config import get_topology_config
        tc = get_topology_config()
        assert tc["auto_approve_l1"] is True
        assert tc["pushback_threshold"] == 3
