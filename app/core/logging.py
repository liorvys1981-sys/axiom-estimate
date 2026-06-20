"""
Structured JSON logging for axiom-estimate.

Configures the root logger (and uvicorn loggers) to emit every log record
as a single-line JSON object so that log-aggregation tools (Cloud Logging,
Datadog, Loki, …) can parse fields without regex.

Fields emitted on every record
───────────────────────────────
  timestamp    – ISO-8601 UTC (from pythonjsonlogger)
  level        – DEBUG / INFO / WARNING / ERROR / CRITICAL
  message      – the formatted log message
  logger       – logger name (e.g. "app.main", "uvicorn.access")
  service      – SERVICE_NAME env-var (default "api-gateway")
  environment  – APP_ENV env-var (default "development")
  request_id   – populated by MetricsMiddleware via contextvars; empty string
                 when no request context is active

Usage
─────
    from app.core.logging import configure_logging
    configure_logging(log_level="INFO")
"""
from __future__ import annotations

import logging
import os
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Context variable – set per-request by the metrics/logging middleware
# ---------------------------------------------------------------------------
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


# ---------------------------------------------------------------------------
# Custom formatter
# ---------------------------------------------------------------------------
class _AxiomJsonFormatter(jsonlogger.JsonFormatter):
    """Extends JsonFormatter with static service-level fields."""

    _service: str = os.getenv("SERVICE_NAME", "api-gateway")
    _environment: str = os.getenv("APP_ENV", "development")

    def add_fields(
        self,
        log_record: dict,
        record: logging.LogRecord,
        message_dict: dict,
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Rename pythonjsonlogger's default key to our convention
        log_record["timestamp"] = log_record.pop("asctime", None) or log_record.get("timestamp")
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = self._service
        log_record["environment"] = self._environment
        log_record["request_id"] = request_id_var.get()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_CONFIGURED = False


def configure_logging(log_level: str = "INFO") -> None:
    """
    Replace all handlers on the root logger (and key uvicorn loggers) with a
    single StreamHandler that emits JSON.  Safe to call multiple times — only
    the first call takes effect.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = _AxiomJsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        rename_fields={"asctime": "timestamp"},
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    # Root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Silence noisy third-party loggers while keeping our level
    for noisy in ("uvicorn.error", "uvicorn.access", "uvicorn", "fastapi"):
        lg = logging.getLogger(noisy)
        lg.handlers.clear()
        lg.addHandler(handler)
        lg.setLevel(numeric_level)
        lg.propagate = False
