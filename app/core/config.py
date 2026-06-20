"""Application configuration using pydantic-settings."""
from __future__ import annotations

import logging
import logging.config
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings — values are read from environment variables.

    All fields have sensible defaults for local development.  In
    production (APP_ENV=production) the DATABASE_URL and JWT_SECRET_KEY
    *must* be supplied via Railway environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "AXIOM ESTIMATE"
    app_version: str = "2.0.0"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    service_name: str = "api-gateway"
    service_port: int = 8000

    # ── Database ─────────────────────────────────────────────────────────
    # SQLite for local dev; PostgreSQL in production via Railway DATABASE_URL
    database_url: str = "sqlite:///./axiom_dev.db"

    # ── JWT ──────────────────────────────────────────────────────────────
    jwt_secret_key: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── Feature flags ────────────────────────────────────────────────────
    guardian_enabled: bool = False

    # ── Derived helpers ──────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    # ── Validators ───────────────────────────────────────────────────────
    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}, got {v!r}")
        return upper

    @field_validator("jwt_secret_key")
    @classmethod
    def _warn_insecure_secret(cls, v: str) -> str:
        if v == "dev-insecure-change-me":
            # Logged after logging is configured; use print as a fallback here
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY is set to the insecure default. "
                "Set a strong secret in production.",
                stacklevel=2,
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

def configure_logging(settings: Settings | None = None) -> None:
    """Configure structured logging for the application.

    In production a JSON-friendly format is used so that Railway's log
    aggregation can parse fields easily.  In development a human-readable
    format is used instead.
    """
    if settings is None:
        settings = get_settings()

    fmt_plain = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    fmt_json = (
        '{"time":"%(asctime)s","level":"%(levelname)s",'
        '"logger":"%(name)s","message":"%(message)s"}'
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {"format": fmt_plain},
                "json": {"format": fmt_json},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "json" if settings.is_production else "plain",
                }
            },
            "root": {
                "level": settings.log_level,
                "handlers": ["console"],
            },
            # Quieten noisy third-party loggers
            "loggers": {
                "uvicorn.access": {"level": "WARNING", "propagate": True},
                "sqlalchemy.engine": {
                    "level": "WARNING" if settings.is_production else "INFO",
                    "propagate": True,
                },
            },
        }
    )
