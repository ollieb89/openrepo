from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from ..logging import get_logger
from ..models import MemorizeAccepted, MemorizeRequest

router = APIRouter()
logger = get_logger("router.memorize")


async def _run_memorize(service, request: MemorizeRequest) -> None:
    """Background task: calls service.memorize() and logs any errors."""
    try:
        await service.memorize(
            resource_url=request.resource_url,
            modality=request.modality,
            user=request.user,
        )
        logger.info(f"Memorized: {request.resource_url}")
    except Exception as e:
        logger.error(f"Memorization failed for {request.resource_url}: {e}")


@router.post("/memorize", status_code=202, response_model=MemorizeAccepted)
async def memorize(
    payload: MemorizeRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> JSONResponse:
    """POST /memorize — queues memorization as background task, returns 202 Accepted."""
    memu = getattr(request.app.state, "memu", None)
    if memu is None:
        return JSONResponse(
            status_code=503,
            content={"detail": "Memory service not initialized"},
        )

    background_tasks.add_task(_run_memorize, memu, payload)
    return JSONResponse(
        status_code=202,
        content=MemorizeAccepted().model_dump(),
    )
