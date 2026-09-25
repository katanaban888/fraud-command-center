from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"


def test_transactions_pagination_and_filters():
    with TestClient(app) as client:
        response = client.get("/api/transactions?page=1&page_size=3&is_fraud=true")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) <= 3
    assert payload["pagination"]["page_size"] == 3
    assert all(item["is_fraud"] for item in payload["items"])


def test_unknown_alert_returns_not_found():
    with TestClient(app) as client:
        response = client.get("/api/alerts/ALR-NOT-FOUND")

    assert response.status_code == 404


def test_rule_simulation_returns_bounded_metrics():
    with TestClient(app) as client:
        response = client.post("/api/rules/simulate", json={"rule_id": "R004", "version": "V2"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["alert_volume"] >= payload["confirmed_fraud"]
    assert 0 <= payload["precision"] <= 1
    assert 0 <= payload["recall"] <= 1
    assert 0 <= payload["false_positive_rate"] <= 1
