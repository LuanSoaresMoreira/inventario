import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from inventario_backend import main
from inventario_backend.main import app

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]


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


def test_openapi_contract_is_current() -> None:
    committed_contract = json.loads(
        (ROOT / "docs" / "openapi.json").read_text(encoding="utf-8")
    )

    assert committed_contract == app.openapi()
    assert set(committed_contract["paths"]) == {
        "/api/alerts",
        "/api/alerts/{alert_id}/mock-dispatch",
        "/api/alerts/generate",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/auth/me",
        "/api/auth/users/{user_id}/role",
        "/api/components",
        "/api/costs",
        "/api/dashboard/summary",
        "/api/environments",
        "/api/environments/{environment_id}",
        "/api/equipment",
        "/api/equipment/{equipment_id}",
        "/api/equipment/{equipment_id}/movements",
        "/api/equipment/{equipment_id}/public-access",
        "/api/equipment/{equipment_id}/public-access/revoke",
        "/api/equipment/{equipment_id}/public-access/rotate",
        "/api/equipment/{equipment_id}/warranties",
        "/api/failure-predictions",
        "/api/failure-predictions/evaluate",
        "/api/failure-predictions/generate",
        "/api/failure-predictions/monitoring",
        "/api/failure-predictions/notifications",
        "/api/failure-predictions/policies",
        "/api/failure-predictions/policies/{policy_id}/disable",
        "/api/failure-predictions/policies/{policy_id}/enable",
        "/api/failure-predictions/simulate",
        "/api/failure-predictions/{prediction_id}/decision",
        "/api/failure-predictions/{prediction_id}/mock-notify",
        "/api/health",
        "/api/health/database",
        "/api/maintenance-plans",
        "/api/maintenance-plans/{plan_id}",
        "/api/maintenance-plans/{plan_id}/approve",
        "/api/maintenance-plans/{plan_id}/publish",
        "/api/maintenance-plans/simulate",
        "/api/maintenances",
        "/api/maintenances/{maintenance_id}",
        "/api/maintenances/{maintenance_id}/components",
        "/api/maintenances/{maintenance_id}/costs",
        "/api/movements",
        "/api/notifications/deliveries",
        "/api/occurrences",
        "/api/occurrences/{occurrence_id}",
        "/api/occurrences/{occurrence_id}/comments",
        "/api/occurrences/{occurrence_id}/history",
        "/api/public/equipment/{public_token}",
        "/api/public/equipment/{public_token}/occurrences",
        "/api/public/occurrences/{tracking_token}",
        "/api/reports/inventory",
        "/api/reports/inventory.csv",
    }
