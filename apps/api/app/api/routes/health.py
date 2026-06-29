"""Health check endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.db.clickhouse import get_clickhouse
from app.db.postgres import engine
from app.db.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check. Always returns ok if the API process is up.

    Use this as the Render/Railway/Fly health check path — it never touches a
    backing service, so a transient DB/Redis blip won't recycle the instance.
    """
    return {"status": "ok"}


@router.get("/health/db")
def health_db() -> dict[str, str]:
    """Readiness check for PostgreSQL connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001 - surface any connectivity failure
        return {"status": "error", "database": "unavailable", "detail": str(exc)}


@router.get("/health/redis")
def health_redis() -> dict[str, str]:
    """Readiness check for Redis connectivity (run queue + WS fanout)."""
    try:
        get_redis().ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as exc:  # noqa: BLE001 - surface any connectivity failure
        return {"status": "error", "redis": "unavailable", "detail": str(exc)}


@router.get("/health/clickhouse")
def health_clickhouse() -> dict[str, str]:
    """Readiness check for ClickHouse connectivity (trace analytics store)."""
    try:
        get_clickhouse().command("SELECT 1")
        return {"status": "ok", "clickhouse": "connected"}
    except Exception as exc:  # noqa: BLE001 - surface any connectivity failure
        return {"status": "error", "clickhouse": "unavailable", "detail": str(exc)}
