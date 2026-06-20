"""
Global error-handling middleware.

Catches all unhandled exceptions that escape route handlers and returns a
structured JSON error response.  Sensitive details (tracebacks, internal
paths) are hidden in production; full context is logged server-side.
"""
from __future__ import annotations

import logging
import traceback
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import get_settings

logger = logging.getLogger("axiom.errors")
settings = get_settings()


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return a structured error response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        try:
            return await call_next(request)

        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(
                "Unhandled exception on %s %s — %s",
                request.method,
                request.url.path,
                exc,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "exception_type": type(exc).__name__,
                    "traceback": tb,
                },
            )

            # In production, never leak internal details to the client.
            if settings.is_production:
                body = {
                    "error": "internal_server_error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "request_id": request_id,
                }
            else:
                body = {
                    "error": "internal_server_error",
                    "message": str(exc),
                    "exception_type": type(exc).__name__,
                    "request_id": request_id,
                    "traceback": tb.splitlines(),
                }

            return JSONResponse(
                status_code=500,
                content=body,
                headers={"X-Request-ID": request_id},
            )
