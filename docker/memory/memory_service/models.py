from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MemorizeRequest(BaseModel):
    resource_url: str
    modality: str = "conversation"
    user: dict[str, Any] | None = None


class RetrieveRequest(BaseModel):
    queries: list[dict[str, Any]]
    where: dict[str, Any] | None = None


class MemorizeAccepted(BaseModel):
    status: str = "accepted"
    message: str = "Memorization queued"


class HealthResponse(BaseModel):
    status: str
    service: str
    memu_initialized: bool
