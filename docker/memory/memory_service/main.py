from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .logging import get_logger
from .routers import health, memorize, memories, retrieve
from .service import init_service

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    logger.info("Initializing MemoryService...")
    try:
        # MemoryService.__init__ is synchronous
        app.state.memu = init_service(settings)
        logger.info("MemoryService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MemoryService: {e}")
        app.state.memu = None  # Health endpoint will report uninitialized

    yield


app = FastAPI(title="OpenClaw Memory Service", lifespan=lifespan)
app.include_router(health.router)
app.include_router(memorize.router)
app.include_router(retrieve.router)
app.include_router(memories.router)
