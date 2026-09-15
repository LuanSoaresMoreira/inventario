from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from inventario_backend.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Cria um pool somente quando o banco for usado pela primeira vez."""

    return create_engine(
        str(get_settings().database_url),
        pool_pre_ping=True,
    )


def get_db() -> Generator[Session, None, None]:
    """Fornece uma sessão transacional para dependências do FastAPI."""

    with Session(get_engine()) as session:
        yield session


def check_database() -> None:
    """Executa uma consulta sem efeitos para verificar a conexão."""

    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))

