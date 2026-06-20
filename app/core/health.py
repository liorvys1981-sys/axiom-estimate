"""
Health check state management for axiom-estimate.

Liveness  – is the process alive?  (always True while running)
Readiness – is the app ready to serve traffic?
            Requires: startup complete AND database reachable.
Startup   – has the lifespan initialisation finished?

The DB connectivity check is intentionally lightweight: it opens a
connection, issues a trivial query (SELECT 1), and closes immediately.
SQLite (dev) and PostgreSQL (prod) are both supported via the standard
DATABASE_URL env-var.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_startup_time: float = time.monotonic()
_ready: bool = False


# ---------------------------------------------------------------------------
# Lifecycle hooks
# ---------------------------------------------------------------------------
def mark_ready() -> None:
    """Mark the service as ready to accept traffic."""
    global _ready
    _ready = True


# ---------------------------------------------------------------------------
# Probe helpers
# ---------------------------------------------------------------------------
def is_alive() -> bool:
    """Always True while the process is running."""
    return True


def is_ready() -> bool:
    """True only when startup is complete AND the database is reachable."""
    return _ready


def startup_complete() -> bool:
    """True once the lifespan initialisation has finished."""
    return _ready


def uptime_seconds() -> float:
    """Seconds elapsed since the module was first imported."""
    return time.monotonic() - _startup_time


# ---------------------------------------------------------------------------
# Database connectivity check
# ---------------------------------------------------------------------------
def check_database() -> Dict[str, Any]:
    """
    Attempt a trivial query against the configured DATABASE_URL.

    Returns a dict with keys:
        ok      – bool, True if the ping succeeded
        detail  – human-readable status string
        url_set – bool, True if DATABASE_URL is configured (non-default)

    Never raises — all exceptions are caught and surfaced via ``ok=False``.
    """
    database_url: str = os.getenv("DATABASE_URL", "")
    url_set: bool = bool(database_url) and database_url != "sqlite:///./axiom_dev.db"

    if not database_url:
        return {
            "ok": False,
            "detail": "DATABASE_URL is not set",
            "url_set": False,
        }

    try:
        # Use SQLAlchemy if available (already a transitive dep in many setups);
        # fall back to a raw sqlite3 ping for the dev SQLite case.
        if database_url.startswith("sqlite"):
            import sqlite3

            db_path = database_url.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path, timeout=2)
            conn.execute("SELECT 1")
            conn.close()
        else:
            # PostgreSQL / MySQL via SQLAlchemy (optional dep)
            try:
                from sqlalchemy import create_engine, text  # type: ignore[import-untyped]

                engine = create_engine(database_url, pool_pre_ping=True, pool_size=1, max_overflow=0)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                engine.dispose()
            except ImportError:
                # SQLAlchemy not installed — cannot verify non-sqlite DBs.
                return {
                    "ok": False,
                    "detail": "sqlalchemy not installed; cannot verify non-sqlite database connectivity",
                    "url_set": url_set,
                }

        return {"ok": True, "detail": "database reachable", "url_set": url_set}

    except Exception as exc:  # noqa: BLE001
        logger.warning("Database health check failed: %s", exc)
        return {"ok": False, "detail": str(exc), "url_set": url_set}
