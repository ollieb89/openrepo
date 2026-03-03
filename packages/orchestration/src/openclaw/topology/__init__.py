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

__all__ = [
    "EdgeType",
    "TopologyNode",
    "TopologyEdge",
    "TopologyGraph",
]
