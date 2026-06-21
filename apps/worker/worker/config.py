"""Worker configuration loaded from the repo-root .env (shared with the API)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/worker/worker/config.py -> parents[3] == repo root.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # PostgreSQL (same database as the API)
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

    # AI providers / models (optional; mock provider is used when keys are absent)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cheap_model_name: str = ""
    strong_model_name: str = ""
    default_eval_model_name: str = ""

    # UCB adaptive routing
    ucb_exploration_weight: float = 1.0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
