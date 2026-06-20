"""SQLAlchemy session factory and database initialisation."""
from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_settings = get_settings()

# ---------------------------------------------------------------------------
# Engine configuration
# ---------------------------------------------------------------------------
_is_sqlite = _settings.database_url.startswith("sqlite")

_connect_args: dict = {"check_same_thread": False} if _is_sqlite else {}

_pool_kwargs: dict = (
    {}
    if _is_sqlite
    else {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # recycle connections every 30 min
    }
)

engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    **_pool_kwargs,
)

# Enable WAL mode for SQLite to improve concurrent read performance
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Dependency / context-manager helpers
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError as exc:
        logger.error("Database connection check failed: %s", exc)
        return False


def init_db() -> None:
    """Create all tables that do not yet exist (dev/test convenience).

    In production, schema changes are managed by Alembic migrations.
    This function is a no-op when the tables already exist.
    """
    from app.db.models import Base  # local import to avoid circular deps

    logger.info("Initialising database schema (create_all)…")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema ready.")
