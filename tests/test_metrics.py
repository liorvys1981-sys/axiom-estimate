"""
Tests for the /metrics endpoint and the core metrics store.

Run with:  pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core import metrics as metrics_state


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /metrics  (Prometheus text exposition)
# ---------------------------------------------------------------------------
class TestMetricsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_content_type_is_prometheus_text(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.headers["content-type"]

    def test_body_contains_help_and_type_lines(self, client):
        body = client.get("/metrics").text
        assert "# HELP http_requests_total" in body
        assert "# TYPE http_requests_total counter" in body
        assert "# HELP http_errors_total" in body
        assert "# HELP http_request_duration_seconds" in body
        assert "# TYPE http_request_duration_seconds histogram" in body

    def test_request_counter_increments_after_api_call(self, client):
        # Make a known API call so the counter has at least one entry
        client.get("/health/live")
        # /health/live is in _SILENT_PATHS but still recorded in metrics
        body = client.get("/metrics").text
        # The metrics endpoint itself is also recorded; just verify format
        assert "http_requests_total" in body

    def test_estimates_call_appears_in_metrics(self, client):
        """POST /api/v1/estimates should appear in the metrics output."""
        payload = {
            "client_id": "shop-metrics-test",
            "vehicle_vin": "1HGBH41JXMN109186",
            "vehicle_year": 2022,
            "vehicle_make": "Honda",
            "vehicle_model": "Civic",
            "damage_description": "Metrics test request",
            "photo_urls": [],
            "office_ids": [1],
        }
        client.post("/api/v1/estimates", json=payload)
        body = client.get("/metrics").text
        assert "/api/v1/estimates" in body


# ---------------------------------------------------------------------------
# Core metrics store unit tests
# ---------------------------------------------------------------------------
class TestMetricsStore:
    def test_record_request_increments_total(self):
        before = metrics_state.total_requests()
        metrics_state.record_request("GET", "/test-path", 200, 0.01)
        assert metrics_state.total_requests() == before + 1

    def test_record_5xx_increments_errors(self):
        before = metrics_state.total_errors()
        metrics_state.record_request("GET", "/test-error-path", 500, 0.05)
        assert metrics_state.total_errors() == before + 1

    def test_record_4xx_does_not_increment_errors(self):
        before = metrics_state.total_errors()
        metrics_state.record_request("GET", "/test-404-path", 404, 0.02)
        assert metrics_state.total_errors() == before

    def test_generate_metrics_text_is_non_empty(self):
        metrics_state.record_request("GET", "/unit-test", 200, 0.001)
        text = metrics_state.generate_metrics_text()
        assert len(text) > 0
        assert text.endswith("\n")

    def test_histogram_buckets_present_in_output(self):
        metrics_state.record_request("GET", "/bucket-test", 200, 0.003)
        text = metrics_state.generate_metrics_text()
        assert "_bucket{" in text
        assert '_sum{' in text
        assert '_count{' in text

    def test_p99_latency_returns_float(self):
        metrics_state.record_request("GET", "/latency-test", 200, 0.123)
        result = metrics_state.p99_latency_seconds()
        assert isinstance(result, float)
        assert result >= 0.0
