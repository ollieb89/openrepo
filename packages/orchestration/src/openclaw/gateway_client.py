"""HTTP client for the openclaw gateway (port 18789)."""

import json
import httpx
from dataclasses import dataclass
from typing import AsyncIterator, Optional
from openclaw.config import get_gateway_config
from openclaw.logging import get_logger

logger = get_logger("gateway_client")

@dataclass
class DispatchResult:
    run_id: str
    status: str  # "ok" | "error"
    output: Optional[str] = None
    error: Optional[str] = None

@dataclass
class GatewayClient:
    base_url: str
    auth_token: str
    timeout: float = 300.0  # 5 minutes default

    @classmethod
    def from_config(cls) -> "GatewayClient":
        config = get_gateway_config()
        return cls(
            base_url=f"http://localhost:{config.get('port', 18789)}",
            auth_token=config.get("token", ""),
        )

    async def dispatch(
        self, agent_id: str, message: str, timeout: Optional[float] = None
    ) -> DispatchResult:
        """Dispatch a directive to an agent via the gateway API."""
        async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/agent/{agent_id}/message",
                json={"message": message},
                headers={"Authorization": f"Bearer {self.auth_token}"},
            )
            data = response.json()
            return DispatchResult(
                run_id=data.get("runId", ""),
                status="ok" if response.is_success else "error",
                output=data.get("output"),
                error=data.get("error"),
            )

    async def dispatch_stream(
        self, agent_id: str, message: str
    ) -> AsyncIterator[dict]:
        """Stream dispatch — yields incremental updates as the agent works."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/agent/{agent_id}/message",
                json={"message": message, "stream": True},
                headers={"Authorization": f"Bearer {self.auth_token}"},
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        yield json.loads(line[6:])
