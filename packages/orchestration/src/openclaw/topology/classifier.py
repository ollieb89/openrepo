"""
Topology Archetype Classifier

Pattern-matching classification of topology graphs into Lean, Balanced,
or Robust archetypes based on structural shape analysis.

Design decision (Phase 61 CONTEXT): Uses pattern-matching, NOT hard numeric
thresholds, so classification adapts naturally to graph size.
"""

from dataclasses import dataclass, field
from typing import List, Set, Tuple

from .models import TopologyGraph, EdgeType


@dataclass
class ArchetypeResult:
    """
    Result of an archetype classification.

    archetype: "lean", "balanced", or "robust"
    confidence: 0.0-1.0 — how strongly the graph matches the archetype
    explanation: human-readable reason for the classification (always non-empty)
    traits: list of structural annotations, e.g. "review-heavy", "flat-delegation"
    """

    archetype: str
    confidence: float
    explanation: str
    traits: List[str] = field(default_factory=list)


class ArchetypeClassifier:
    """
    Classifies a TopologyGraph into one of three archetypes:

    - Lean: linear chain or flat delegation, no coordination/review gates
    - Balanced: tree with coordination and/or review edges, moderate structure
    - Robust: DAG with review gates AND (escalation or multiple coordination paths)

    Classification is deterministic — same graph always returns same result.
    """

    def classify(self, graph: TopologyGraph) -> ArchetypeResult:
        """
        Classify the graph into an archetype using pattern matching.

        Returns an ArchetypeResult with archetype, confidence, explanation, and traits.
        """
        features = self._compute_features(graph)
        return self._match_archetype(features)

    # --- Internal feature extraction ---

    def _compute_features(self, graph: TopologyGraph) -> dict:
        """
        Compute structural features for pattern matching.

        Returns a dict with keys:
        - node_count, edge_count
        - delegation_edges, coordination_edges, review_gates, escalation_edges, info_flow_edges
        - max_depth: longest delegation chain
        - has_multiple_coordination_paths: bool
        """
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)

        delegation_edges = sum(1 for e in graph.edges if e.edge_type == EdgeType.DELEGATION)
        coordination_edges = sum(1 for e in graph.edges if e.edge_type == EdgeType.COORDINATION)
        review_gates = sum(1 for e in graph.edges if e.edge_type == EdgeType.REVIEW_GATE)
        escalation_edges = sum(1 for e in graph.edges if e.edge_type == EdgeType.ESCALATION)
        info_flow_edges = sum(1 for e in graph.edges if e.edge_type == EdgeType.INFORMATION_FLOW)

        max_depth = self._compute_max_depth(graph)
        has_multiple_coordination_paths = self._has_multiple_coordination_paths(graph)

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "delegation_edges": delegation_edges,
            "coordination_edges": coordination_edges,
            "review_gates": review_gates,
            "escalation_edges": escalation_edges,
            "info_flow_edges": info_flow_edges,
            "max_depth": max_depth,
            "has_multiple_coordination_paths": has_multiple_coordination_paths,
        }

    def _compute_max_depth(self, graph: TopologyGraph) -> int:
        """
        Compute the longest path through delegation edges using BFS/DFS.

        Returns 0 for empty graphs, 1 for a single node, etc.
        """
        if not graph.nodes:
            return 0
        if not graph.edges:
            return 1

        # Build adjacency map for delegation edges only
        delegation_adj: dict = {n.id: [] for n in graph.nodes}
        for e in graph.edges:
            if e.edge_type == EdgeType.DELEGATION:
                delegation_adj.setdefault(e.from_role, []).append(e.to_role)

        # DFS to find max depth from any starting node
        visited: Set[str] = set()
        max_depth = 1

        def dfs(node_id: str, depth: int, path: Set[str]) -> int:
            """DFS that avoids cycles."""
            best = depth
            for neighbor in delegation_adj.get(node_id, []):
                if neighbor not in path:
                    child_depth = dfs(neighbor, depth + 1, path | {neighbor})
                    best = max(best, child_depth)
            return best

        all_ids = {n.id for n in graph.nodes}
        for node_id in all_ids:
            depth = dfs(node_id, 1, {node_id})
            max_depth = max(max_depth, depth)

        return max_depth

    def _has_multiple_coordination_paths(self, graph: TopologyGraph) -> bool:
        """
        Check if any node is reachable via more than one coordination path.

        A node has multiple coordination paths if it has 2+ incoming coordination edges.
        """
        incoming_coordination: dict = {}
        for e in graph.edges:
            if e.edge_type == EdgeType.COORDINATION:
                incoming_coordination.setdefault(e.to_role, 0)
                incoming_coordination[e.to_role] += 1

        return any(count > 1 for count in incoming_coordination.values())

    # --- Pattern matching ---

    def _match_archetype(self, features: dict) -> ArchetypeResult:
        """
        Apply pattern-matching rules to assign an archetype.

        Priority: Robust > Lean > Balanced
        (Robust has explicit structural requirements that are unambiguous)
        """
        coordination_edges = features["coordination_edges"]
        review_gates = features["review_gates"]
        escalation_edges = features["escalation_edges"]
        max_depth = features["max_depth"]
        edge_count = features["edge_count"]
        node_count = features["node_count"]
        has_multiple_coord = features["has_multiple_coordination_paths"]

        # --- ROBUST pattern ---
        # Requires: review gate AND (escalation OR multiple coordination paths)
        if review_gates >= 1 and (escalation_edges >= 1 or has_multiple_coord):
            traits = []
            reasons = []

            if review_gates > 1:
                traits.append("review-heavy")
                reasons.append(f"{review_gates} review gates")
            else:
                reasons.append("review gate present")

            if escalation_edges > 0:
                traits.append("fallback-roles")
                reasons.append(f"{escalation_edges} escalation path(s)")

            if has_multiple_coord:
                traits.append("redundant-paths")
                reasons.append("multiple coordination paths")

            # Confidence: strong if all robust features present
            robust_feature_count = sum([
                review_gates > 1,
                escalation_edges > 0,
                has_multiple_coord,
            ])
            confidence = 0.9 if robust_feature_count >= 2 else (0.75 if robust_feature_count == 1 else 0.6)

            atypical = ""
            if coordination_edges == 0:
                atypical = "Atypical: review gate without coordination edges"

            explanation = (
                f"Classified as robust because {', '.join(reasons)}."
                + (f" {atypical}" if atypical else "")
            )

            return ArchetypeResult(
                archetype="robust",
                confidence=confidence,
                explanation=explanation,
                traits=traits,
            )

        # --- LEAN pattern ---
        # Requires: no coordination edges AND no review gates AND
        #           (linear chain OR flat delegation OR minimal edges)
        if coordination_edges == 0 and review_gates == 0:
            traits = []
            reasons = []

            # Check for linear chain: max_depth close to node count
            if node_count > 1 and max_depth >= node_count - 1:
                traits.append("linear-chain")
                reasons.append(f"linear delegation chain (depth {max_depth})")
            elif node_count == 0 or (edge_count <= node_count):
                traits.append("flat-delegation")
                reasons.append("flat delegation structure")

            # Fall-through if neither trait matches (still lean)
            if not traits:
                traits.append("flat-delegation")
                reasons.append("minimal structural complexity")

            # Confidence: high if clearly linear/flat, lower for ambiguous cases
            confidence = 0.9 if "linear-chain" in traits else 0.8

            explanation = (
                f"Classified as lean because {', '.join(reasons)}."
                " No coordination or review gate edges present."
            )

            return ArchetypeResult(
                archetype="lean",
                confidence=confidence,
                explanation=explanation,
                traits=traits,
            )

        # --- BALANCED pattern (everything else) ---
        # Has coordination or review gate, but doesn't meet robust threshold
        traits = []
        reasons = []

        if coordination_edges > 0:
            traits.append("coordination-linked")
            reasons.append(f"{coordination_edges} coordination edge(s)")

        if review_gates > 0:
            traits.append("review-gated")
            reasons.append(f"{review_gates} review gate(s)")

        if not reasons:
            # Fallback: info-flow only or mixed without strong pattern
            reasons.append("moderate structural complexity")

        # Confidence: based on how clearly it matches balanced features
        match_count = sum([coordination_edges > 0, review_gates > 0])
        confidence = 0.8 if match_count >= 2 else (0.7 if match_count == 1 else 0.6)

        explanation = (
            f"Classified as balanced because {', '.join(reasons)}."
            " Structure has coordination but does not meet robust threshold."
        )

        return ArchetypeResult(
            archetype="balanced",
            confidence=confidence,
            explanation=explanation,
            traits=traits,
        )
