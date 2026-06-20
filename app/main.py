"""
AXIOM ESTIMATE — API Gateway
FastAPI application entry-point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import estimates, health
from app.core import health as health_state
from app.core.config import configure_logging, get_settings
from app.db.session import check_db_connection, init_db

settings = get_settings()

# Configure structured logging before anything else runs
configure_logging(settings)
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

    # ── Database initialisation ──────────────────────────────────────────
    if check_db_connection():
        logger.info("Database connection verified (%s)", settings.database_url.split("@")[-1])
        init_db()
    else:
        logger.error(
            "Cannot reach database at startup — service will start but persistence "
            "is unavailable until the database becomes reachable."
        )

    health_state.mark_ready()
    logger.info("Service ready — %s", settings.service_name)

    yield

    # ── Graceful shutdown ────────────────────────────────────────────────
    logger.info("Shutting down %s — disposing connection pool…", settings.service_name)
    from app.db.session import engine
    engine.dispose()
    logger.info("Connection pool disposed. Goodbye.")


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

# CORS — tighten origins in production via environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else ["https://axiomestimate.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
