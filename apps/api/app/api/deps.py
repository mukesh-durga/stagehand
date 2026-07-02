"""Shared FastAPI dependencies."""

from sqlalchemy.orm import Session

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.models.user import User
from app.db.postgres import get_db
from app.db.trace_store import TraceStore, make_trace_store
from app.services import auth_service
from app.services.exceptions import InvalidTokenError

# auto_error=False so we can return a consistent 401 (not 403) when the header
# is missing, matching the rest of the auth surface.
_bearer = HTTPBearer(auto_error=False)


def get_trace_store(db: Session = Depends(get_db)) -> TraceStore:
    """Return the configured TraceStore (ClickHouse, or Postgres in hosted demo)."""
    return make_trace_store(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from a Bearer token, or raise 401."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return auth_service.get_user_from_token(db, credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc) or "Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
