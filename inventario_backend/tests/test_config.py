import pytest
from pydantic import ValidationError

from inventario_backend.config import Settings


def test_database_url_accepts_postgresql_psycopg() -> None:
    settings = Settings(
        database_url="postgresql+psycopg://app:password@localhost:5432/inventario"
    )

    assert settings.database_url.scheme == "postgresql+psycopg"


def test_database_url_rejects_non_postgresql_scheme() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///local.db")
