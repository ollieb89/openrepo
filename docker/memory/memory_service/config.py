from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_PASSWORD: str
    DB_HOST: str = "openclaw-memory-db"
    DB_PORT: int = 5432
    DB_NAME: str = "openclaw_memory"
    DB_USER: str = "claw_admin"

    # OpenRouter configuration (for chat/LLM + embeddings)
    OPENROUTER_API_KEY: str
    # Note: OpenRouter uses /api/v1 in endpoints, so base URL should not include it
    OPENROUTER_BASE_URL: str = "https://openrouter.ai"
    
    # Free/Open models on OpenRouter
    OPENROUTER_CHAT_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"
    # NVIDIA free embedding model on OpenRouter (768 dimensions)
    OPENROUTER_EMBED_MODEL: str = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    
    # Optional: OpenAI fallback for embeddings (if OpenRouter fails)
    OPENAI_API_KEY: str = ""
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
