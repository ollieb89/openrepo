"""
Topology Data Models

Core data structures for representing agent topology graphs.
These models capture the structural shape of an orchestration system.
Provides JSON serialization (to_dict/from_dict, to_json/from_json) for
storage and wire-transfer with zero data loss.
"""

import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class EdgeType(str, Enum):
    DELEGATION = "delegation"
    COORDINATION = "coordination"
    REVIEW_GATE = "review_gate"
    INFORMATION_FLOW = "information_flow"
    ESCALATION = "escalation"


@dataclass
class TopologyNode:
    """A single node in the topology graph representing an agent role."""

    id: str
    level: int          # 1, 2, or 3 — matching AgentLevel hierarchy
    intent: str         # What this role does (free text)
    risk_level: str     # "low", "medium", or "high"
    resource_constraints: Optional[Dict] = None   # e.g. {"mem": "4g", "cpu": 1}
    estimated_load: Optional[float] = None        # Estimated load factor (0.0–1.0)

    def to_dict(self) -> dict:
        """Serialize to a plain dict suitable for JSON encoding."""
        return {
            "id": self.id,
            "level": self.level,
            "intent": self.intent,
            "risk_level": self.risk_level,
            "resource_constraints": self.resource_constraints,
            "estimated_load": self.estimated_load,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TopologyNode":
        """Deserialize from a plain dict (as produced by to_dict)."""
        return cls(
            id=data["id"],
            level=data["level"],
            intent=data["intent"],
            risk_level=data["risk_level"],
            resource_constraints=data.get("resource_constraints"),
            estimated_load=data.get("estimated_load"),
        )


@dataclass
class TopologyEdge:
    """A directed edge between two roles in the topology graph."""

    from_role: str
    to_role: str
    edge_type: EdgeType

    def to_dict(self) -> dict:
        """Serialize to a plain dict; edge_type is stored as its string value."""
        return {
            "from_role": self.from_role,
            "to_role": self.to_role,
            "edge_type": self.edge_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TopologyEdge":
        """Deserialize from a plain dict (as produced by to_dict)."""
        return cls(
            from_role=data["from_role"],
            to_role=data["to_role"],
            edge_type=EdgeType(data["edge_type"]),
        )


@dataclass
class TopologyGraph:
    """
    A versioned, project-scoped topology graph with nodes and edges.

    Represents the structural shape of an orchestration system at a point
    in time. Supports full JSON round-trip serialization with zero data loss.
    """

    nodes: List[TopologyNode]
    edges: List[TopologyEdge]
    project_id: str
    proposal_id: Optional[str] = None
    version: int = 1
    created_at: str = ""      # ISO 8601; auto-set in __post_init__ if empty
    metadata: Optional[dict] = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Serialize the entire graph to a plain dict for JSON encoding."""
        return {
            "project_id": self.project_id,
            "proposal_id": self.proposal_id,
            "version": self.version,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TopologyGraph":
        """Deserialize from a plain dict (as produced by to_dict)."""
        return cls(
            project_id=data["project_id"],
            proposal_id=data.get("proposal_id"),
            version=data.get("version", 1),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata"),
            nodes=[TopologyNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[TopologyEdge.from_dict(e) for e in data.get("edges", [])],
        )

    def to_json(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "TopologyGraph":
        """Deserialize from a JSON string (as produced by to_json)."""
        return cls.from_dict(json.loads(json_str))
