"""
Tests for health-check endpoints.

Run with:  pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.core import health as health_state


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /health  (shallow ping)
# ---------------------------------------------------------------------------
class TestShallowHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /health/live  (liveness probe)
# ---------------------------------------------------------------------------
class TestLiveness:
    def test_live_returns_200(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200

    def test_live_body(self, client):
        data = client.get("/health/live").json()
        assert data["status"] == "alive"
        assert "service" in data


# ---------------------------------------------------------------------------
# /health/ready  (readiness probe — now includes DB check)
# ---------------------------------------------------------------------------
class TestReadiness:
    def test_ready_after_startup_with_db_ok(self, client):
        """200 when startup complete and DB ping succeeds."""
        db_ok = {"ok": True, "detail": "database reachable", "url_set": False}
        with patch("app.core.health.check_database", return_value=db_ok):
            resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "uptime_seconds" in data
        assert "checks" in data
        assert data["checks"]["database"]["ok"] is True
        assert "metrics_summary" in data

    def test_ready_503_when_db_unreachable(self, client):
        """503 when DB ping fails even if startup is complete."""
        db_fail = {"ok": False, "detail": "connection refused", "url_set": True}
        with patch("app.core.health.check_database", return_value=db_fail):
            resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"]["ok"] is False

    def test_not_ready_before_startup(self):
        """503 when the lifespan hook has not yet called mark_ready."""
        health_state._ready = False
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                # TestClient does NOT run the lifespan here because we
                # bypassed it; _ready is still False from above.
                resp = c.get("/health/ready")
                assert resp.status_code == 503
        finally:
            health_state.mark_ready()


# ---------------------------------------------------------------------------
# /health/startup  (startup probe)
# ---------------------------------------------------------------------------
class TestStartup:
    def test_startup_returns_200_after_init(self, client):
        resp = client.get("/health/startup")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"
