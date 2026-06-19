"""Shared pytest fixtures.

The ``client`` fixture wires the API to a single database connection wrapped in a
transaction that is rolled back after each test, so tests are isolated and leave
the database clean. Requires PostgreSQL to be running (see README).
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.postgres import engine, get_db
from app.main import app


@pytest.fixture
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    # create_savepoint lets service-level commits resolve to savepoints, keeping
    # the outer transaction open so it can be rolled back at teardown.
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
