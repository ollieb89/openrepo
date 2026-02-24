from memu.app import MemoryService

from .config import Settings
from .logging import get_logger

logger = get_logger("service")


def init_service(settings: Settings) -> MemoryService:
    """Initialize MemoryService with postgres backend and OpenAI LLM profiles.

    The MemoryService constructor is synchronous. Individual methods
    (memorize, retrieve, list_memory_items, delete_memory_item) are async.
    """
    service = MemoryService(
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
    )
    logger.info("MemoryService instance created")
    return service
