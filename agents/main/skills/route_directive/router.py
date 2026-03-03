"""Route directives from L1 to the appropriate L2 PM via gateway API."""

from openclaw.gateway_client import GatewayClient
from openclaw.project_config import load_and_validate_openclaw_config

class DirectiveRouter:
    def __init__(self):
        self.client = GatewayClient.from_config()
        self.config = load_and_validate_openclaw_config()

    async def route(self, directive: str, context: dict = None) -> dict:
        """Analyze directive and route to the best PM agent."""
        target = self._resolve_target(directive, context)
        result = await self.client.dispatch(target, directive)
        return {"target": target, "run_id": result.run_id, "status": result.status}

    def _resolve_target(self, directive: str, context: dict) -> str:
        """Resolve target agent using project registry and keyword matching."""
        # Uses agents/main/agent/config.json project_registry
        # Priority: propose -> explicit mention → stack detection → generic → escalate

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
