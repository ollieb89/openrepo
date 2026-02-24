"""
MemoryClient — per-project, per-agent scoped wrapper around the memU REST API.

All memory operations are structurally scoped: project_id and agent_type are
required at construction time, making it impossible to issue unscoped requests.

Usage:
    from openclaw.memory_client import MemoryClient, AgentType

    async with MemoryClient("http://localhost:18791", "pumplai", AgentType.L3_CODE) as client:
        await client.memorize("task T-001 completed successfully")
        memories = await client.retrieve("what happened with T-001?")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

import httpx

from .logging import get_logger

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Retrieve timeout: 3s total, 2s connect — fast path, fail fast.
TIMEOUT_RETRIEVE = httpx.Timeout(3.0, connect=2.0)

#: Memorize timeout: 10s total, 2s connect — embedding generation is slow.
TIMEOUT_MEMORIZE = httpx.Timeout(10.0, connect=2.0)

#: Structured logger for this module.
logger = get_logger("memory_client")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class AgentType(str, Enum):
    """
    Identifies which tier of agent is issuing the memory operation.

    Inherits from str so that values serialize directly in JSON payloads
    without calling .value — e.g. AgentType.L3_CODE in a dict becomes "l3_code".
    """

    L2_PM = "l2_pm"
    L3_CODE = "l3_code"
    L3_TEST = "l3_test"


@dataclass(frozen=True)
class MemorizeResult:
    """Return value from a successful memorize() call."""

    accepted: bool
    message: str


@dataclass(frozen=True)
class RetrieveResult:
    """Return value from a successful retrieve() call (rarely used directly)."""

    items: List[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class MemoryClient:
    """
    Async HTTP client for the memU memory service with enforced project scoping.

    Both project_id and agent_type are required at construction time.
    Every memory operation automatically includes them — callers cannot omit them.

    Degradation behaviour:
        - health()    → False   (never raises)
        - memorize()  → None    (never raises)
        - retrieve()  → []      (never raises)

    Lifecycle:
        Use as an async context manager so the underlying httpx.AsyncClient is
        properly closed after the call site is done:

            async with MemoryClient(url, project_id, agent_type) as client:
                result = await client.memorize("...")
    """

    def __init__(
        self,
        base_url: str,
        project_id: str,
        agent_type: AgentType,
    ) -> None:
        """
        Create a scoped MemoryClient.

        Args:
            base_url:   Root URL of the memU service, e.g. "http://memu-server:18791".
            project_id: Identifier for the project — used as the memU user_id to
                        ensure per-project isolation.  Required; no default.
            agent_type: Which agent tier is issuing requests.  Required; no default.
        """
        self.base_url: str = base_url.rstrip("/")
        self.project_id: str = project_id
        self.agent_type: AgentType = agent_type
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Async context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "MemoryClient":
        self._client = httpx.AsyncClient(base_url=self.base_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_client(self) -> httpx.AsyncClient:
        """Return the active httpx client, creating an ad-hoc one if needed."""
        if self._client is None:
            # Allow use outside a context manager (caller is responsible for cleanup)
            self._client = httpx.AsyncClient(base_url=self.base_url)
        return self._client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def health(self) -> bool:
        """
        Check whether the memU service is reachable and initialised.

        Returns:
            True  — service returned 200 with memu_initialized: true
            False — service unreachable, timed out, or returned an error
        """
        client = self._ensure_client()
        try:
            response = await client.get("/health", timeout=3.0)
            response.raise_for_status()
            data = response.json()
            return bool(data.get("memu_initialized", False))
        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
            logger.warning(
                "memU health check failed",
                extra={"project_id": self.project_id, "error": str(exc)},
            )
            return False

    async def memorize(
        self,
        content: str,
        category: Optional[str] = None,
    ) -> Optional[MemorizeResult]:
        """
        Store a memory entry scoped to this client's project and agent.

        The project_id and agent_type are embedded in the request payload
        automatically — callers cannot omit or override them.

        Args:
            content:  The text to memorize (stored as resource_url per memU API).
            category: Optional category label sent at the top level of the POST
                      payload. FastAPI validates it against CategoryValue; the
                      router then injects it into the memu-py user dict for storage.
                      Pass None (default) to omit the field entirely.

        Returns:
            MemorizeResult(accepted=True, ...) on HTTP 202
            None if the service is unreachable or returns an error
        """
        client = self._ensure_client()
        payload = {
            "resource_url": content,
            "modality": "conversation",
            "user": {
                "user_id": self.project_id,
                "agent_type": self.agent_type.value,
            },
        }
        if category is not None:
            payload["category"] = category
        try:
            response = await client.post(
                "/memorize",
                json=payload,
                timeout=TIMEOUT_MEMORIZE,
            )
            response.raise_for_status()
            return MemorizeResult(accepted=True, message="accepted")
        except Exception as exc:
            logger.warning(
                "memU memorize failed",
                extra={
                    "project_id": self.project_id,
                    "agent_type": self.agent_type.value,
                    "error": str(exc),
                },
            )
            return None

    async def retrieve(self, query: str) -> List[dict]:
        """
        Retrieve memories scoped to this client's project.

        The where clause always filters by project_id (mapped to memU user_id),
        making cross-project retrieval structurally impossible.

        Args:
            query: Natural-language query for semantic memory retrieval.

        Returns:
            A list of memory dicts on success, [] on any failure.
        """
        client = self._ensure_client()
        payload = {
            "queries": [{"role": "user", "content": query}],
            "where": {"user_id": self.project_id},
        }
        try:
            response = await client.post(
                "/retrieve",
                json=payload,
                timeout=TIMEOUT_RETRIEVE,
            )
            response.raise_for_status()
            data = response.json()
            # Phase 26 /retrieve returns memu.retrieve() result directly.
            # Shape can be a list or a dict with an "items" key.
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "items" in data:
                return data["items"]
            return []
        except Exception as exc:
            logger.warning(
                "memU retrieve failed",
                extra={"project_id": self.project_id, "error": str(exc)},
            )
            return []
