# ─── Build arguments ──────────────────────────────────────────────────────────
ARG PYTHON_VERSION=3.11
ARG APP_VERSION=2.0.0

# ─── Build stage ──────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /build

# Install dependencies into an isolated prefix
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:${PYTHON_VERSION}-slim

# Image metadata
LABEL maintainer="axiom-team"
LABEL version="${APP_VERSION}"
LABEL description="AXIOM ESTIMATE API Gateway - Autonomous automotive damage estimation"
LABEL org.opencontainers.image.source="https://github.com/liorvys1981-sys/axiom-estimate"
LABEL org.opencontainers.image.licenses="Proprietary"

# Non-root user (matches securityContext in k8s manifests)
RUN useradd --uid 1000 --create-home appuser

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

USER appuser

EXPOSE 8000

# Health probe available at startup
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD sh -c "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health/live')\""

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
