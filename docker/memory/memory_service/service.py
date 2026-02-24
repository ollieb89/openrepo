from memu import MemUService

from .config import Settings
from .logging import get_logger

logger = get_logger("service")


async def init_service(settings: Settings) -> MemUService:
    """Initialize MemUService with postgres backend and OpenAI LLM profiles."""
    service = MemUService(
        llm_profiles={
            "default": {
                "api_key": settings.OPENAI_API_KEY,
                "chat_model": settings.OPENAI_CHAT_MODEL,
            },
            "embedding": {
                "api_key": settings.OPENAI_API_KEY,
                "embed_model": settings.OPENAI_EMBED_MODEL,
            },
        },
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
        memorize_config={
            "llm_temperature": 0.0,
        },
    )
    logger.info("MemUService instance created")
    return service
