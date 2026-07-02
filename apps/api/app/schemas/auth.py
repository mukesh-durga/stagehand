"""Pydantic schemas for authentication."""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Pragmatic email check — avoids adding the email-validator dependency while
# still rejecting obviously invalid addresses. Emails are normalized to lowercase.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(value: str) -> str:
    value = (value or "").strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("Invalid email address")
    return value


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _normalize_email(v)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        return v


class UserLogin(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _normalize_email(v)


class UserRead(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
