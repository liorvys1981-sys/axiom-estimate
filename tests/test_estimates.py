"""
Tests for the estimates API endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


VALID_PAYLOAD = {
    "client_id": "shop-001",
    "vehicle_vin": "1HGBH41JXMN109186",
    "vehicle_year": 2022,
    "vehicle_make": "Honda",
    "vehicle_model": "Civic",
    "damage_description": "Front bumper damage",
    "photo_urls": [],
    "office_ids": [1],
}


class TestCreateEstimate:
    def test_returns_202(self, client):
        resp = client.post("/api/v1/estimates", json=VALID_PAYLOAD)
        assert resp.status_code == 202

    def test_response_has_estimate_id(self, client):
        data = client.post("/api/v1/estimates", json=VALID_PAYLOAD).json()
        assert "estimate_id" in data
        assert len(data["estimate_id"]) == 36  # UUID4

    def test_response_status_is_pending(self, client):
        data = client.post("/api/v1/estimates", json=VALID_PAYLOAD).json()
        assert data["status"] == "pending"

    def test_invalid_vin_rejected(self, client):
        payload = {**VALID_PAYLOAD, "vehicle_vin": "SHORT"}
        resp = client.post("/api/v1/estimates", json=payload)
        assert resp.status_code == 422

    def test_missing_required_field(self, client):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "client_id"}
        resp = client.post("/api/v1/estimates", json=payload)
        assert resp.status_code == 422


class TestGetEstimate:
    def test_returns_200(self, client):
        estimate_id = "123e4567-e89b-12d3-a456-426614174000"
        resp = client.get(f"/api/v1/estimates/{estimate_id}")
        assert resp.status_code == 200

    def test_returns_estimate_id_in_response(self, client):
        estimate_id = "123e4567-e89b-12d3-a456-426614174000"
        data = client.get(f"/api/v1/estimates/{estimate_id}").json()
        assert data["estimate_id"] == estimate_id
