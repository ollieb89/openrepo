"""Tests for topology data model and storage.

Covers:
- TopologyNode, TopologyEdge, TopologyGraph dataclass creation
- JSON round-trip serialization (zero data loss)
- EdgeType enum with all 5 values
- Storage: save_topology, load_topology, changelog
"""

import json
import pytest
from pathlib import Path

from openclaw.topology.models import (
    TopologyGraph,
    TopologyNode,
    TopologyEdge,
    EdgeType,
)


# ── Model / Serialization Tests ───────────────────────────────────────────────


def test_edge_type_values():
    """EdgeType enum has exactly 5 required values."""
    expected = {"delegation", "coordination", "review_gate", "information_flow", "escalation"}
    actual = {e.value for e in EdgeType}
    assert actual == expected


def test_node_serialization():
    """TopologyNode round-trips through to_dict / from_dict."""
    node = TopologyNode(
        id="clawdia_prime",
        level=1,
        intent="Strategic orchestration of all project agents",
        risk_level="high",
        resource_constraints={"mem": "4g", "cpu": 2},
        estimated_load=0.75,
    )
    d = node.to_dict()
    node2 = TopologyNode.from_dict(d)
    assert node2.id == node.id
    assert node2.level == node.level
    assert node2.intent == node.intent
    assert node2.risk_level == node.risk_level
    assert node2.resource_constraints == node.resource_constraints
    assert node2.estimated_load == node.estimated_load


def test_node_optional_fields_default_none():
    """TopologyNode without optional fields defaults to None."""
    node = TopologyNode(id="l3_specialist", level=3, intent="Execute tasks", risk_level="low")
    assert node.resource_constraints is None
    assert node.estimated_load is None
    d = node.to_dict()
    node2 = TopologyNode.from_dict(d)
    assert node2.resource_constraints is None
    assert node2.estimated_load is None


def test_edge_serialization():
    """TopologyEdge round-trips through to_dict / from_dict; edge_type is a string value."""
    edge = TopologyEdge(
        from_role="clawdia_prime",
        to_role="pumplai_pm",
        edge_type=EdgeType.DELEGATION,
    )
    d = edge.to_dict()
    assert d["edge_type"] == "delegation"  # stored as string value
    edge2 = TopologyEdge.from_dict(d)
    assert edge2.from_role == "clawdia_prime"
    assert edge2.to_role == "pumplai_pm"
    assert edge2.edge_type == EdgeType.DELEGATION


def test_graph_with_all_edge_types_roundtrip():
    """TopologyGraph containing all 5 edge types round-trips with zero data loss."""
    nodes = [
        TopologyNode(id="l1", level=1, intent="Orchestrate", risk_level="high"),
        TopologyNode(id="l2", level=2, intent="Manage", risk_level="medium"),
        TopologyNode(id="l3", level=3, intent="Execute", risk_level="low"),
    ]
    edges = [
        TopologyEdge("l1", "l2", EdgeType.DELEGATION),
        TopologyEdge("l1", "l2", EdgeType.COORDINATION),
        TopologyEdge("l2", "l3", EdgeType.REVIEW_GATE),
        TopologyEdge("l1", "l2", EdgeType.INFORMATION_FLOW),
        TopologyEdge("l2", "l1", EdgeType.ESCALATION),
    ]
    graph = TopologyGraph(
        nodes=nodes,
        edges=edges,
        project_id="test_project",
        proposal_id="prop-001",
        version=2,
        metadata={"source": "unit-test"},
    )
    graph2 = TopologyGraph.from_dict(graph.to_dict())
    assert graph.to_dict() == graph2.to_dict()


def test_empty_graph_roundtrip():
    """Empty TopologyGraph (no nodes, no edges) round-trips correctly."""
    graph = TopologyGraph(nodes=[], edges=[], project_id="empty_proj")
    graph2 = TopologyGraph.from_json(graph.to_json())
    assert graph.to_dict() == graph2.to_dict()
    assert graph2.nodes == []
    assert graph2.edges == []


def test_graph_created_at_auto_set():
    """TopologyGraph auto-sets created_at to ISO 8601 if not provided."""
    graph = TopologyGraph(nodes=[], edges=[], project_id="proj")
    assert graph.created_at != ""
    # Basic ISO 8601 check: contains 'T' separator
    assert "T" in graph.created_at


def test_graph_created_at_preserved_if_provided():
    """TopologyGraph preserves a caller-supplied created_at."""
    ts = "2026-01-01T00:00:00Z"
    graph = TopologyGraph(nodes=[], edges=[], project_id="proj", created_at=ts)
    assert graph.created_at == ts


def test_to_json_produces_valid_json():
    """to_json() returns a parseable JSON string."""
    graph = TopologyGraph(
        nodes=[TopologyNode("a", 2, "coordinator", "medium")],
        edges=[],
        project_id="json_proj",
    )
    raw = graph.to_json()
    parsed = json.loads(raw)
    assert parsed["project_id"] == "json_proj"


def test_from_json_roundtrip():
    """from_json(to_json()) produces an object equal to the original."""
    graph = TopologyGraph(
        nodes=[TopologyNode("a", 1, "orchestrator", "low", estimated_load=0.5)],
        edges=[TopologyEdge("a", "b", EdgeType.COORDINATION)],
        project_id="roundtrip_proj",
        proposal_id="p-99",
        version=3,
    )
    graph2 = TopologyGraph.from_json(graph.to_json())
    assert graph.to_dict() == graph2.to_dict()


# ── Storage Tests ─────────────────────────────────────────────────────────────


def test_save_and_load_topology(tmp_path, monkeypatch):
    """save_topology / load_topology round-trips through the filesystem."""
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

    from openclaw.topology.storage import save_topology, load_topology

    graph = TopologyGraph(
        nodes=[TopologyNode("l1", 1, "L1 agent", "high")],
        edges=[TopologyEdge("l1", "l2", EdgeType.DELEGATION)],
        project_id="fs_test",
    )
    save_topology("fs_test", graph)
    loaded = load_topology("fs_test")

    assert loaded is not None
    assert loaded.to_dict() == graph.to_dict()


def test_load_topology_missing_returns_none(tmp_path, monkeypatch):
    """load_topology returns None when current.json does not exist."""
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

    from openclaw.topology.storage import load_topology

    result = load_topology("nonexistent_project")
    assert result is None


def test_topology_dir_created_automatically(tmp_path, monkeypatch):
    """topology/ directory is created automatically on first save."""
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

    from openclaw.topology.storage import save_topology

    graph = TopologyGraph(nodes=[], edges=[], project_id="autocreate")
    save_topology("autocreate", graph)

    topo_dir = tmp_path / "workspace" / ".openclaw" / "autocreate" / "topology"
    assert topo_dir.is_dir()
    assert (topo_dir / "current.json").exists()


def test_changelog_append_and_load(tmp_path, monkeypatch):
    """append_changelog / load_changelog correctly accumulate entries."""
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

    from openclaw.topology.storage import append_changelog, load_changelog

    assert load_changelog("cl_proj") == []

    append_changelog("cl_proj", {"event": "created", "version": 1})
    append_changelog("cl_proj", {"event": "updated", "version": 2})

    entries = load_changelog("cl_proj")
    assert len(entries) == 2
    assert entries[0]["event"] == "created"
    assert entries[1]["event"] == "updated"


def test_bak_created_on_save(tmp_path, monkeypatch):
    """A .bak file is created when overwriting an existing current.json."""
    monkeypatch.setenv("OPENCLAW_ROOT", str(tmp_path))

    from openclaw.topology.storage import save_topology

    graph1 = TopologyGraph(nodes=[], edges=[], project_id="bak_proj")
    save_topology("bak_proj", graph1)

    graph2 = TopologyGraph(nodes=[], edges=[], project_id="bak_proj", version=2)
    save_topology("bak_proj", graph2)

    bak_path = tmp_path / "workspace" / ".openclaw" / "bak_proj" / "topology" / "current.json.bak"
    assert bak_path.exists()
