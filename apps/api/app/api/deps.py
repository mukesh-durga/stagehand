"""Shared FastAPI dependencies."""

from sqlalchemy.orm import Session

from fastapi import Depends

from app.db.postgres import get_db
from app.db.trace_store import TraceStore, make_trace_store


def get_trace_store(db: Session = Depends(get_db)) -> TraceStore:
    """Return the configured TraceStore (ClickHouse, or Postgres in hosted demo)."""
    return make_trace_store(db)
