from fastapi import APIRouter, Request

from ..models import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """GET /health — returns service status and memu initialization state."""
    memu = getattr(request.app.state, "memu", None)
    return HealthResponse(
        status="ok",
        service="openclaw-memory",
        memu_initialized=memu is not None,
    )
