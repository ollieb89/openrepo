"""Route directives from L1 to the appropriate L2 PM via gateway API."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from openclaw.project_config import load_and_validate_openclaw_config


class RouteType(Enum):
    TO_PM = "to_pm"
    SPAWN_L3 = "spawn_l3"
    COORDINATE = "coordinate"
    ESCALATE = "escalate"
    QUEUE = "queue"


@dataclass
class RouteDecision:
    route_type: RouteType
    target: str
    reasoning: str
    confidence: float
    priority: str
    alternatives: List[str] = field(default_factory=list)
    swarm_state: Optional[dict] = None


class DirectiveRouter:
    def __init__(self, config: Optional[dict] = None, swarm_query=None):
        self.config = config if config is not None else load_and_validate_openclaw_config()
        self.swarm_query = swarm_query

    def route(self, directive: str, context: dict = None) -> RouteDecision:
        """Analyze directive and route to the best PM agent."""
        target = self._resolve_target(directive, context)
        route_type = self._infer_route_type(target)
        return RouteDecision(
            route_type=route_type,
            target=target,
            reasoning=f"Keyword match routed to {target}",
            confidence=0.9,
            priority="normal",
        )

    def _infer_route_type(self, target: str) -> RouteType:
        """Infer RouteType from resolved target string."""
        if target == "__propose__":
            return RouteType.COORDINATE
        if target == "l3_specialist":
            return RouteType.SPAWN_L3
        return RouteType.TO_PM

    def _resolve_target(self, directive: str, context: dict) -> str:
        """Resolve target agent using project registry and keyword matching."""
        # Uses agents/main/agent/config.json project_registry
        # Priority: propose -> explicit mention -> stack detection -> generic -> escalate

        if not context:
            context = {}

        directive_lower = directive.lower()

        # Proposal engine: 'propose' or 'topology' keywords route to __propose__ sentinel
        # The JS router (skills/router/index.js) detects __propose__ and invokes openclaw-propose
        if "propose" in directive_lower or "topology" in directive_lower:
            return "__propose__"

        if "python" in directive_lower or "backend" in directive_lower:
            return "python_backend_worker"
        elif "react" in directive_lower or "next" in directive_lower or "frontend" in directive_lower:
            return "nextjs_pm"
        elif "pumpl" in directive_lower:
            return "pumplai_pm"
        elif "docs" in directive_lower:
            return "docs_pm"

        # default to l3_specialist or some general agent if not matching
        return "l3_specialist"
