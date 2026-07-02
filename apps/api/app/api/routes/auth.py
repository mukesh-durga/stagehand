"""Authentication endpoints: signup, signin, and current user."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.postgres import get_db
from app.schemas.auth import TokenResponse, UserCreate, UserLogin, UserRead
from app.services import auth_service
from app.services.exceptions import EmailAlreadyExistsError, InvalidCredentialsError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return auth_service.signup(db, payload)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )


@router.post("/signin", response_model=TokenResponse)
def signin(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return auth_service.signin(db, payload)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return auth_service.current_user_read(current_user)
