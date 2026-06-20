"""
Database session management.

Supports SQLite (development) and PostgreSQL (production) via SQLAlchemy.
Connection pooling is configured for production workloads; SQLite uses a
StaticPool to avoid cross-thread issues in tests.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def _build_engine():
    """Create a SQLAlchemy engine tuned for the configured database backend."""
    url = settings.database_url

    if settings.use_sqlite:
        # SQLite — used for local development and tests only.
        # StaticPool keeps a single connection so in-memory DBs survive across
        # requests; check_same_thread=False is required for FastAPI's thread pool.
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.is_development,
        )
        # Enable WAL mode for better concurrent read performance on SQLite.
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    else:
        # PostgreSQL (or any other production-grade RDBMS).
        engine = create_engine(
            url,
            # Pool sizing: 5 persistent connections, up to 10 overflow under load.
            pool_size=5,
            max_overflow=10,
            # Recycle connections after 30 minutes to avoid stale TCP sessions.
            pool_recycle=1800,
            # Verify connections are alive before handing them to the application.
            pool_pre_ping=True,
            echo=False,
        )

    return engine


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Dependency injection helper ───────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and guarantees cleanup.

    Usage::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Health check ──────────────────────────────────────────────────────────────

def check_database_connection() -> dict:
    """
    Verify that the database is reachable.

    Returns a dict with ``status`` ("ok" or "error") and optional ``detail``.
    Safe to call from health-check endpoints — never raises.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "backend": settings.database_url.split("://")[0]}
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
