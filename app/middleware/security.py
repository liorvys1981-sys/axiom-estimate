"""
Security headers middleware.

Adds a standard set of HTTP security headers to every response.  These
headers defend against common web vulnerabilities (clickjacking, MIME
sniffing, XSS) and are expected by security scanners and compliance tools.

Headers applied:
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Content-Security-Policy: default-src 'self'
  - Permissions-Policy: geolocation=(), microphone=(), camera=()
  - Strict-Transport-Security (HSTS) — production only
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

settings = get_settings()

# Headers applied to every response regardless of environment.
_BASE_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# HSTS is only meaningful over HTTPS — enable in production only.
_HSTS_HEADER = "Strict-Transport-Security"
_HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers to every outgoing response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        for header, value in _BASE_HEADERS.items():
            response.headers[header] = value

        if settings.is_production:
            response.headers[_HSTS_HEADER] = _HSTS_VALUE

        return response
