try:
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

# Support both package import (relative) and direct sys.path import (used in tests)
try:
    from ..logging import get_logger
    from ..models import RetrieveRequest
except ImportError:
    # Fallback for test environments where docker/memory/memory_service is on sys.path
    # but the package is not installed (no fastapi, no relative imports)
    from logging import getLogger as _getLogger

    def get_logger(name: str):  # type: ignore[misc]
        return _getLogger(f"memory.{name}")

    # RetrieveRequest only needed at runtime (FastAPI endpoint body parsing);
    # _filter_after (the testable pure function) has no pydantic dependency.
    try:
        from models import RetrieveRequest  # type: ignore[import]
    except ImportError:
        RetrieveRequest = None  # type: ignore[assignment,misc]

logger = get_logger("router.retrieve")

if _FASTAPI_AVAILABLE:
    router = APIRouter()


def _filter_after(items: list, created_after: str) -> list:
    """Return only items whose created_at is strictly after `created_after`.

    Tolerates missing or unparseable created_at — those items pass through
    (conservative: better to return a stale item than lose a new one).

    Args:
        items:         List of memory dicts from memu.retrieve().
        created_after: ISO timestamp string used as the exclusive lower bound.

    Returns:
        Filtered list of items strictly newer than created_after. Items with
        None/missing created_at are always included (conservative pass-through).
    """
    try:
        from datetime import datetime, timezone
        cutoff = datetime.fromisoformat(created_after.rstrip("Z"))
        # Ensure cutoff is timezone-naive for consistent comparison with item_dt
        if cutoff.tzinfo is not None:
            cutoff = cutoff.replace(tzinfo=None)
    except (ValueError, AttributeError):
        logger.warning(
            f"Unparseable created_after value: {created_after!r} — skipping filter"
        )
        return items

    filtered = []
    for item in items:
        ts = item.get("created_at")
        if ts is None:
            logger.debug(
                "Memory item missing created_at — passing through in cursor filter"
            )
            filtered.append(item)  # pass through — conservative
            continue
        try:
            from datetime import datetime, timezone
            if isinstance(ts, (int, float)):
                item_dt = datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None)  # naive UTC
            else:
                item_dt = datetime.fromisoformat(str(ts).rstrip("Z"))
                # Normalize timezone-aware datetimes to naive UTC for comparison
                if item_dt.tzinfo is not None:
                    item_dt = item_dt.replace(tzinfo=None)
            if item_dt > cutoff:
                filtered.append(item)
        except (ValueError, TypeError, OSError):
            filtered.append(item)  # pass through — conservative
    return filtered


if _FASTAPI_AVAILABLE:
    @router.post("/retrieve")
    async def retrieve(payload: RetrieveRequest, request: Request):
        """POST /retrieve — synchronously retrieves memory items matching the queries."""
        memu = getattr(request.app.state, "memu", None)
        if memu is None:
            return JSONResponse(
                status_code=503,
                content={"detail": "Memory service not initialized"},
            )

        try:
            result = await memu.retrieve(
                queries=payload.queries,
                where=payload.where,
            )

            # Apply cursor filter if provided (PERF-07)
            if payload.created_after:
                if isinstance(result, list):
                    result = _filter_after(result, payload.created_after)
                elif isinstance(result, dict) and "items" in result:
                    result["items"] = _filter_after(result["items"], payload.created_after)

            return result
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Retrieval error: {str(e)}"},
            )
