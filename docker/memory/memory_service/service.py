from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pendulum
from memu.app import MemoryService

from .config import Settings
from .logging import get_logger
from .models import HealthFlag, HealthScanRequest, HealthScanResult
from .scan_engine import _check_staleness, _find_conflicts

logger = get_logger("service")


def init_service(settings: Settings) -> MemoryService:
    """Initialize MemoryService with postgres backend and OpenAI LLM profiles.

    The MemoryService constructor is synchronous. Individual methods
    (memorize, retrieve, list_memory_items, delete_memory_item) are async.
    """
    service = MemoryService(
        llm_profiles={
            "default": {
                "api_key": settings.OPENAI_API_KEY,
                "chat_model": settings.OPENAI_CHAT_MODEL,
            },
            "embedding": {
                "api_key": settings.OPENAI_API_KEY,
                "embed_model": settings.OPENAI_EMBED_MODEL,
            },
        },
        database_config={
            "metadata_store": {
                "provider": "postgres",
                "ddl_mode": "create",
                "dsn": settings.dsn,
            },
            "vector_index": {
                "provider": "pgvector",
                "dsn": settings.dsn,
            },
        },
    )
    logger.info("MemoryService instance created")
    return service


# ---------------------------------------------------------------------------
# Health scan orchestration
# ---------------------------------------------------------------------------


async def run_health_scan(
    memu: MemoryService,
    app: Any,
    body: HealthScanRequest,
) -> HealthScanResult:
    """Run a full health scan for the given user_id scope.

    Detects:
        1. Stale memories — old items that haven't been retrieved recently.
        2. Conflicting memories — pairs of items with high cosine similarity
           (possible duplicates or contradictory facts about the same topic).

    Results are stored ephemerally in app.state.health_flags (keyed by memory_id)
    so the GET /memories/health-flags endpoint can serve cached results.

    Returns:
        HealthScanResult with flags list, ISO scanned_at timestamp, and totals.
    """
    now = datetime.now(timezone.utc)

    # Fetch all items for this user (project) scope
    list_result = await memu.list_memory_items(where={"user_id": body.user_id})
    items = list_result.get("items", [])

    logger.info(f"Health scan started: user_id={body.user_id}, item_count={len(items)}")

    # --- Staleness detection ---
    stale_flags: list[HealthFlag] = []
    for raw_item in items:
        # list_memory_items returns serialised dicts; reconstruct a simple namespace
        # for attribute access used by _check_staleness.
        item_obj = _ItemProxy(raw_item)
        age_score = _check_staleness(
            item_obj,
            age_threshold_days=body.age_threshold_days,
            retrieval_window_days=body.retrieval_window_days,
            now=now,
        )
        if age_score is not None:
            recommendation = "archive" if age_score > 2.0 else "review"
            stale_flags.append(
                HealthFlag(
                    memory_id=item_obj.id,
                    flag_type="stale",
                    score=round(age_score, 4),
                    recommendation=recommendation,
                )
            )

    # --- Conflict detection ---
    # Reconstruct item proxies with embeddings for cosine_topk
    item_proxies = [_ItemProxy(raw) for raw in items]
    conflict_pairs = _find_conflicts(
        item_proxies,
        similarity_min=body.similarity_min,
        similarity_max=body.similarity_max,
    )

    conflict_flags: list[HealthFlag] = []
    for id_a, id_b, similarity in conflict_pairs:
        recommendation = "merge" if similarity > 0.90 else "review"
        conflict_flags.append(
            HealthFlag(
                memory_id=id_a,
                flag_type="conflict",
                score=round(similarity, 4),
                recommendation=recommendation,
                conflict_with=id_b,
            )
        )

    all_flags = stale_flags + conflict_flags

    # Store flags ephemerally in app.state for GET /memories/health-flags
    if app is not None:
        if not hasattr(app.state, "health_flags"):
            app.state.health_flags = {}
        app.state.health_flags = {flag.memory_id: flag.model_dump() for flag in all_flags}

    totals = {
        "stale": len(stale_flags),
        "conflict": len(conflict_flags),
        "total": len(all_flags),
    }

    logger.info(
        f"Health scan complete: stale={totals['stale']}, conflict={totals['conflict']}, "
        f"total={totals['total']}"
    )

    return HealthScanResult(
        flags=all_flags,
        scanned_at=now.isoformat(),
        totals=totals,
    )


class _ItemProxy:
    """Lightweight proxy to provide attribute access over a raw dict from list_memory_items.

    list_memory_items() returns serialised dicts (after model_dump), not MemoryItem objects.
    This proxy normalises field access so the scan helpers can use item.id, item.created_at,
    item.extra, and item.embedding without caring whether the source was a dict or model.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @property
    def id(self) -> str:
        return self._raw["id"]

    @property
    def created_at(self) -> datetime:
        value = self._raw["created_at"]
        if isinstance(value, datetime):
            return value
        # ISO string from serialisation
        return pendulum.parse(str(value))

    @property
    def extra(self) -> dict[str, Any]:
        return self._raw.get("extra") or {}

    @property
    def embedding(self) -> list[float] | None:
        return self._raw.get("embedding")
