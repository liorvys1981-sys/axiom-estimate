"""
AXIOM ESTIMATE — API Gateway
FastAPI application entry-point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import estimates, health
from app.core import health as health_state
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup → yield → shutdown."""
    logger.info("Starting %s v%s [%s]", settings.app_name, settings.app_version, settings.app_env)
    health_state.mark_ready()
    logger.info("Service ready — %s", settings.service_name)
    yield
    logger.info("Shutting down %s", settings.service_name)


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

# ---------------------------------------------------------------------------
# CORS — origins driven by ALLOWED_ORIGINS env var in production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(health.router)
app.include_router(estimates.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": settings.service_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
