from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200


def test_list_scenarios():
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert "inventory_alert" in r.json()["scenarios"]


def test_run_unknown_scenario():
    r = client.post("/api/scenarios/not_exist/run", json={"params": {}})
    assert r.status_code == 404