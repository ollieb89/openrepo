from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ..logging import get_logger
from ..models import HealthScanRequest, MemoryUpdateRequest
from ..service import run_health_scan

router = APIRouter()
logger = get_logger("router.memories")


@router.get("/memories")
async def list_memories(
    request: Request,
    user_id: Optional[str] = Query(default=None),
):
    """GET /memories — returns a list of all memory items, optionally filtered by user_id."""
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Memory service not initialized"},
        )

    try:
        where = {"user_id": user_id} if user_id else None
        result = await memu.list_memory_items(where=where)
        return result
    except Exception as e:
        logger.error(f"List memories failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"List error: {str(e)}"},
        )


@router.post("/memories/health-scan")
async def health_scan(request: Request, body: HealthScanRequest):
    """POST /memories/health-scan — run a health scan for the given user_id scope.

    Detects stale memories (old + not recently retrieved) and conflicting memories
    (high cosine similarity pairs). Returns a HealthScanResult with scored flags.
    """
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Memory service not initialized"},
        )

    try:
        logger.info(f"Health scan requested: user_id={body.user_id}")
        result = await run_health_scan(memu, request.app, body)
        logger.info(
            f"Health scan complete: stale={result.totals['stale']}, "
            f"conflict={result.totals['conflict']}"
        )
        return result
    except Exception as e:
        logger.error(f"Health scan failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Health scan error: {str(e)}"},
        )


@router.get("/memories/health-flags")
async def get_health_flags(request: Request):
    """GET /memories/health-flags — retrieve cached health flags from the last scan.

    Returns an empty dict if no scan has been run yet.
    """
    flags = getattr(request.app.state, "health_flags", {})
    return flags


@router.put("/memories/{memory_id}")
async def update_memory(memory_id: str, request: Request, body: MemoryUpdateRequest):
    """PUT /memories/{memory_id} — updates content of an existing memory item.

    Delegates to MemoryService.update_memory_item() which handles re-embedding
    and category summary patching. Returns 404 if the item is not found.
    """
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Memory service not initialized"},
        )

    try:
        result = await memu.update_memory_item(
            memory_id=memory_id,
            memory_content=body.content,
        )
        return result
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"detail": str(e)},
        )
    except Exception as e:
        logger.error(f"Update memory {memory_id} failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Update error: {str(e)}"},
        )


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, request: Request):
    """DELETE /memories/{memory_id} — removes a single memory item by ID."""
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Memory service not initialized"},
        )

    try:
        await memu.delete_memory_item(memory_id=memory_id)
        return {"status": "deleted", "memory_id": memory_id}
    except Exception as e:
        logger.error(f"Delete memory {memory_id} failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Delete error: {str(e)}"},
        )
