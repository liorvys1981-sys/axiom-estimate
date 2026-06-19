"""Application configuration using environment variables."""
import os
from functools import lru_cache


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

    # Feature flags
    guardian_enabled: bool = os.getenv("GUARDIAN_ENABLED", "false").lower() == "true"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
