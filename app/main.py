"""
AXIOM ESTIMATE — API Gateway
FastAPI application entry-point.
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import estimates, health, metrics
from app.core import health as health_state
from app.core.config import get_settings
from app.core.logging import configure_logging, request_id_var
from app.core import metrics as metrics_state

settings = get_settings()

# Configure structured JSON logging before anything else emits a log record.
configure_logging(log_level=settings.log_level)
logger = logging.getLogger(__name__)

# Paths excluded from request-log noise (probes + metrics scrapes)
_SILENT_PATHS = frozenset({"/health", "/health/live", "/health/ready", "/health/startup", "/metrics"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    logger.info(
        "Starting service",
        extra={
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        },
    )
    health_state.mark_ready()
    logger.info("Service ready", extra={"service": settings.service_name})
    yield
    logger.info("Shutting down", extra={"service": settings.service_name})


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Autonomous automotive damage-estimation platform. "
        "Multi-agent AI pipeline for insurance, total-loss, lien, audit and CPO services."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else ["https://axiomestimate.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Metrics + structured-request-logging middleware ───────────────────────────
@app.middleware("http")
async def metrics_and_logging_middleware(request: Request, call_next):
    """
    Per-request middleware that:
      1. Generates a unique request_id and stores it in a ContextVar so that
         every log record emitted during this request carries it automatically.
      2. Measures end-to-end latency.
      3. Records the result in the in-process metrics store.
      4. Emits a structured access-log entry (skipped for probe/metrics paths
         to avoid polluting logs with high-frequency noise).
    """
    req_id = str(uuid.uuid4())
    token = request_id_var.set(req_id)

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency = time.perf_counter() - start
        metrics_state.record_request(request.method, request.url.path, 500, latency)
        raise
    finally:
        request_id_var.reset(token)

    latency = time.perf_counter() - start
    path = request.url.path
    status_code = response.status_code

    metrics_state.record_request(request.method, path, status_code, latency)

    if path not in _SILENT_PATHS:
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": path,
                "status_code": status_code,
                "latency_ms": round(latency * 1000, 2),
                "request_id": req_id,
            },
        )

    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(estimates.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.service_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
