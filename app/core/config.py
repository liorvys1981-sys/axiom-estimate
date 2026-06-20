"""Application configuration via pydantic-settings (env vars + .env file)."""
from __future__ import annotations

import logging
import warnings
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Minimum acceptable length for JWT secret keys.
_JWT_SECRET_MIN_LENGTH = 32

# Default allowed origins for CORS when ALLOWED_ORIGINS is not set.
_DEFAULT_ALLOWED_ORIGINS = ["https://axiom-estimate-production.up.railway.app"]


_INSECURE_SECRET = "dev-insecure-change-me"

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings(BaseSettings):
    """Central settings — values are read from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = Field("AXIOM ESTIMATE", alias="APP_NAME")
    app_version: str = Field("2.0.0", alias="APP_VERSION")
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    service_name: str = Field("api-gateway", alias="SERVICE_NAME")
    service_port: int = Field(8000, alias="SERVICE_PORT")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = Field("sqlite:///./axiom_dev.db", alias="DATABASE_URL")

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(_INSECURE_SECRET, alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(60, alias="JWT_EXPIRE_MINUTES")

<<<<<<< HEAD
    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS",
    )

    # ── Feature flags ─────────────────────────────────────────────────────────
    guardian_enabled: bool = Field(False, alias="GUARDIAN_ENABLED")

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: Any) -> str:
        upper = str(v).upper()
        if upper not in _LOG_LEVELS:
            raise ValueError(f"log_level must be one of {_LOG_LEVELS}, got {v!r}")
        return upper

    @field_validator("app_env", mode="before")
    @classmethod
    def validate_app_env(cls, v: Any) -> str:
        allowed = {"development", "staging", "production"}
        lower = str(v).lower()
        if lower not in allowed:
            raise ValueError(f"app_env must be one of {allowed}, got {v!r}")
        return lower

    @model_validator(mode="after")
    def warn_insecure_secret_in_production(self) -> "Settings":
        if self.is_production and self.jwt_secret_key == _INSECURE_SECRET:
            warnings.warn(
                "JWT_SECRET_KEY is set to the insecure default in production! "
                "Set a cryptographically random secret immediately.",
                stacklevel=2,
            )
        return self

    # ── Derived properties ────────────────────────────────────────────────────
=======
    # CORS — comma-separated list of allowed origins, e.g.:
    #   ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
    _allowed_origins_raw: str = os.getenv("ALLOWED_ORIGINS", "")

    # Feature flags
    guardian_enabled: bool = os.getenv("GUARDIAN_ENABLED", "false").lower() == "true"
>>>>>>> origin/main

    def __init__(self) -> None:
        self._validate_secrets()

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
<<<<<<< HEAD
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def use_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def effective_cors_origins(self) -> list[str]:
        """Return CORS origins appropriate for the current environment."""
        if self.is_production:
            # In production, only allow explicitly configured origins.
            # Fall back to the axiom domain if the default dev list slipped through.
            dev_defaults = {"http://localhost:3000", "http://localhost:8000"}
            prod_origins = [o for o in self.cors_origins if o not in dev_defaults]
            return prod_origins or ["https://axiomestimate.com"]
        return self.cors_origins

    def configure_logging(self) -> None:
        """Apply structured logging configuration for the current environment."""
        if self.is_production:
            # JSON logging in production — consumed by Railway / log aggregators.
            try:
                from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

                handler = logging.StreamHandler()
                formatter = jsonlogger.JsonFormatter(
                    fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                )
                handler.setFormatter(formatter)
                logging.root.handlers = [handler]
            except ImportError:
                # Graceful fallback if python-json-logger is somehow missing.
                logging.basicConfig(
                    level=self.log_level,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                )
        else:
            logging.basicConfig(
                level=self.log_level,
                format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            )
        logging.root.setLevel(self.log_level)
=======
    def allowed_origins(self) -> list[str]:
        """Return the list of CORS-allowed origins.

        Reads ALLOWED_ORIGINS (comma-separated).  Falls back to the
        production default when the variable is absent or empty.
        """
        raw = self._allowed_origins_raw.strip()
        if raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return _DEFAULT_ALLOWED_ORIGINS

    # ------------------------------------------------------------------
    # Secrets validation
    # ------------------------------------------------------------------

    def _validate_secrets(self) -> None:
        """Enforce critical secret constraints in production.

        Raises ``ValueError`` at startup if any required secret is
        missing or insecure so that a misconfigured deploy fails fast
        rather than running with unsafe defaults.
        """
        if not self.is_production:
            return

        errors: list[str] = []

        # JWT secret must be present and long enough to be secure.
        if not self.jwt_secret_key or len(self.jwt_secret_key) < _JWT_SECRET_MIN_LENGTH:
            errors.append(
                f"JWT_SECRET_KEY must be at least {_JWT_SECRET_MIN_LENGTH} characters "
                f"in production (got {len(self.jwt_secret_key or '')} chars)."
            )

        # DATABASE_URL must be set to a real database, not the dev SQLite fallback.
        if not self.database_url or self.database_url.startswith("sqlite"):
            errors.append(
                "DATABASE_URL must be set to a non-SQLite database URL in production."
            )

        if errors:
            raise ValueError(
                "Production secrets validation failed:\n"
                + "\n".join(f"  • {e}" for e in errors)
            )
>>>>>>> origin/main


@lru_cache()
def get_settings() -> Settings:
    return Settings()
