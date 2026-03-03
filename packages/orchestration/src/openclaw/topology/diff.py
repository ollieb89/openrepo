"""
Topology Diff Engine

Computes structural deltas between two TopologyGraph versions.
Used for changelog entries, correction tracking, and Phase 64 enrichment.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .models import TopologyGraph, TopologyNode, TopologyEdge, EdgeType


@dataclass
class TopologyDiff:
    """
    Represents the structural differences between two topology graphs.

    Fields contain lists of dicts for serialization compatibility.
    The annotations dict is mutable for Phase 64 structural memory enrichment.
    """

    added_nodes: List[dict] = field(default_factory=list)
    removed_nodes: List[dict] = field(default_factory=list)
    modified_nodes: List[dict] = field(default_factory=list)
    added_edges: List[dict] = field(default_factory=list)
    removed_edges: List[dict] = field(default_factory=list)
    modified_edges: List[dict] = field(default_factory=list)
    summary: str = ""
    annotations: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict for changelog entries."""
        return {
            "added_nodes": self.added_nodes,
            "removed_nodes": self.removed_nodes,
            "modified_nodes": self.modified_nodes,
            "added_edges": self.added_edges,
            "removed_edges": self.removed_edges,
            "modified_edges": self.modified_edges,
            "summary": self.summary,
            "annotations": self.annotations,
        }


def _node_to_dict(node: TopologyNode) -> dict:
    """Convert a TopologyNode to a plain dict for diff storage."""
    return {
        "id": node.id,
        "level": node.level,
        "intent": node.intent,
        "risk_level": node.risk_level,
        "resource_constraints": node.resource_constraints,
        "estimated_load": node.estimated_load,
    }


def _edge_to_dict(edge: TopologyEdge) -> dict:
    """Convert a TopologyEdge to a plain dict for diff storage."""
    return {
        "from_role": edge.from_role,
        "to_role": edge.to_role,
        "edge_type": edge.edge_type.value,
    }


def _compare_nodes(old_node: TopologyNode, new_node: TopologyNode) -> dict:
    """
    Compare two nodes with the same id and return a changes dict.

    Returns a dict like:
    {"field_name": {"old": old_value, "new": new_value}, ...}
    """
    changes = {}
    fields_to_compare = ["level", "intent", "risk_level", "resource_constraints", "estimated_load"]

    for f in fields_to_compare:
        old_val = getattr(old_node, f)
        new_val = getattr(new_node, f)
        if old_val != new_val:
            changes[f] = {"old": old_val, "new": new_val}

    return changes


def topology_diff(old: TopologyGraph, new: TopologyGraph) -> TopologyDiff:
    """
    Compute the structural diff between two topology graphs.

    Nodes are matched by id. Edges are matched by (from_role, to_role) tuple.
    Modified edges are same endpoints but different edge_type.

    Returns a TopologyDiff with all change categories populated and a
    human-readable summary.
    """
    # --- Node diff ---
    old_nodes_by_id = {n.id: n for n in old.nodes}
    new_nodes_by_id = {n.id: n for n in new.nodes}

    old_ids = set(old_nodes_by_id.keys())
    new_ids = set(new_nodes_by_id.keys())

    added_node_ids = new_ids - old_ids
    removed_node_ids = old_ids - new_ids
    common_node_ids = old_ids & new_ids

    added_nodes = [_node_to_dict(new_nodes_by_id[nid]) for nid in sorted(added_node_ids)]
    removed_nodes = [_node_to_dict(old_nodes_by_id[nid]) for nid in sorted(removed_node_ids)]

    modified_nodes = []
    for nid in sorted(common_node_ids):
        changes = _compare_nodes(old_nodes_by_id[nid], new_nodes_by_id[nid])
        if changes:
            modified_nodes.append({"id": nid, "changes": changes})

    # --- Edge diff ---
    # Match edges by (from_role, to_role) endpoint pair
    old_edges_by_endpoints = {(e.from_role, e.to_role): e for e in old.edges}
    new_edges_by_endpoints = {(e.from_role, e.to_role): e for e in new.edges}

    old_endpoints = set(old_edges_by_endpoints.keys())
    new_endpoints = set(new_edges_by_endpoints.keys())

    # Identify endpoint pairs present in both — check for edge_type modifications
    common_endpoints = old_endpoints & new_endpoints
    modified_edges = []
    for ep in sorted(common_endpoints):
        old_edge = old_edges_by_endpoints[ep]
        new_edge = new_edges_by_endpoints[ep]
        if old_edge.edge_type != new_edge.edge_type:
            modified_edges.append({
                "from_role": ep[0],
                "to_role": ep[1],
                "old_edge_type": old_edge.edge_type,
                "new_edge_type": new_edge.edge_type,
            })

    # For added/removed, exclude modified (same endpoints, different type)
    modified_endpoints = {(m["from_role"], m["to_role"]) for m in modified_edges}

    added_endpoint_keys = new_endpoints - old_endpoints
    removed_endpoint_keys = old_endpoints - new_endpoints

    added_edges = [_edge_to_dict(new_edges_by_endpoints[ep]) for ep in sorted(added_endpoint_keys)]
    removed_edges = [_edge_to_dict(old_edges_by_endpoints[ep]) for ep in sorted(removed_endpoint_keys)]

    # --- Build summary ---
    summary_parts = []

    if added_nodes:
        ids = ", ".join(n["id"] for n in added_nodes)
        summary_parts.append(f"Added nodes: {ids}")

    if removed_nodes:
        ids = ", ".join(n["id"] for n in removed_nodes)
        summary_parts.append(f"Removed nodes: {ids}")

    if modified_nodes:
        mods = []
        for m in modified_nodes:
            change_descs = []
            for f, vals in m["changes"].items():
                change_descs.append(f"{f} from {vals['old']} to {vals['new']}")
            mods.append(f"{m['id']} changed {', '.join(change_descs)}")
        summary_parts.append(f"Modified: {'; '.join(mods)}")

    if added_edges:
        edge_descs = [f"{e['from_role']}\u2192{e['to_role']} ({e['edge_type']})" for e in added_edges]
        summary_parts.append(f"Added edges: {', '.join(edge_descs)}")

    if removed_edges:
        edge_descs = [f"{e['from_role']}\u2192{e['to_role']} ({e['edge_type']})" for e in removed_edges]
        summary_parts.append(f"Removed edges: {', '.join(edge_descs)}")

    if modified_edges:
        edge_descs = [
            f"{m['from_role']}\u2192{m['to_role']} ({m['old_edge_type'].value}\u2192{m['new_edge_type'].value})"
            for m in modified_edges
        ]
        summary_parts.append(f"Modified edges: {', '.join(edge_descs)}")

    summary = ". ".join(summary_parts) if summary_parts else "No structural changes"

    return TopologyDiff(
        added_nodes=added_nodes,
        removed_nodes=removed_nodes,
        modified_nodes=modified_nodes,
        added_edges=added_edges,
        removed_edges=removed_edges,
        modified_edges=modified_edges,
        summary=summary,
    )


def format_diff(diff: TopologyDiff) -> str:
    """
    Format a TopologyDiff as a multi-line human-readable string for terminal display.

    Empty sections are skipped.
    """
    lines = []

    if diff.added_nodes:
        lines.append("ADDED NODES")
        for n in diff.added_nodes:
            lines.append(f"  + {n['id']} (level={n['level']}, intent={n['intent']}, risk={n['risk_level']})")

    if diff.removed_nodes:
        lines.append("REMOVED NODES")
        for n in diff.removed_nodes:
            lines.append(f"  - {n['id']} (level={n['level']}, intent={n['intent']}, risk={n['risk_level']})")

    if diff.modified_nodes:
        lines.append("MODIFIED NODES")
        for m in diff.modified_nodes:
            lines.append(f"  ~ {m['id']}")
            for f, vals in m["changes"].items():
                lines.append(f"      {f}: {vals['old']} -> {vals['new']}")

    if diff.added_edges:
        lines.append("ADDED EDGES")
        for e in diff.added_edges:
            lines.append(f"  + {e['from_role']} -> {e['to_role']} ({e['edge_type']})")

    if diff.removed_edges:
        lines.append("REMOVED EDGES")
        for e in diff.removed_edges:
            lines.append(f"  - {e['from_role']} -> {e['to_role']} ({e['edge_type']})")

    if diff.modified_edges:
        lines.append("MODIFIED EDGES")
        for m in diff.modified_edges:
            lines.append(
                f"  ~ {m['from_role']} -> {m['to_role']}: "
                f"{m['old_edge_type'].value} -> {m['new_edge_type'].value}"
            )

    if not lines:
        return "No structural changes."

    return "\n".join(lines)
