"""Application configuration loaded from environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Per-deployment-mode defaults for the optional mode flags. An explicitly-set env
# var always wins; only unset (None) flags fall back to these.
_MODE_DEFAULTS = {
    "local": {
        "clickhouse_enabled": True,
        "worker_enabled": True,
        "hosted_demo_execution": False,
        "trace_storage": "clickhouse",
    },
    "hosted_demo": {
        "clickhouse_enabled": False,
        "worker_enabled": False,
        "hosted_demo_execution": True,
        "trace_storage": "postgres",
    },
}

# Root .env lives at the repo root: apps/api/app/config.py -> parents[3] == repo root.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"


def _normalize_database_url(url: str) -> str:
    """Normalize a managed-provider Postgres URL to the psycopg2 driver scheme.

    Neon/Supabase/Render emit `postgres://` or `postgresql://`; SQLAlchemy needs
    `postgresql+psycopg2://`. Returns the empty string unchanged.
    """
    if not url:
        return ""
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://") :]
    return url


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
    # Comma-separated list of additional allowed CORS origins (e.g. the Vercel URL).
    backend_cors_origins: str = ""

    # Deployment mode — "local" (full stack) or "hosted_demo" (free-tier, no
    # ClickHouse / no separate worker). The flags below default from this mode
    # when left unset, but any explicitly-set env var always wins.
    deployment_mode: str = "local"  # "local" | "hosted_demo"
    # Sentinels (None) so an explicit env value overrides the mode-based default.
    clickhouse_enabled: bool | None = None
    worker_enabled: bool | None = None
    hosted_demo_execution: bool | None = None
    trace_storage: str | None = None  # "clickhouse" | "postgres"
    # AI provider selection. "mock" forces the deterministic provider (hosted demo).
    ai_provider: str = "mock"

    # PostgreSQL
    # In production set DATABASE_URL (Neon/Supabase/Render). When empty the URL is
    # built from the POSTGRES_* components below (used for local Docker Compose).
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

    # AI providers / models (optional; mock provider is used when keys are absent).
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cheap_model_name: str = ""
    strong_model_name: str = ""
    default_eval_model_name: str = ""

    # Run limits / defaults
    default_max_cost_usd: float = 0.50
    default_max_steps: int = 25
    default_max_runtime_seconds: int = 120

    # Billing (test mode only — never real charges)
    billing_mode: str = "mock"  # "mock" | "stripe_test"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    @model_validator(mode="after")
    def _apply_mode_defaults(self) -> "Settings":
        """Fill unset deployment flags from DEPLOYMENT_MODE defaults.

        Explicit env vars take precedence; only None flags are filled. Unknown
        modes fall back to ``local`` defaults so the app never starts misconfigured.
        """
        defaults = _MODE_DEFAULTS.get(self.deployment_mode, _MODE_DEFAULTS["local"])
        if self.clickhouse_enabled is None:
            self.clickhouse_enabled = defaults["clickhouse_enabled"]
        if self.worker_enabled is None:
            self.worker_enabled = defaults["worker_enabled"]
        if self.hosted_demo_execution is None:
            self.hosted_demo_execution = defaults["hosted_demo_execution"]
        if self.trace_storage is None:
            self.trace_storage = defaults["trace_storage"]
        return self

    @property
    def use_postgres_traces(self) -> bool:
        """True when traces should be read/written via Postgres rather than ClickHouse."""
        return self.trace_storage == "postgres" or not self.clickhouse_enabled

    @property
    def effective_database_url(self) -> str:
        """SQLAlchemy connection URL for PostgreSQL (sync, psycopg2).

        Prefers an explicit DATABASE_URL (production) and normalizes the
        `postgres://` / `postgresql://` schemes that managed providers emit to the
        psycopg2 driver scheme. Falls back to the POSTGRES_* components locally.
        """
        return _normalize_database_url(self.database_url) or (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins: local dev URLs + frontend URL + configured extras."""
        origins = [
            "http://localhost:5173",
            "http://localhost:5174",
            self.frontend_url,
        ]
        origins.extend(
            o.strip() for o in self.backend_cors_origins.split(",") if o.strip()
        )
        # De-duplicate while preserving order.
        seen: set[str] = set()
        return [o for o in origins if o and not (o in seen or seen.add(o))]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
