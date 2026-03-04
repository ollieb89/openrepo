"""
Topology Proposal Rubric Scorer

Scores topology proposals across 7 dimensions (0-10 integers) to produce
a quantitative RubricScore. Higher is always better across all dimensions.

Design decisions:
- Complexity score inverts raw count: simple topologies score high.
- preference_fit is always 5 pre-Phase 64 (neutral baseline; Phase 64 adds
  preference learning so this becomes dynamic).
- overall_confidence is a weighted average of the 6 measured dimensions.
- find_key_differentiators identifies dimensions with >= 3 spread across proposals.
"""

from typing import List

from .models import TopologyGraph, EdgeType
from .proposal_models import RubricScore


# Default scoring weights. Sum to 1.0.
DEFAULT_WEIGHTS: dict = {
    "complexity":             0.15,
    "coordination_overhead":  0.15,
    "risk_containment":       0.20,
    "time_to_first_output":   0.20,
    "cost_estimate":          0.10,
    "preference_fit":         0.20,
}

# Ordered list of dimension names (excludes overall_confidence)
DIMENSIONS: List[str] = list(DEFAULT_WEIGHTS.keys())


def _clamp(value: int, lo: int = 0, hi: int = 10) -> int:
    return max(lo, min(hi, value))


class RubricScorer:
    """
    Scores a TopologyGraph across 6 measurable dimensions plus a weighted
    overall_confidence.

    Usage:
        scorer = RubricScorer()
        score = scorer.score_proposal(graph, weights={})  # empty = DEFAULT_WEIGHTS

    When weights={} is passed, DEFAULT_WEIGHTS are used. Pass a subset or
    full dict to override; missing keys fall back to DEFAULT_WEIGHTS.
    """

    def score_proposal(
        self,
        topology: TopologyGraph,
        weights: dict,
        project_id: str = None,
        archetype: str = None,
        explore: bool = None,
    ) -> RubricScore:
        """
        Score a topology graph.

        Args:
            topology: The TopologyGraph to score.
            weights: Dict of dimension -> float weights. Empty dict uses DEFAULT_WEIGHTS.
                     Missing keys fall back to DEFAULT_WEIGHTS.
            project_id: Optional project ID for dynamic preference_fit computation (Phase 64).
            archetype: Optional archetype name for dynamic preference_fit lookup.
            explore: Optional epsilon-greedy flag. When True, preference_fit is neutral (5).
                     Determined by caller at session level (not per-call).

        Returns:
            RubricScore with all 7 fields populated (key_differentiators is []).
        """
        effective_weights = {**DEFAULT_WEIGHTS, **weights}

        node_count = len(topology.nodes)
        edge_count = len(topology.edges)

        # Count edge types
        coordination_edge_count = sum(
            1 for e in topology.edges if e.edge_type == EdgeType.COORDINATION
        )
        review_gate_count = sum(
            1 for e in topology.edges if e.edge_type == EdgeType.REVIEW_GATE
        )
        escalation_count = sum(
            1 for e in topology.edges if e.edge_type == EdgeType.ESCALATION
        )

        # Compute chain depth (delegation-only paths)
        max_chain_depth = self._compute_chain_depth(topology)

        # --- Score each dimension ---

        # complexity: lower node/edge count = higher score
        complexity = _clamp(10 - node_count - edge_count // 2)

        # coordination_overhead: fewer coordination edges = higher score
        coordination_overhead = _clamp(10 - coordination_edge_count * 3)

        # risk_containment: more review gates and escalation paths = higher score
        risk_containment = _clamp(review_gate_count * 3 + escalation_count * 2)

        # time_to_first_output: shorter chain = higher score
        time_to_first_output = _clamp(10 - max_chain_depth * 2)

        # cost_estimate: fewer nodes = higher score (proxy for token/resource cost)
        cost_estimate = _clamp(10 - node_count * 2)

        # preference_fit: dynamic when project_id and archetype are provided (Phase 64)
        # Falls back to neutral 5 when context is insufficient (backward compatible)
        if project_id and archetype:
            from openclaw.topology.memory import MemoryProfiler
            from openclaw.config import get_topology_config
            topo_config = get_topology_config()
            profiler = MemoryProfiler(
                project_id,
                decay_lambda=topo_config["decay_lambda"],
                exploration_rate=topo_config["exploration_rate"],
                min_threshold=topo_config["pattern_extraction_threshold"],
            )
            preference_fit = profiler.get_preference_fit(
                archetype, explore=(explore if explore is not None else False)
            )
        else:
            preference_fit = 5  # Neutral when no context available

        # overall_confidence: weighted average of all 6 dimensions
        dim_scores = {
            "complexity":             complexity,
            "coordination_overhead":  coordination_overhead,
            "risk_containment":       risk_containment,
            "time_to_first_output":   time_to_first_output,
            "cost_estimate":          cost_estimate,
            "preference_fit":         preference_fit,
        }
        overall_confidence = _clamp(round(
            sum(dim_scores[d] * effective_weights[d] for d in DIMENSIONS)
        ))

        return RubricScore(
            complexity=complexity,
            coordination_overhead=coordination_overhead,
            risk_containment=risk_containment,
            time_to_first_output=time_to_first_output,
            cost_estimate=cost_estimate,
            preference_fit=preference_fit,
            overall_confidence=overall_confidence,
        )

    def _compute_chain_depth(self, topology: TopologyGraph) -> int:
        """
        Compute the longest delegation chain depth via DFS.

        Returns 0 for empty graphs, 1 for single-node graphs.
        """
        if not topology.nodes:
            return 0
        if not topology.edges:
            return 1

        # Build adjacency map for delegation edges only
        adj: dict = {n.id: [] for n in topology.nodes}
        for e in topology.edges:
            if e.edge_type == EdgeType.DELEGATION:
                adj.setdefault(e.from_role, []).append(e.to_role)

        max_depth = 1

        def dfs(node_id: str, depth: int, visited: set) -> int:
            best = depth
            for child in adj.get(node_id, []):
                if child not in visited:
                    child_depth = dfs(child, depth + 1, visited | {child})
                    best = max(best, child_depth)
            return best

        for node_id in adj:
            depth = dfs(node_id, 1, {node_id})
            max_depth = max(max_depth, depth)

        return max_depth


def score_proposal(
    topology: TopologyGraph,
    weights: dict,
    project_id: str = None,
    archetype: str = None,
    explore: bool = None,
) -> RubricScore:
    """Standalone wrapper around RubricScorer.score_proposal().

    Convenience function for use in CLI and other non-class contexts.

    Args:
        topology: The TopologyGraph to score.
        weights: Dict of dimension -> float weights. Empty dict uses DEFAULT_WEIGHTS.
        project_id: Optional project ID for dynamic preference_fit (Phase 64).
        archetype: Optional archetype name for preference_fit lookup.
        explore: Optional epsilon-greedy flag passed through to MemoryProfiler.

    Returns:
        RubricScore with all 7 fields populated.
    """
    return RubricScorer().score_proposal(
        topology, weights, project_id=project_id, archetype=archetype, explore=explore
    )


def find_key_differentiators(scores: List[RubricScore]) -> List[str]:
    """
    Identify dimensions where proposals differ most significantly.

    Returns dimension names where max - min across all scores >= 3,
    sorted by spread descending.

    Args:
        scores: List of RubricScore objects (typically 2-3 proposals).

    Returns:
        List of dimension name strings where spread >= 3. Empty list if
        fewer than 2 scores or all dimensions have < 3 spread.
    """
    if len(scores) < 2:
        return []

    spreads: List[tuple] = []
    for dim in DIMENSIONS:
        values = [getattr(s, dim) for s in scores]
        spread = max(values) - min(values)
        if spread >= 3:
            spreads.append((dim, spread))

    # Sort by spread descending for most-differentiating first
    spreads.sort(key=lambda x: x[1], reverse=True)
    return [dim for dim, _ in spreads]
