"""Database setup for the worker (connects to the same Postgres as the API)."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from worker.config import get_settings

_settings = get_settings()

engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


@contextmanager
def session_scope(
    factory: Callable[[], Session] = SessionLocal,
) -> Iterator[Session]:
    """Yield a session, committing on success and rolling back on error."""
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
