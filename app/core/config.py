"""Application configuration using environment variables."""
import os
from functools import lru_cache

# Minimum acceptable length for JWT secret keys.
_JWT_SECRET_MIN_LENGTH = 32

# Default allowed origins for CORS when ALLOWED_ORIGINS is not set.
_DEFAULT_ALLOWED_ORIGINS = ["https://axiom-estimate-production.up.railway.app"]


class Settings:
    """Central settings loaded from environment variables."""

    app_name: str = os.getenv("APP_NAME", "AXIOM ESTIMATE")
    app_version: str = os.getenv("APP_VERSION", "2.0.0")
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    service_name: str = os.getenv("SERVICE_NAME", "api-gateway")
    service_port: int = int(os.getenv("SERVICE_PORT", "8000"))

    # Database (injected at runtime in production via Secret Manager)
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./axiom_dev.db")

    # JWT
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-insecure-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # CORS — comma-separated list of allowed origins, e.g.:
    #   ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com
    _allowed_origins_raw: str = os.getenv("ALLOWED_ORIGINS", "")

    # Feature flags
    guardian_enabled: bool = os.getenv("GUARDIAN_ENABLED", "false").lower() == "true"

    def __init__(self) -> None:
        self._validate_secrets()

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
