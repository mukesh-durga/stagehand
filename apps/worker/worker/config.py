"""Worker configuration loaded from the repo-root .env (shared with the API)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/worker/worker/config.py -> parents[3] == repo root.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


def _normalize_database_url(url: str) -> str:
    """Normalize a managed-provider Postgres URL to the psycopg2 driver scheme."""
    if not url:
        return ""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # PostgreSQL (same database as the API)
    # In production set DATABASE_URL; locally it is built from the components below.
    database_url: str = ""
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
    # ClickHouse Cloud requires TLS (port 8443, secure=True). Local Docker uses 8123.
    clickhouse_secure: bool = False

    # Run limits / defaults
    default_max_cost_usd: float = 0.50
    default_max_steps: int = 25
    default_max_runtime_seconds: int = 120

    # AI providers / models (optional; mock provider is used when keys are absent)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cheap_model_name: str = ""
    strong_model_name: str = ""
    default_eval_model_name: str = ""

    # UCB adaptive routing
    ucb_exploration_weight: float = 1.0

    # Billing mode (the worker only reads this; the API owns billing endpoints).
    billing_mode: str = "mock"

    @property
    def effective_database_url(self) -> str:
        """Prefer DATABASE_URL (production); fall back to POSTGRES_* (local)."""
        return _normalize_database_url(self.database_url) or (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
