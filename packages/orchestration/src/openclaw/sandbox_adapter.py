"""Adapter to spawn L3 containers through openclaw's sandbox API."""

import json
from .gateway_client import GatewayClient
from .agent_registry import AgentRegistry, AgentLevel

class SandboxAdapter:
    """Routes L3 spawning through the openclaw sandbox instead of raw Docker."""

    def __init__(self, gateway: GatewayClient, registry: AgentRegistry):
        self.gateway = gateway
        self.registry = registry

    async def spawn_l3(
        self,
        task_id: str,
        skill_hint: str,
        project_id: str,
        directive: str,
        memory_context: str = "",
        volume_mounts: list = None,
        env_vars: dict = None,
    ) -> dict:
        """Spawn an L3 task via the openclaw sandbox API."""
        agent_spec = self.registry.get("l3_specialist")

        if not agent_spec:
            raise ValueError("l3_specialist agent spec not found in registry")

        # The gateway currently accepts messages. The L3 system expects
        # a JSON-encoded directive that openclaw.json routes appropriately
        result = await self.gateway.dispatch(
            agent_id="l3_specialist",
            message=self._build_l3_directive(
                task_id=task_id,
                skill_hint=skill_hint,
                directive=directive,
                memory_context=memory_context,
                volume_mounts=volume_mounts or [],
                env_vars=env_vars or {}
            ),
        )
        return {
            "task_id": task_id,
            "run_id": result.run_id,
            "status": result.status,
        }

    def _build_l3_directive(self, **kwargs) -> str:
        """Build the structured directive string for L3 execution."""
        return json.dumps({
            "type": "l3_task",
            "task_id": kwargs["task_id"],
            "skill_hint": kwargs["skill_hint"],
            "directive": kwargs["directive"],
            "memory_context": kwargs["memory_context"],
            "staging_branch": f"l3/task-{kwargs['task_id']}",
            "volume_mounts": kwargs["volume_mounts"],
            "env_vars": kwargs["env_vars"],
        })