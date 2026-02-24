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
    logger.info("Initializing MemUService...")
    try:
        app.state.memu = await init_service(settings)
        logger.info("MemUService initialized successfully")
    except TypeError:
        # MemUService constructor is synchronous — call without await
        try:
            settings2 = Settings()
            from memu import MemUService
            app.state.memu = MemUService(
                llm_profiles={
                    "default": {
                        "api_key": settings2.OPENAI_API_KEY,
                        "chat_model": settings2.OPENAI_CHAT_MODEL,
                    },
                    "embedding": {
                        "api_key": settings2.OPENAI_API_KEY,
                        "embed_model": settings2.OPENAI_EMBED_MODEL,
                    },
                },
                database_config={
                    "metadata_store": {
                        "provider": "postgres",
                        "ddl_mode": "create",
                        "dsn": settings2.dsn,
                    },
                    "vector_index": {
                        "provider": "pgvector",
                        "dsn": settings2.dsn,
                    },
                },
                memorize_config={
                    "llm_temperature": 0.0,
                },
            )
            logger.info("MemUService initialized successfully (sync constructor)")
        except Exception as inner_e:
            logger.error(f"Failed to initialize MemUService (sync): {inner_e}")
            app.state.memu = None
    except Exception as e:
        logger.error(f"Failed to initialize MemUService: {e}")
        app.state.memu = None

    yield


app = FastAPI(title="OpenClaw Memory Service", lifespan=lifespan)
app.include_router(health.router)
app.include_router(memorize.router)
app.include_router(retrieve.router)
app.include_router(memories.router)
