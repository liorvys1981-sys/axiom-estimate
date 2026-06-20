"""
Prometheus metrics endpoint.

Exposes /metrics in the Prometheus text exposition format.  The endpoint is
consumed by a Prometheus scraper (Railway metrics plugin, k8s ServiceMonitor,
or a standalone Prometheus instance).

Tracked metrics:
  - http_requests_total          — counter by method, path, status
  - http_request_duration_seconds — histogram of request latency
  - db_pool_connections          — gauge for connection pool stats (PostgreSQL)
  - estimates_created_total      — business counter for new estimates
  - estimates_by_status          — gauge per status bucket
"""
from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"])

# ── Prometheus metric definitions ─────────────────────────────────────────────
# Metrics are defined at module level so they persist across requests.

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _PROMETHEUS_AVAILABLE = True

    HTTP_REQUESTS_TOTAL = Counter(
        "http_requests_total",
        "Total HTTP requests received",
        ["method", "path", "status_code"],
    )

    HTTP_REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
        buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    )

    ESTIMATES_CREATED = Counter(
        "estimates_created_total",
        "Total number of damage estimates submitted",
    )

    ESTIMATES_BY_STATUS = Gauge(
        "estimates_by_status",
        "Current count of estimates grouped by status",
        ["status"],
    )

    DB_POOL_CONNECTIONS = Gauge(
        "db_pool_connections",
        "Database connection pool statistics",
        ["state"],  # checked_in | checked_out | overflow
    )

except ImportError:
    _PROMETHEUS_AVAILABLE = False
    logger.warning(
        "prometheus-client is not installed — /metrics will return a 501 stub. "
        "Add prometheus-client to requirements.txt to enable metrics."
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    include_in_schema=False,  # Keep out of public OpenAPI docs
    summary="Prometheus metrics",
)
async def prometheus_metrics() -> PlainTextResponse:
    """
    Expose Prometheus metrics for scraping.

    Returns metrics in the standard Prometheus text exposition format
    (Content-Type: text/plain; version=0.0.4).
    """
    if not _PROMETHEUS_AVAILABLE:
        return PlainTextResponse(
            content="# prometheus-client not installed\n",
            status_code=501,
        )

    # Refresh connection pool gauges if using SQLAlchemy with a real pool.
    _update_pool_metrics()

    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


def _update_pool_metrics() -> None:
    """Refresh DB pool gauges from the SQLAlchemy engine pool stats."""
    if not _PROMETHEUS_AVAILABLE:
        return
    try:
        from app.db.session import engine
        from sqlalchemy.pool import StaticPool

        pool = engine.pool
        if isinstance(pool, StaticPool):
            # SQLite StaticPool has no meaningful pool stats.
            return

        DB_POOL_CONNECTIONS.labels(state="checked_in").set(pool.checkedin())
        DB_POOL_CONNECTIONS.labels(state="checked_out").set(pool.checkedout())
        DB_POOL_CONNECTIONS.labels(state="overflow").set(pool.overflow())
    except Exception as exc:
        logger.debug("Could not update pool metrics: %s", exc)
