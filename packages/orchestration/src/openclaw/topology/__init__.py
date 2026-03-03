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

__all__ = [
    "EdgeType",
    "TopologyNode",
    "TopologyEdge",
    "TopologyGraph",
    "save_topology",
    "load_topology",
]
