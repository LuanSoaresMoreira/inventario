from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from inventario_backend import main
from inventario_backend.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "inventario-backend"}


def test_health_endpoint_allows_frontend_origin() -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_database_health_when_database_is_available(monkeypatch) -> None:
    monkeypatch.setattr(main, "check_database", lambda: None)

    response = client.get("/api/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "postgresql"}


def test_database_health_hides_connection_error(monkeypatch) -> None:
    def unavailable_database() -> None:
        raise OperationalError("SELECT 1", {}, Exception("secret connection detail"))

    monkeypatch.setattr(main, "check_database", unavailable_database)

    response = client.get("/api/health/database")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
