from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_PASSWORD: str
    DB_HOST: str = "openclaw-memory-db"
    DB_PORT: int = 5432
    DB_NAME: str = "openclaw_memory"
    DB_USER: str = "claw_admin"

    OPENAI_API_KEY: str
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
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
