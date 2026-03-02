from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_PASSWORD: str
    DB_HOST: str = "openclaw-memory-db"
    DB_PORT: int = 5432
    DB_NAME: str = "openclaw_memory"
    DB_USER: str = "claw_admin"

    # OpenRouter configuration (for chat/LLM)
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Free/Open models on OpenRouter
    OPENROUTER_CHAT_MODEL: str = "openrouter/meta-llama/llama-3.1-70b-instruct:free"
    
    # OpenAI for embeddings (OpenRouter doesn't provide embeddings)
    # Embeddings are very cheap ($0.02 per 1M tokens) or use OpenAI free tier
    OPENAI_API_KEY: str = ""  # Optional - only needed for creating new embeddings
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"

    SERVICE_PORT: int = 18791

    @property
    def dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
