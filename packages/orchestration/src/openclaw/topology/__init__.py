"""
OpenClaw Topology Package

Provides data models and file storage for agent topology graphs.
"""

from .models import (
    EdgeType,
    TopologyNode,
    TopologyEdge,
    TopologyGraph,
)
from .storage import (
    save_topology,
    load_topology,
)
from .diff import (
    TopologyDiff,
    topology_diff,
    format_diff,
)
from .classifier import (
    ArchetypeClassifier,
    ArchetypeResult,
)
from .proposal_models import (
    RubricScore,
    TopologyProposal,
    ProposalSet,
)
from .rubric import (
    RubricScorer,
    find_key_differentiators,
    DEFAULT_WEIGHTS,
    DIMENSIONS,
)

__all__ = [
    "EdgeType",
    "TopologyNode",
    "TopologyEdge",
    "TopologyGraph",
    "save_topology",
    "load_topology",
    "TopologyDiff",
    "topology_diff",
    "format_diff",
    "ArchetypeClassifier",
    "ArchetypeResult",
    "RubricScore",
    "TopologyProposal",
    "ProposalSet",
    "RubricScorer",
    "find_key_differentiators",
    "DEFAULT_WEIGHTS",
    "DIMENSIONS",
]
