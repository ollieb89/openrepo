import os

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from ..logging import get_logger
from ..models import MemorizeAccepted, MemorizeRequest

router = APIRouter()
logger = get_logger("router.memorize")


def _get_conflict_threshold() -> float:
    """Read conflict threshold from openclaw.json memory.conflict_threshold.

    Falls back to 0.85 default (MEMORY_CONFLICT_THRESHOLD equivalent, QUAL-07).
    Cannot import openclaw.config — this runs inside the Docker memory container.
    """
    _DEFAULT = 0.85
    try:
        import json
        from pathlib import Path
        openclaw_root = os.environ.get("OPENCLAW_ROOT", str(Path.home() / ".openclaw"))
        config_path = Path(openclaw_root) / "openclaw.json"
        with open(config_path) as f:
            cfg = json.load(f)
        threshold = cfg.get("memory", {}).get("conflict_threshold")
        if threshold is not None:
            return float(threshold)
    except Exception:
        pass
    return _DEFAULT


async def _run_memorize(service, request: MemorizeRequest) -> None:
    """Background task: checks for conflicts, then calls service.memorize() if clear."""
    try:
        # --- Conflict pre-check (QUAL-07) ---
        threshold = _get_conflict_threshold()
        user_dict = dict(request.user) if request.user else {}
        if request.category is not None:
            user_dict["category"] = request.category

        # Retrieve existing memories to check cosine similarity
        try:
            existing = await service.retrieve(
                query=request.resource_url,
                user=user_dict if user_dict else None,
                limit=5,
            )
            items = existing.get("items", []) if isinstance(existing, dict) else []
            for item in items:
                score = item.get("score", 0.0) if isinstance(item, dict) else 0.0
                if score >= threshold:
                    logger.warning(
                        "Conflict detected — skipping memorize (existing memory kept)",
                        extra={
                            "resource_url": request.resource_url,
                            "conflict_score": score,
                            "threshold": threshold,
                            "conflict_memory_id": item.get("id", "unknown") if isinstance(item, dict) else "unknown",
                        },
                    )
                    return
        except Exception as conflict_err:
            # Fail-open: if conflict check fails, proceed with memorize
            logger.warning(f"Conflict pre-check failed, proceeding with memorize: {conflict_err}")

        # --- Memorize ---
        await service.memorize(
            resource_url=request.resource_url,
            modality=request.modality,
            user=user_dict if user_dict else None,
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
