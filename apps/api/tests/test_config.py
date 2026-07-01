"""Tests for configuration loading."""

import app.config as config_mod
from app.config import Settings, get_settings


def test_settings_have_defaults() -> None:
    settings = get_settings()
    assert settings.app_env
    assert settings.postgres_db
    assert isinstance(settings.postgres_port, int)


def test_database_url_is_well_formed() -> None:
    settings = Settings(
        postgres_user="u",
        postgres_password="p",
        postgres_host="h",
        postgres_port=5432,
        postgres_db="d",
    )
    assert settings.effective_database_url == "postgresql+psycopg2://u:p@h:5432/d"


def test_database_url_override_is_normalized() -> None:
    # Managed providers emit postgres:// or postgresql://; both map to psycopg2.
    assert (
        Settings(database_url="postgres://u:p@host:5432/db").effective_database_url
        == "postgresql+psycopg2://u:p@host:5432/db"
    )
    assert (
        Settings(database_url="postgresql://u:p@host:5432/db").effective_database_url
        == "postgresql+psycopg2://u:p@host:5432/db"
    )
    # An already-qualified URL is passed through unchanged.
    qualified = "postgresql+psycopg2://u:p@host:5432/db"
    assert Settings(database_url=qualified).effective_database_url == qualified


def test_cors_origins_includes_localhost_and_extras() -> None:
    settings = Settings(
        frontend_url="https://app.example.com",
        backend_cors_origins="https://a.example.com, https://b.example.com",
    )
    origins = settings.cors_origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:5174" in origins
    assert "https://app.example.com" in origins
    assert "https://a.example.com" in origins
    assert "https://b.example.com" in origins
    # No duplicates.
    assert len(origins) == len(set(origins))


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_candidate_env_files_safe_at_shallow_path(monkeypatch) -> None:
    """Building env-file candidates must not IndexError when packaged shallowly.

    In the Docker image the module lives at /app/app/config.py, so `parents[3]`
    (the monorepo repo root) does not exist. Previously this crashed at import.
    """
    # Shallow (Docker) layout and an even shallower path — neither may raise.
    for fake in ("/app/app/config.py", "/config.py"):
        monkeypatch.setattr(config_mod, "__file__", fake)
        result = config_mod._candidate_env_files()
        assert isinstance(result, tuple)
        # Settings must still construct with those env-file candidates.
        assert Settings(_env_file=result or None).app_env
