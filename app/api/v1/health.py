"""Health check endpoints."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core import health as health_state
from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("")
async def health():
    """Simple health check — returns 200 OK for Railway and similar platforms."""
    return {"status": "ok"}


@router.get("/live")
async def liveness():
    """Kubernetes liveness probe — returns 200 while process is alive."""
    if not health_state.is_alive():
        return JSONResponse(status_code=503, content={"status": "unhealthy"})
    return {"status": "alive", "service": settings.service_name}


@router.get("/ready")
async def readiness():
    """Kubernetes readiness probe — returns 200 when app is ready for traffic."""
    if not health_state.is_ready():
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "service": settings.service_name},
        )
    return {
        "status": "ready",
        "service": settings.service_name,
        "uptime_seconds": round(health_state.uptime_seconds(), 2),
    }


@router.get("/startup")
async def startup():
    """Kubernetes startup probe — returns 200 once initialisation is complete."""
    if not health_state.startup_complete():
        return JSONResponse(
            status_code=503,
            content={"status": "starting", "service": settings.service_name},
        )
    return {"status": "started", "service": settings.service_name}
