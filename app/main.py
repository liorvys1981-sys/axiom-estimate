"""
AXIOM ESTIMATE — API Gateway
FastAPI application entry-point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import estimates, health, metrics
from app.core import health as health_state
from app.core.config import get_settings
from app.db.session import check_database_connection
from app.middleware.errors import ErrorHandlingMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.security import SecurityHeadersMiddleware

settings = get_settings()

# Configure logging before anything else so all subsequent log calls are
# formatted correctly (JSON in production, plain text in development).
settings.configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    logger.info(
        "Starting %s v%s [env=%s]",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )

    # Verify database connectivity at startup so a misconfigured DATABASE_URL
    # surfaces immediately rather than on the first real request.
    db_status = check_database_connection()
    if db_status["status"] == "ok":
        logger.info("Database connection OK (backend=%s)", db_status.get("backend"))
    else:
        logger.warning(
            "Database connection FAILED at startup: %s — service will start but "
            "database-dependent endpoints will return errors.",
            db_status.get("detail"),
        )

    health_state.mark_ready()
    logger.info("Service ready — %s", settings.service_name)

    yield

    # Graceful shutdown: log and allow in-flight requests to drain.
    logger.info("Shutting down %s — draining connections", settings.service_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Autonomous automotive damage-estimation platform. "
        "Multi-agent AI pipeline for insurance, total-loss, lien, audit and CPO services."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    # Disable OpenAPI schema in production to reduce attack surface.
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

<<<<<<< HEAD
# ── Middleware (applied in reverse order — last added = outermost) ─────────────
# 1. Error handler — must be outermost so it catches errors from all layers.
app.add_middleware(ErrorHandlingMiddleware)
# 2. Security headers — applied to every response.
app.add_middleware(SecurityHeadersMiddleware)
# 3. Request logging — logs after security headers are set.
app.add_middleware(RequestLoggingMiddleware)
# 4. CORS — innermost so preflight requests are handled before auth/logging.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
=======
# ---------------------------------------------------------------------------
# CORS — origins driven by ALLOWED_ORIGINS env var in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
>>>>>>> origin/main
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
# ── Routers ───────────────────────────────────────────────────────────────────
=======

# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Attach security headers to every HTTP response."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


# Routers
>>>>>>> origin/main
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(estimates.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.service_name,
        "version": settings.app_version,
        "docs": "/docs" if not settings.is_production else "disabled",
    }
