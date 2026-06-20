"""
Health check endpoints for axiom-estimate.

Probe semantics
───────────────
GET /health          – Shallow ping; always 200 while the process is up.
                       Used by Railway / load-balancer health checks.

GET /health/live     – Kubernetes liveness probe.
                       200 → process is alive; 503 → restart the pod.

GET /health/ready    – Kubernetes readiness probe.
                       200 → app is initialised AND database is reachable.
                       503 → remove from load-balancer rotation.
                       Includes: uptime, DB status, aggregate request stats.

GET /health/startup  – Kubernetes startup probe.
                       200 → lifespan init complete; 503 → still starting.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core import health as health_state
from app.core import metrics as metrics_state
from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("")
async def health():
    """Railway / load-balancer health check — always 200 while the process is up."""
    return {"status": "ok"}


@router.get("/live")
async def liveness():
    """Kubernetes liveness probe — 200 while the process is alive."""
    if not health_state.is_alive():
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return {"status": "alive", "service": settings.service_name}


@router.get("/ready")
async def readiness():
    """
    Kubernetes readiness probe.

    Returns 200 only when:
      1. The lifespan startup hook has completed (mark_ready called).
      2. DATABASE_URL is set and the database responds to a SELECT 1 ping.

    Returns 503 otherwise so the pod is removed from the load-balancer
    rotation until it is genuinely ready.
    """
    if not health_state.is_ready():
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "service": settings.service_name},
        )

    db = health_state.check_database()
    if not db["ok"]:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": settings.service_name,
                "checks": {
                    "database": {
                        "ok": False,
                        "detail": db["detail"],
                    }
                },
            },
        )

    return {
        "status": "ready",
        "service": settings.service_name,
        "uptime_seconds": round(health_state.uptime_seconds(), 2),
        "checks": {
            "database": {
                "ok": db["ok"],
                "detail": db["detail"],
                "url_configured": db["url_set"],
            }
        },
        "metrics_summary": {
            "total_requests": metrics_state.total_requests(),
            "total_errors": metrics_state.total_errors(),
            "p99_latency_seconds": round(metrics_state.p99_latency_seconds(), 4),
        },
    }


@router.get("/startup")
async def startup():
    """Kubernetes startup probe — 200 once lifespan initialisation is complete."""
    if not health_state.startup_complete():
        return JSONResponse(
            status_code=503,
            content={"status": "starting", "service": settings.service_name},
        )
    return {"status": "started", "service": settings.service_name}

