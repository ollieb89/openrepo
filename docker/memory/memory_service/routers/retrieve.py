from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..logging import get_logger
from ..models import RetrieveRequest

router = APIRouter()
logger = get_logger("router.retrieve")


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
        return result
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Retrieval error: {str(e)}"},
        )
