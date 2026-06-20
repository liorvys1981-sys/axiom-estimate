"""Health check endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core import health as health_state
from app.core.config import get_settings
from app.db.session import check_database_connection

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def health():
    """Railway health check — returns 200 OK while the service is running."""
    return {"status": "ok"}


@router.get("/live")
async def liveness():
    """
    Liveness probe — returns 200 while the process is alive.

    Used by Railway, Kubernetes, and load balancers to detect a crashed or
    deadlocked process.  A 503 here triggers an automatic container restart.
    """
    if not health_state.is_alive():
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "timestamp": _now_iso()},
        )
    return {
        "status": "alive",
        "service": settings.service_name,
        "version": settings.app_version,
        "timestamp": _now_iso(),
    }


@router.get("/ready")
async def readiness():
    """
    Readiness probe — returns 200 when the app is ready to serve traffic.

    Checks both application state and database connectivity.  A 503 here
    removes the instance from the load balancer rotation without restarting it.
    """
    if not health_state.is_ready():
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": settings.service_name,
                "timestamp": _now_iso(),
            },
        )

    db = check_database_connection()
    overall_ok = db["status"] == "ok"

    body = {
        "status": "ready" if overall_ok else "degraded",
        "service": settings.service_name,
        "version": settings.app_version,
        "uptime_seconds": round(health_state.uptime_seconds(), 2),
        "timestamp": _now_iso(),
        "checks": {
            "database": db,
        },
    }

    if not overall_ok:
        return JSONResponse(status_code=503, content=body)
    return body


@router.get("/startup")
async def startup():
    """
    Startup probe — returns 200 once initialisation is complete.

    Railway and Kubernetes use this to delay liveness/readiness checks until
    the application has finished its boot sequence.
    """
    if not health_state.startup_complete():
        return JSONResponse(
            status_code=503,
            content={
                "status": "starting",
                "service": settings.service_name,
                "timestamp": _now_iso(),
            },
        )
    return {
        "status": "started",
        "service": settings.service_name,
        "version": settings.app_version,
        "timestamp": _now_iso(),
    }
