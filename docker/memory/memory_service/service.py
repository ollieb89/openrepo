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
    """Initialize MemoryService with postgres backend and LLM profiles.

    The MemoryService constructor is synchronous. Individual methods
    (memorize, retrieve, list_memory_items, delete_memory_item) are async.
    
    Uses OpenRouter for chat/LLM (free models) and OpenAI for embeddings.
    If OpenAI key is not provided, embedding operations will fail gracefully.
    """
    llm_profiles = {
        "default": {
            "api_key": settings.OPENROUTER_API_KEY,
            "base_url": settings.OPENROUTER_BASE_URL,
            "chat_model": settings.OPENROUTER_CHAT_MODEL,
        },
    }
    
    # Only add embedding profile if OpenAI key is provided
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"):
        llm_profiles["embedding"] = {
            "api_key": settings.OPENAI_API_KEY,
            "embed_model": settings.OPENAI_EMBED_MODEL,
        }
        logger.info("Embeddings configured with OpenAI")
    else:
        logger.warning("OPENAI_API_KEY not configured - embeddings disabled. "
                      "New memories will be stored without embeddings. "
                      "Conflict detection requires manual embedding insertion.")
    
    service = MemoryService(
        llm_profiles=llm_profiles,
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
    logger.info("MemoryService initialized (OpenRouter for chat)")
    return service


# ---------------------------------------------------------------------------
# Health scan orchestration
# ---------------------------------------------------------------------------


async def _fetch_embeddings_direct(memory_ids: list[str], dsn: str) -> dict[str, list[float]]:
    """Fetch embeddings directly from PostgreSQL since list_memory_items excludes them.
    
    Returns a dict mapping memory_id -> embedding vector.
    """
    if not memory_ids:
        return {}
    
    import asyncio
    import psycopg
    
    try:
        # Use a thread pool to run the sync psycopg query
        def _query():
            embeddings = {}
            # Parse DSN to extract connection parameters
            # DSN format: postgresql+psycopg://user:pass@host:port/db
            conn_str = dsn.replace("postgresql+psycopg://", "postgresql://")
            with psycopg.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    placeholders = ','.join(['%s'] * len(memory_ids))
                    cur.execute(
                        f"SELECT id, embedding::text FROM memory_items WHERE id IN ({placeholders})",
                        memory_ids
                    )
                    for row in cur.fetchall():
                        mid, emb_str = row
                        if emb_str:
                            # Parse vector string like "[0.1,0.2,...]" to list of floats
                            emb_str = emb_str.strip('[]')
                            if emb_str:
                                embeddings[mid] = [float(x) for x in emb_str.split(',')]
            return embeddings
        
        # Run in thread pool to not block
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _query)
    except Exception as e:
        logger.warning(f"Failed to fetch embeddings: {e}")
        return {}


async def run_health_scan(
    memu: MemoryService,
    app: Any,
    body: HealthScanRequest,
    dsn: str | None = None,
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
    
    # Fetch embeddings separately since list_memory_items excludes them
    memory_ids = [item.get("id") for item in items if item.get("id")]
    embeddings_map = await _fetch_embeddings_direct(memory_ids, dsn) if dsn else {}
    
    # Attach embeddings to items for conflict detection
    for item in items:
        mid = item.get("id")
        if mid and mid in embeddings_map:
            item["embedding"] = embeddings_map[mid]

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
