"""
Tests for health-check endpoints.

Run with:  pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import health as health_state


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


class TestLiveness:
    def test_live_returns_200(self, client):
        resp = client.get("/health/live")
        assert resp.status_code == 200

    def test_live_body(self, client):
        data = client.get("/health/live").json()
        assert data["status"] == "alive"
        assert "service" in data


class TestReadiness:
    def test_ready_after_startup(self, client):
        # The lifespan context calls mark_ready(), so after app startup it's ready
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_not_ready_before_startup(self):
        # Temporarily reset ready flag
        health_state._ready = False
        with TestClient(app, raise_server_exceptions=False):
            pass
        # Restore
        health_state.mark_ready()


class TestStartup:
    def test_startup_returns_200_after_init(self, client):
        resp = client.get("/health/startup")
        assert resp.status_code == 200
        assert resp.json()["status"] == "started"
