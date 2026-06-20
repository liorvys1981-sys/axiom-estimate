"""
Prometheus-compatible metrics endpoint.

GET /metrics  →  text/plain; version=0.0.4
              →  Prometheus exposition format

The response is intentionally plain text (not JSON) so that any
Prometheus-compatible scraper can consume it without configuration.

Example output
──────────────
    # HELP http_requests_total Total number of HTTP requests processed.
    # TYPE http_requests_total counter
    http_requests_total{method="GET",path="/api/v1/estimates",status="200"} 42
    # HELP http_errors_total Total number of HTTP 5xx responses.
    # TYPE http_errors_total counter
    # HELP http_request_duration_seconds HTTP request latency in seconds.
    # TYPE http_request_duration_seconds histogram
    http_request_duration_seconds_bucket{method="GET",path="/api/v1/estimates",le="0.005"} 10
    ...
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core import metrics as metrics_state

router = APIRouter(tags=["metrics"])

_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=True)
async def metrics() -> PlainTextResponse:
    """
    Expose all in-process metrics in Prometheus text exposition format.

    Suitable for scraping by Prometheus, Grafana Agent, VictoriaMetrics,
    or any OpenMetrics-compatible collector.
    """
    body = metrics_state.generate_metrics_text()
    return PlainTextResponse(content=body, media_type=_CONTENT_TYPE)
