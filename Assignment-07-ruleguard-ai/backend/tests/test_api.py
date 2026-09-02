"""API-level: input validation, kill switch, stub mode. cd backend && pytest -v"""
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_empty_request_returns_400():
    resp = client.post("/api/v1/risk/judge", json={"request": ""})
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_error"


def test_missing_field_returns_400():
    assert client.post("/api/v1/risk/judge", json={}).status_code == 400


def test_too_long_request_returns_400():
    assert client.post("/api/v1/risk/judge", json={"request": "x" * 2001}).status_code == 400


def test_kill_switch_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", False)
    resp = client.post("/api/v1/risk/judge", json={"request": "Allow users to log in."})
    assert resp.status_code == 503
    assert resp.json()["error"] == "llm_disabled"


def test_stub_mode_returns_schema_valid_response(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_stub", True)
    resp = client.post("/api/v1/risk/judge", json={"request": "Allow users to log in."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] in {"low", "medium", "high"}
    assert 0.0 <= body["confidence"] <= 1.0


def test_health_endpoint_reports_status():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "llm_enabled" in resp.json()
