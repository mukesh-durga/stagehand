"""Tests for authentication (Milestone 20)."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models.user import User


def _creds(email: str | None = None) -> dict[str, str]:
    return {
        "name": "Ada Lovelace",
        "email": email or f"user-{uuid.uuid4().hex[:8]}@example.com",
        "password": "supersecret1",
    }


def test_signup_creates_user_and_returns_token(client: TestClient, db_session) -> None:
    body = _creds()
    resp = client.post("/auth/signup", json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == body["email"]
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Real row exists in Postgres.
    row = db_session.scalar(select(User).where(User.email == body["email"]))
    assert row is not None
    assert row.name == "Ada Lovelace"


def test_password_is_hashed_not_plaintext(client: TestClient, db_session) -> None:
    body = _creds()
    client.post("/auth/signup", json=body)
    row = db_session.scalar(select(User).where(User.email == body["email"]))
    assert row is not None
    assert row.password_hash != body["password"]
    assert row.password_hash.startswith("$2")  # bcrypt hash prefix


def test_duplicate_email_rejected(client: TestClient) -> None:
    body = _creds()
    assert client.post("/auth/signup", json=body).status_code == 201
    dup = client.post("/auth/signup", json={**_creds(), "email": body["email"]})
    assert dup.status_code == 409


def test_signup_rejects_short_password(client: TestClient) -> None:
    resp = client.post("/auth/signup", json={**_creds(), "password": "short"})
    assert resp.status_code == 422


def test_signup_rejects_invalid_email(client: TestClient) -> None:
    resp = client.post("/auth/signup", json={**_creds(), "email": "not-an-email"})
    assert resp.status_code == 422


def test_signin_succeeds_with_correct_password(client: TestClient) -> None:
    body = _creds()
    client.post("/auth/signup", json=body)
    resp = client.post("/auth/signin", json={"email": body["email"], "password": body["password"]})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_signin_fails_with_wrong_password(client: TestClient) -> None:
    body = _creds()
    client.post("/auth/signup", json=body)
    resp = client.post("/auth/signin", json={"email": body["email"], "password": "wrongpassword"})
    assert resp.status_code == 401


def test_signin_fails_with_unknown_email(client: TestClient) -> None:
    resp = client.post(
        "/auth/signin", json={"email": "nobody@example.com", "password": "supersecret1"}
    )
    assert resp.status_code == 401


def test_email_is_normalized_lowercase(client: TestClient) -> None:
    body = _creds(email=f"Mixed-{uuid.uuid4().hex[:6]}@Example.COM")
    client.post("/auth/signup", json=body)
    # Sign in with a different case must still match.
    resp = client.post(
        "/auth/signin", json={"email": body["email"].upper(), "password": body["password"]}
    )
    assert resp.status_code == 200


def test_me_requires_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_invalid_token(client: TestClient) -> None:
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.valid.token"})
    assert resp.status_code == 401


def test_me_returns_current_user_with_valid_token(client: TestClient) -> None:
    body = _creds()
    token = client.post("/auth/signup", json=body).json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == body["email"]
    assert "password_hash" not in data
