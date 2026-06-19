"""PostgreSQL connectivity test.

Skips automatically if the database is not reachable, so the suite still passes
in environments without Docker running.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.postgres import engine


def test_postgres_connection() -> None:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")
    assert result == 1
