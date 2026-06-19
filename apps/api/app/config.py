"""Application configuration loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Root .env lives at the repo root: apps/api/app/config.py -> parents[3] == repo root.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Typed application settings.

    Values are read from the repo-root .env (falling back to a local .env in the
    api directory). Unrelated keys in the shared .env are ignored.
    """

    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    api_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "stagehand"
    postgres_user: str = "stagehand"
    postgres_password: str = "stagehand"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ClickHouse
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "stagehand"

    # Run limits / defaults
    default_max_cost_usd: float = 0.50
    default_max_steps: int = 25
    default_max_runtime_seconds: int = 120

    @property
    def database_url(self) -> str:
        """SQLAlchemy connection URL for PostgreSQL (sync, psycopg2)."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
