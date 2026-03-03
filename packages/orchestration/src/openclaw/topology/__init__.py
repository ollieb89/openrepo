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
]
