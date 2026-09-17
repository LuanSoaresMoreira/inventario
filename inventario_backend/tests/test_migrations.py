from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from inventario_backend.config import get_settings
from inventario_backend.database import get_engine
from inventario_backend.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _postgres_bin() -> Path | None:
    configured = os.environ.get("POSTGRES_BIN")
    if configured:
        candidate = Path(configured)
        if (candidate / "initdb.exe").exists() or (candidate / "initdb").exists():
            return candidate

    initdb = shutil.which("initdb")
    if initdb:
        return Path(initdb).parent

    roots = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "PostgreSQL",
        Path("/usr/lib/postgresql"),
    ]
    candidates: list[Path] = []
    for root in roots:
        if root.is_dir():
            candidates.extend(path / "bin" for path in root.iterdir())

    executable = "initdb.exe" if os.name == "nt" else "initdb"
    return next(
        (
            path
            for path in sorted(candidates, reverse=True)
            if (path / executable).exists()
        ),
        None,
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def isolated_postgres(tmp_path: Path) -> Iterator[str]:
    binaries = _postgres_bin()
    if binaries is None:
        pytest.skip("PostgreSQL local não encontrado; defina POSTGRES_BIN")

    executable_suffix = ".exe" if os.name == "nt" else ""
    initdb = binaries / f"initdb{executable_suffix}"
    pg_ctl = binaries / f"pg_ctl{executable_suffix}"
    postgres = binaries / f"postgres{executable_suffix}"
    data_dir = tmp_path / "postgres-data"
    log_path = tmp_path / "postgres.log"
    port = _free_port()

    subprocess.run(
        [
            str(initdb),
            "-D",
            str(data_dir),
            "-U",
            "postgres",
            "--auth=trust",
            "--encoding=UTF8",
            "--no-locale",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    server_process: subprocess.Popen[str] | None = None
    log_file = None
    if os.name == "nt":
        # pg_ctl tenta criar um token restrito no Windows e pode falhar em runners
        # já isolados. Iniciar o postmaster diretamente preserva o mesmo cluster
        # descartável sem depender dessa API do sistema operacional.
        log_file = log_path.open("w", encoding="utf-8")
        server_process = subprocess.Popen(
            [
                str(postgres),
                "-D",
                str(data_dir),
                "-F",
                "-p",
                str(port),
                "-h",
                "127.0.0.1",
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        subprocess.run(
            [
                str(pg_ctl),
                "-D",
                str(data_dir),
                "-l",
                str(log_path),
                "-o",
                f"-F -p {port} -h 127.0.0.1",
                "-w",
                "start",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    database_url = f"postgresql+psycopg://postgres@127.0.0.1:{port}/postgres"
    for _ in range(100):
        if server_process is not None and server_process.poll() is not None:
            log_file.close()
            pytest.fail(f"PostgreSQL encerrou durante o start:\n{log_path.read_text()}")
        probe = create_engine(database_url)
        try:
            with probe.connect() as connection:
                connection.execute(text("SELECT 1"))
            break
        except DBAPIError:
            time.sleep(0.1)
        finally:
            probe.dispose()
    else:
        pytest.fail("PostgreSQL temporário não ficou pronto em 10 segundos")

    try:
        yield database_url
    finally:
        stopped = subprocess.run(
            [str(pg_ctl), "-D", str(data_dir), "-m", "fast", "-w", "stop"],
            check=False,
            capture_output=True,
            text=True,
        )
        if stopped.returncode != 0 and server_process is not None:
            server_process.terminate()
            server_process.wait(timeout=10)
        if log_file is not None:
            log_file.close()


def test_upgrade_append_only_and_rollback(
    isolated_postgres: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", isolated_postgres)
    get_settings.cache_clear()
    get_engine.cache_clear()
    alembic_config = Config(str(BACKEND_ROOT / "alembic.ini"))

    command.upgrade(alembic_config, "head")
    engine = create_engine(isolated_postgres)
    expected_tables = set(Base.metadata.tables)
    assert expected_tables <= set(inspect(engine).get_table_names())

    event_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events "
                "(id, entity_type, entity_id, action, reason) "
                "VALUES (:id, 'equipment', :entity_id, 'created', 'test')"
            ),
            {"id": event_id, "entity_id": entity_id},
        )

    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(
            text("UPDATE audit_events SET reason = 'changed' WHERE id = :id"),
            {"id": event_id},
        )
    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(
            text("DELETE FROM audit_events WHERE id = :id"),
            {"id": event_id},
        )

    engine.dispose()
    command.downgrade(alembic_config, "base")
    verification_engine = create_engine(isolated_postgres)
    assert expected_tables.isdisjoint(inspect(verification_engine).get_table_names())
    verification_engine.dispose()

    get_settings.cache_clear()
    get_engine.cache_clear()
