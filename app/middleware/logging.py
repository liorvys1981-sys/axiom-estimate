"""
Request/response logging middleware.

Logs every inbound request and its outcome with:
  - A unique request ID (X-Request-ID header, generated if absent)
  - HTTP method, path, status code
  - Wall-clock execution time in milliseconds
  - Client IP address

In production the log records are emitted as JSON (via python-json-logger).
In development they are plain-text for readability.
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("axiom.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request/response pair with timing and a correlation ID."""

    # Paths that are too noisy to log at INFO level (health probes, metrics).
    _QUIET_PATHS = {"/health/live", "/health/ready", "/health/startup", "/metrics"}

    async def dispatch(self, request: Request, call_next) -> Response:
        # Propagate or generate a request ID for distributed tracing.
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        start = time.perf_counter()
        response: Response | None = None

        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            status_code = response.status_code if response is not None else 500

            log_level = logging.INFO
            if request.url.path in self._QUIET_PATHS:
                log_level = logging.DEBUG
            elif status_code >= 500:
                log_level = logging.ERROR
            elif status_code >= 400:
                log_level = logging.WARNING

            logger.log(
                log_level,
                "%s %s %s %.1fms",
                request.method,
                request.url.path,
                status_code,
                elapsed_ms,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(elapsed_ms, 1),
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )

            if response is not None:
                response.headers["X-Request-ID"] = request_id
