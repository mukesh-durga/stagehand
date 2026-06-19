"""Tests for configuration loading."""

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
    assert settings.database_url == "postgresql+psycopg2://u:p@h:5432/d"


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()
