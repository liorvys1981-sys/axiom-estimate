"""Alembic migration environment for AXIOM ESTIMATE.

DATABASE_URL is read from the environment (or .env file) at runtime so
that the same migration scripts work against both SQLite (local dev) and
PostgreSQL (Railway production).
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Alembic Config object ────────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Target metadata ──────────────────────────────────────────────────────────
# Import Base so Alembic can detect model changes for autogenerate.
from app.db.models import Base  # noqa: E402

target_metadata = Base.metadata

# ── DATABASE_URL override ────────────────────────────────────────────────────
# Prefer the environment variable over alembic.ini so Railway injects the
# production PostgreSQL URL without touching the ini file.
_db_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
config.set_main_option("sqlalchemy.url", _db_url)


# ── Migration helpers ────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required).

    This emits the SQL to stdout / a file rather than executing it.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the database directly)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
