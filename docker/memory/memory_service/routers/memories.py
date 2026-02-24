from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ..logging import get_logger

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
