"""
Tests for topology diff engine.

Tests structural delta computation between two TopologyGraph versions.
"""

import pytest
from openclaw.topology.models import (
    TopologyGraph,
    TopologyNode,
    TopologyEdge,
    EdgeType,
)
from openclaw.topology.diff import topology_diff, TopologyDiff, format_diff


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


# --- Tests ---

class TestIdenticalTopologies:
    def test_identical_topologies_no_changes(self):
        node_a = make_node("agent-a")
        node_b = make_node("agent-b")
        edge = make_edge("agent-a", "agent-b")

        graph = make_graph(nodes=[node_a, node_b], edges=[edge])
        diff = topology_diff(graph, graph)

        assert diff.added_nodes == []
        assert diff.removed_nodes == []
        assert diff.modified_nodes == []
        assert diff.added_edges == []
        assert diff.removed_edges == []
        assert diff.modified_edges == []

    def test_identical_topologies_summary_no_changes(self):
        graph = make_graph(nodes=[make_node("a")], edges=[])
        diff = topology_diff(graph, graph)
        assert "No structural changes" in diff.summary


class TestNodeChanges:
    def test_added_node_detected(self):
        old_graph = make_graph(nodes=[make_node("agent-a")])
        new_graph = make_graph(nodes=[make_node("agent-a"), make_node("agent-b")])

        diff = topology_diff(old_graph, new_graph)

        assert len(diff.added_nodes) == 1
        assert diff.added_nodes[0]["id"] == "agent-b"
        assert diff.removed_nodes == []
        assert diff.modified_nodes == []

    def test_removed_node_detected(self):
        old_graph = make_graph(nodes=[make_node("agent-a"), make_node("agent-b")])
        new_graph = make_graph(nodes=[make_node("agent-a")])

        diff = topology_diff(old_graph, new_graph)

        assert len(diff.removed_nodes) == 1
        assert diff.removed_nodes[0]["id"] == "agent-b"
        assert diff.added_nodes == []
        assert diff.modified_nodes == []

    def test_modified_node_detected_risk_level(self):
        old_node = make_node("agent-a", risk_level="low")
        new_node = make_node("agent-a", risk_level="high")

        old_graph = make_graph(nodes=[old_node])
        new_graph = make_graph(nodes=[new_node])

        diff = topology_diff(old_graph, new_graph)

        assert len(diff.modified_nodes) == 1
        mod = diff.modified_nodes[0]
        assert mod["id"] == "agent-a"
        assert "risk_level" in mod["changes"]
        assert mod["changes"]["risk_level"]["old"] == "low"
        assert mod["changes"]["risk_level"]["new"] == "high"

    def test_modified_node_detected_intent(self):
        old_node = make_node("agent-a", intent="task execution")
        new_node = make_node("agent-a", intent="review coordination")

        old_graph = make_graph(nodes=[old_node])
        new_graph = make_graph(nodes=[new_node])

        diff = topology_diff(old_graph, new_graph)

        assert len(diff.modified_nodes) == 1
        mod = diff.modified_nodes[0]
        assert "intent" in mod["changes"]

    def test_multiple_field_changes_on_same_node(self):
        old_node = TopologyNode(id="a", level=2, intent="task", risk_level="low")
        new_node = TopologyNode(id="a", level=3, intent="orchestration", risk_level="high")

        diff = topology_diff(make_graph(nodes=[old_node]), make_graph(nodes=[new_node]))

        mod = diff.modified_nodes[0]
        assert "level" in mod["changes"]
        assert "intent" in mod["changes"]
        assert "risk_level" in mod["changes"]


class TestEdgeChanges:
    def test_added_edge_detected(self):
        node_a = make_node("agent-a")
        node_b = make_node("agent-b")

        old_graph = make_graph(nodes=[node_a, node_b], edges=[])
        new_edge = make_edge("agent-a", "agent-b")
        new_graph = make_graph(nodes=[node_a, node_b], edges=[new_edge])

        diff = topology_diff(old_graph, new_graph)

        assert len(diff.added_edges) == 1
        assert diff.added_edges[0]["from_role"] == "agent-a"
        assert diff.added_edges[0]["to_role"] == "agent-b"
        assert diff.removed_edges == []

    def test_removed_edge_detected(self):
        node_a = make_node("agent-a")
        node_b = make_node("agent-b")
        edge = make_edge("agent-a", "agent-b", EdgeType.DELEGATION)

        old_graph = make_graph(nodes=[node_a, node_b], edges=[edge])
        new_graph = make_graph(nodes=[node_a, node_b], edges=[])

        diff = topology_diff(old_graph, new_graph)

        assert len(diff.removed_edges) == 1
        assert diff.removed_edges[0]["from_role"] == "agent-a"
        assert diff.added_edges == []

    def test_modified_edge_type_detected(self):
        node_a = make_node("agent-a")
        node_b = make_node("agent-b")

        old_edge = make_edge("agent-a", "agent-b", EdgeType.DELEGATION)
        new_edge = make_edge("agent-a", "agent-b", EdgeType.COORDINATION)

        old_graph = make_graph(nodes=[node_a, node_b], edges=[old_edge])
        new_graph = make_graph(nodes=[node_a, node_b], edges=[new_edge])

        diff = topology_diff(old_graph, new_graph)

        assert len(diff.modified_edges) == 1
        mod = diff.modified_edges[0]
        assert mod["from_role"] == "agent-a"
        assert mod["to_role"] == "agent-b"
        assert mod["old_edge_type"] == EdgeType.DELEGATION
        assert mod["new_edge_type"] == EdgeType.COORDINATION
        # Modified edges should not appear in added/removed
        assert diff.added_edges == []
        assert diff.removed_edges == []


class TestSerializability:
    def test_diff_to_dict_serializable(self):
        """TopologyDiff.to_dict() must return a JSON-serializable dict."""
        import json

        old_graph = make_graph(nodes=[make_node("a"), make_node("b")], edges=[make_edge("a", "b")])
        new_node = make_node("c")
        new_graph = make_graph(nodes=[make_node("a"), new_node], edges=[])

        diff = topology_diff(old_graph, new_graph)
        result = diff.to_dict()

        # Must serialize without error
        serialized = json.dumps(result)
        assert serialized is not None

        # Must have expected keys
        assert "added_nodes" in result
        assert "removed_nodes" in result
        assert "modified_nodes" in result
        assert "added_edges" in result
        assert "removed_edges" in result
        assert "modified_edges" in result
        assert "summary" in result
        assert "annotations" in result

    def test_annotations_field_present_and_mutable(self):
        """TopologyDiff must have an annotations field for Phase 64 enrichment."""
        graph = make_graph(nodes=[make_node("a")])
        diff = topology_diff(graph, graph)

        assert hasattr(diff, "annotations")
        assert isinstance(diff.annotations, dict)

        # Must be mutable (Phase 64 enrichment requirement)
        diff.annotations["structural_insight"] = "test"
        assert diff.annotations["structural_insight"] == "test"


class TestSummary:
    def test_diff_summary_human_readable_with_changes(self):
        old_graph = make_graph(nodes=[make_node("agent-a")])
        new_graph = make_graph(nodes=[make_node("agent-a"), make_node("agent-b")])

        diff = topology_diff(old_graph, new_graph)

        assert isinstance(diff.summary, str)
        assert len(diff.summary) > 0
        # Should mention the added node
        assert "agent-b" in diff.summary or "Added" in diff.summary or "added" in diff.summary

    def test_diff_summary_empty_graph(self):
        empty = make_graph()
        diff = topology_diff(empty, empty)
        assert "No structural changes" in diff.summary


class TestFormatDiff:
    def test_format_diff_returns_string(self):
        graph = make_graph(nodes=[make_node("a")])
        diff = topology_diff(graph, graph)
        output = format_diff(diff)
        assert isinstance(output, str)

    def test_format_diff_includes_sections_for_changes(self):
        old_graph = make_graph(nodes=[make_node("a"), make_node("b")])
        new_graph = make_graph(nodes=[make_node("a"), make_node("c")])

        diff = topology_diff(old_graph, new_graph)
        output = format_diff(diff)

        assert "ADDED NODES" in output
        assert "REMOVED NODES" in output

    def test_format_diff_skips_empty_sections(self):
        """format_diff must not show sections with no entries."""
        old_graph = make_graph(nodes=[make_node("a")])
        new_graph = make_graph(nodes=[make_node("a"), make_node("b")])

        diff = topology_diff(old_graph, new_graph)
        output = format_diff(diff)

        # Only added nodes changed — removed/modified sections should be absent
        assert "REMOVED NODES" not in output
        assert "MODIFIED NODES" not in output
