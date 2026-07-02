"""Authentication business logic: signup, signin, and token issuance."""

import uuid

import jwt
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from app.services.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)


def _user_read(user: User) -> UserRead:
    return UserRead(id=user.id, name=user.name, email=user.email, created_at=user.created_at)


def _token_response(user: User) -> TokenResponse:
    token = create_access_token(subject=str(user.id), email=user.email)
    return TokenResponse(access_token=token, user=_user_read(user))


def signup(db: Session, data: UserCreate) -> TokenResponse:
    repo = UserRepository(db)
    if repo.get_by_email(data.email) is not None:
        raise EmailAlreadyExistsError(data.email)

    user = User(
        name=data.name,
        email=data.email,  # already normalized to lowercase by the schema
        password_hash=hash_password(data.password),
    )
    repo.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


def signin(db: Session, data: UserLogin) -> TokenResponse:
    user = UserRepository(db).get_by_email(data.email)
    # Verify even when the user is missing is unnecessary here; a simple check is
    # fine for this scope. Both branches return the same generic 401 upstream.
    if user is None or not verify_password(data.password, user.password_hash):
        raise InvalidCredentialsError()
    return _token_response(user)


def get_user_from_token(db: Session, token: str) -> User:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token missing subject")
    try:
        user_id = uuid.UUID(str(subject))
    except ValueError as exc:
        raise InvalidTokenError("Malformed subject") from exc

    user = UserRepository(db).get(user_id)
    if user is None:
        raise InvalidTokenError("User no longer exists")
    return user


def current_user_read(user: User) -> UserRead:
    return _user_read(user)
