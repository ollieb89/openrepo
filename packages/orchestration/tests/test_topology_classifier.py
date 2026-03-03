"""
Tests for archetype classifier.

Tests pattern-matching classification of topology graphs into
Lean, Balanced, or Robust archetypes.
"""

import pytest
from openclaw.topology.models import (
    TopologyGraph,
    TopologyNode,
    TopologyEdge,
    EdgeType,
)
from openclaw.topology.classifier import ArchetypeClassifier, ArchetypeResult


# --- Fixtures ---

def make_node(id: str, level: int = 2, intent: str = "task", risk_level: str = "low") -> TopologyNode:
    return TopologyNode(id=id, level=level, intent=intent, risk_level=risk_level)


def make_edge(from_role: str, to_role: str, edge_type: EdgeType = EdgeType.DELEGATION) -> TopologyEdge:
    return TopologyEdge(from_role=from_role, to_role=to_role, edge_type=edge_type)


def make_graph(nodes=None, edges=None, project_id="test") -> TopologyGraph:
    return TopologyGraph(
        nodes=nodes or [],
        edges=edges or [],
        project_id=project_id,
    )


classifier = ArchetypeClassifier()


# --- ArchetypeResult structure tests ---

class TestArchetypeResultStructure:
    def test_result_has_required_fields(self):
        node_a = make_node("l1", level=1)
        node_b = make_node("l2", level=2)
        graph = make_graph(nodes=[node_a, node_b], edges=[make_edge("l1", "l2")])

        result = classifier.classify(graph)

        assert hasattr(result, "archetype")
        assert hasattr(result, "confidence")
        assert hasattr(result, "explanation")
        assert hasattr(result, "traits")

    def test_archetype_is_valid_value(self):
        node = make_node("a")
        graph = make_graph(nodes=[node])

        result = classifier.classify(graph)

        assert result.archetype in {"lean", "balanced", "robust"}

    def test_confidence_in_valid_range(self):
        node_a = make_node("l1", level=1)
        node_b = make_node("l2", level=2)
        graph = make_graph(nodes=[node_a, node_b], edges=[make_edge("l1", "l2")])

        result = classifier.classify(graph)

        assert 0.0 <= result.confidence <= 1.0

    def test_explanation_always_present(self):
        """Explanation must always be non-empty (Phase 61 CONTEXT requirement)."""
        graphs = [
            make_graph(nodes=[make_node("a"), make_node("b")], edges=[make_edge("a", "b")]),
            make_graph(nodes=[make_node("a")]),
            make_graph(),
        ]

        for graph in graphs:
            result = classifier.classify(graph)
            assert isinstance(result.explanation, str)
            assert len(result.explanation) > 0, f"Explanation empty for {graph}"

    def test_traits_populated(self):
        """traits must be a list (may be empty for edge cases, but must exist)."""
        result = classifier.classify(make_graph(nodes=[make_node("a"), make_node("b")],
                                                 edges=[make_edge("a", "b")]))
        assert isinstance(result.traits, list)


# --- Lean archetype tests ---

class TestLeanArchetype:
    def test_lean_linear_chain(self):
        """Two nodes, one delegation edge — minimal chain = lean."""
        node_a = make_node("l1", level=1)
        node_b = make_node("l2", level=2)
        edge = make_edge("l1", "l2", EdgeType.DELEGATION)

        result = classifier.classify(make_graph(nodes=[node_a, node_b], edges=[edge]))

        assert result.archetype == "lean"

    def test_lean_flat_delegation(self):
        """One L1 delegating to 3 L3s, no coordination — flat lean topology."""
        l1 = make_node("orchestrator", level=1)
        workers = [make_node(f"worker-{i}", level=3) for i in range(3)]
        edges = [make_edge("orchestrator", f"worker-{i}", EdgeType.DELEGATION) for i in range(3)]

        result = classifier.classify(make_graph(nodes=[l1] + workers, edges=edges))

        assert result.archetype == "lean"

    def test_lean_no_review_gates(self):
        """Lean topology must have no review gates."""
        l1 = make_node("a", level=1)
        l2 = make_node("b", level=2)
        edge = make_edge("a", "b", EdgeType.DELEGATION)

        result = classifier.classify(make_graph(nodes=[l1, l2], edges=[edge]))

        assert result.archetype == "lean"

    def test_lean_has_linear_or_flat_trait(self):
        """Lean topology should have 'linear-chain' or 'flat-delegation' trait."""
        node_a = make_node("l1", level=1)
        node_b = make_node("l2", level=2)
        edge = make_edge("l1", "l2", EdgeType.DELEGATION)

        result = classifier.classify(make_graph(nodes=[node_a, node_b], edges=[edge]))

        assert result.archetype == "lean"
        assert any(t in result.traits for t in ["linear-chain", "flat-delegation"])

    def test_lean_empty_graph(self):
        """Empty graph with no edges classifies as lean (trivially)."""
        result = classifier.classify(make_graph(nodes=[make_node("a")]))
        assert result.archetype == "lean"


# --- Robust archetype tests ---

class TestRobustArchetype:
    def test_robust_with_review_gates_and_escalation(self):
        """Review gate + escalation = robust."""
        l1 = make_node("orchestrator", level=1)
        l2a = make_node("pm-a", level=2)
        l2b = make_node("pm-b", level=2)
        l3 = make_node("worker", level=3)

        edges = [
            make_edge("orchestrator", "pm-a", EdgeType.DELEGATION),
            make_edge("pm-a", "worker", EdgeType.DELEGATION),
            make_edge("worker", "pm-a", EdgeType.REVIEW_GATE),
            make_edge("pm-a", "orchestrator", EdgeType.ESCALATION),
        ]

        result = classifier.classify(make_graph(nodes=[l1, l2a, l2b, l3], edges=edges))

        assert result.archetype == "robust"

    def test_robust_with_multiple_coordination_paths(self):
        """Review gate + multiple coordination paths = robust."""
        nodes = [make_node(f"n{i}", level=2) for i in range(4)]
        edges = [
            make_edge("n0", "n1", EdgeType.DELEGATION),
            make_edge("n0", "n2", EdgeType.DELEGATION),
            make_edge("n1", "n3", EdgeType.COORDINATION),
            make_edge("n2", "n3", EdgeType.COORDINATION),
            make_edge("n3", "n0", EdgeType.REVIEW_GATE),
        ]

        result = classifier.classify(make_graph(nodes=nodes, edges=edges))

        assert result.archetype == "robust"

    def test_robust_has_review_heavy_trait(self):
        """Multiple review gates should give 'review-heavy' trait."""
        l1 = make_node("l1", level=1)
        l2 = make_node("l2", level=2)
        l3a = make_node("l3a", level=3)
        l3b = make_node("l3b", level=3)

        edges = [
            make_edge("l1", "l2", EdgeType.DELEGATION),
            make_edge("l2", "l3a", EdgeType.DELEGATION),
            make_edge("l3a", "l2", EdgeType.REVIEW_GATE),
            make_edge("l2", "l1", EdgeType.REVIEW_GATE),
            make_edge("l1", "l2", EdgeType.ESCALATION),
        ]

        result = classifier.classify(make_graph(nodes=[l1, l2, l3a, l3b], edges=edges))

        assert result.archetype == "robust"
        assert "review-heavy" in result.traits

    def test_robust_has_fallback_roles_trait(self):
        """Escalation edges should give 'fallback-roles' trait."""
        l1 = make_node("l1", level=1)
        l2 = make_node("l2", level=2)

        edges = [
            make_edge("l1", "l2", EdgeType.DELEGATION),
            make_edge("l2", "l1", EdgeType.REVIEW_GATE),
            make_edge("l2", "l1", EdgeType.ESCALATION),
        ]

        result = classifier.classify(make_graph(nodes=[l1, l2], edges=edges))

        assert result.archetype == "robust"
        assert "fallback-roles" in result.traits


# --- Balanced archetype tests ---

class TestBalancedArchetype:
    def test_balanced_tree_with_coordination(self):
        """Tree topology with coordination edges = balanced."""
        l1 = make_node("orchestrator", level=1)
        l2a = make_node("pm-a", level=2)
        l2b = make_node("pm-b", level=2)

        edges = [
            make_edge("orchestrator", "pm-a", EdgeType.DELEGATION),
            make_edge("orchestrator", "pm-b", EdgeType.DELEGATION),
            make_edge("pm-a", "pm-b", EdgeType.COORDINATION),
        ]

        result = classifier.classify(make_graph(nodes=[l1, l2a, l2b], edges=edges))

        assert result.archetype == "balanced"

    def test_balanced_with_single_review_gate_no_escalation(self):
        """Single review gate without escalation = balanced (not robust)."""
        l1 = make_node("l1", level=1)
        l2 = make_node("l2", level=2)

        edges = [
            make_edge("l1", "l2", EdgeType.DELEGATION),
            make_edge("l2", "l1", EdgeType.REVIEW_GATE),
        ]

        result = classifier.classify(make_graph(nodes=[l1, l2], edges=edges))

        # Should be balanced (review gate but no escalation or multiple coord paths)
        assert result.archetype == "balanced"

    def test_balanced_has_coordination_linked_trait(self):
        """Balanced topology with coordination edges should have 'coordination-linked' trait."""
        l1 = make_node("orchestrator", level=1)
        l2a = make_node("pm-a", level=2)
        l2b = make_node("pm-b", level=2)

        edges = [
            make_edge("orchestrator", "pm-a", EdgeType.DELEGATION),
            make_edge("orchestrator", "pm-b", EdgeType.DELEGATION),
            make_edge("pm-a", "pm-b", EdgeType.COORDINATION),
        ]

        result = classifier.classify(make_graph(nodes=[l1, l2a, l2b], edges=edges))

        assert result.archetype == "balanced"
        assert "coordination-linked" in result.traits


# --- Determinism tests ---

class TestDeterminism:
    def test_classification_is_deterministic(self):
        """Same graph always gets same result across 100 runs."""
        nodes = [make_node("l1", level=1), make_node("l2", level=2), make_node("l3", level=3)]
        edges = [
            make_edge("l1", "l2", EdgeType.DELEGATION),
            make_edge("l2", "l3", EdgeType.DELEGATION),
        ]
        graph = make_graph(nodes=nodes, edges=edges)

        first_result = classifier.classify(graph)

        for _ in range(99):
            result = classifier.classify(graph)
            assert result.archetype == first_result.archetype
            assert result.confidence == first_result.confidence
            assert result.explanation == first_result.explanation
            assert result.traits == first_result.traits

    def test_same_input_same_archetype_different_graphs(self):
        """Two structurally identical graphs give identical results."""
        def make_balanced():
            l1 = make_node("orchestrator", level=1)
            l2a = make_node("pm-a", level=2)
            l2b = make_node("pm-b", level=2)
            edges = [
                make_edge("orchestrator", "pm-a", EdgeType.DELEGATION),
                make_edge("orchestrator", "pm-b", EdgeType.DELEGATION),
                make_edge("pm-a", "pm-b", EdgeType.COORDINATION),
            ]
            return make_graph(nodes=[l1, l2a, l2b], edges=edges)

        g1 = make_balanced()
        g2 = make_balanced()

        r1 = classifier.classify(g1)
        r2 = classifier.classify(g2)

        assert r1.archetype == r2.archetype
        assert r1.confidence == r2.confidence


# --- Edge case tests ---

class TestEdgeCases:
    def test_edge_case_gets_nearest_archetype(self):
        """Ambiguous graph still gets a classification, never raises."""
        # Graph with all edge types mixed
        nodes = [make_node(f"n{i}", level=(i % 3) + 1) for i in range(5)]
        edges = [
            make_edge("n0", "n1", EdgeType.DELEGATION),
            make_edge("n1", "n2", EdgeType.COORDINATION),
            make_edge("n2", "n3", EdgeType.INFORMATION_FLOW),
            make_edge("n3", "n0", EdgeType.REVIEW_GATE),
        ]
        graph = make_graph(nodes=nodes, edges=edges)

        result = classifier.classify(graph)

        assert result.archetype in {"lean", "balanced", "robust"}
        assert len(result.explanation) > 0

    def test_single_node_classifies(self):
        """Single node graph classifies without error."""
        result = classifier.classify(make_graph(nodes=[make_node("solo")]))
        assert result.archetype in {"lean", "balanced", "robust"}

    def test_empty_graph_classifies(self):
        """Empty graph classifies without error."""
        result = classifier.classify(make_graph())
        assert result.archetype in {"lean", "balanced", "robust"}

    def test_information_flow_only_graph(self):
        """Graph with only information_flow edges — should be lean or balanced."""
        nodes = [make_node(f"n{i}", level=2) for i in range(3)]
        edges = [
            make_edge("n0", "n1", EdgeType.INFORMATION_FLOW),
            make_edge("n1", "n2", EdgeType.INFORMATION_FLOW),
        ]
        result = classifier.classify(make_graph(nodes=nodes, edges=edges))
        # Should not raise, and should return valid archetype
        assert result.archetype in {"lean", "balanced", "robust"}
