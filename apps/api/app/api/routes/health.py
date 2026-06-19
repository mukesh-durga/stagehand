"""Health check endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.db.postgres import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check. Always returns ok if the API process is up."""
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
