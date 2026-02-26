from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel

CategoryValue = Literal["review_decision", "task_outcome"]


class MemorizeRequest(BaseModel):
    resource_url: str
    modality: str = "conversation"
    user: dict[str, Any] | None = None
    category: Optional[CategoryValue] = None


class RetrieveRequest(BaseModel):
    queries: list[dict[str, Any]]
    where: dict[str, Any] | None = None
    created_after: Optional[str] = None  # ISO timestamp cursor for delta fetch (PERF-07)


class MemorizeAccepted(BaseModel):
    status: str = "accepted"
    message: str = "Memorization queued"


class HealthResponse(BaseModel):
    status: str
    service: str
    memu_initialized: bool


# ---------------------------------------------------------------------------
# Health scan models
# ---------------------------------------------------------------------------


class HealthFlag(BaseModel):
    memory_id: str
    flag_type: Literal["stale", "conflict"]
    score: float  # age_score (days/threshold) for stale; cosine similarity for conflict
    recommendation: Literal["archive", "review", "merge"]
    conflict_with: Optional[str] = None  # memory_id of conflicting item (conflict flags only)


class HealthScanRequest(BaseModel):
    user_id: str  # Required — prevents cross-project scope leak (Pitfall 6)
    age_threshold_days: int = 30
    retrieval_window_days: int = 14
    similarity_min: float = 0.75
    similarity_max: float = 0.97


class HealthScanResult(BaseModel):
    flags: list[HealthFlag]
    scanned_at: str  # ISO timestamp
    totals: dict  # {"stale": N, "conflict": N, "total": N}


class MemoryUpdateRequest(BaseModel):
    content: str  # Required (non-optional) — prevents Pitfall 1 empty-body ValueError
