# Deployment Guide

## Railway (Primary)

Railway is the primary deployment target for AXIOM ESTIMATE. The repository includes a `railway.toml` that configures the build and deploy pipeline automatically.

### Prerequisites

- Railway account with a project created
- Railway CLI installed (`npm install -g @railway/cli`) or use the Railway dashboard
- PostgreSQL plugin added to the Railway project (for production persistence)

### Steps

**1. Link the repository**

Connect your GitHub repository to the Railway project via the Railway dashboard or:

```bash
railway link
```

**2. Set environment variables**

In the Railway dashboard → Service → Variables, set:

```
APP_ENV=production
LOG_LEVEL=INFO
SERVICE_NAME=api-gateway
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=<automatically set by Railway PostgreSQL plugin>
CORS_ORIGINS=["https://axiomestimate.com"]
```

> **Never commit secrets to the repository.** Use Railway's variable management exclusively.

**3. Deploy**

Railway deploys automatically on every push to the configured branch. To trigger a manual deploy:

```bash
railway up
```

**4. Validate the deployment**

```bash
# Liveness — process is alive
curl https://<your-railway-domain>/health/live

# Readiness — app is ready and database is connected
curl https://<your-railway-domain>/health/ready

# Version info
curl https://<your-railway-domain>/
```

Expected `/health/ready` response:

```json
{
  "status": "ready",
  "service": "api-gateway",
  "version": "2.0.0",
  "uptime_seconds": 12.34,
  "timestamp": "2024-01-01T00:00:00+00:00",
  "checks": {
    "database": { "status": "ok", "backend": "postgresql" }
  }
}
```

### Railway Configuration (`railway.toml`)

| Setting | Value | Purpose |
|---------|-------|---------|
| `builder` | `dockerfile` | Use the repo's Dockerfile |
| `startCommand` | `uvicorn ... --workers 2` | 2 workers for Railway's single-instance plan |
| `healthcheckPath` | `/health/ready` | Railway polls this to confirm deployment success |
| `healthcheckTimeout` | `30` | Seconds before Railway marks the deploy as failed |
| `restartPolicyType` | `ON_FAILURE` | Auto-restart on crash |
| `restartPolicyMaxRetries` | `3` | Stop restart loop after 3 consecutive failures |

### Port Binding

Railway injects a `$PORT` environment variable. The `startCommand` in `railway.toml` uses `$PORT` directly. The Dockerfile `CMD` also respects `${PORT:-8000}` for local Docker runs.

---

## Docker Compose (Local Development)

```bash
# Start the full local stack
docker compose up --build

# Run with a specific environment
APP_ENV=staging docker compose up --build
```

The API is available at `http://localhost:8000`.

---

## Database Migrations

Migrations are managed with Alembic. Run them before starting the application in production.

```bash
# Apply all pending migrations
alembic upgrade head

# Check current migration state
alembic current

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Roll back one migration
alembic downgrade -1
```

On Railway, run migrations as a one-off command before deploying:

```bash
railway run alembic upgrade head
```

---

## Health Check Validation

| Endpoint | Expected Status | Purpose |
|----------|----------------|---------|
| `GET /health/live` | 200 | Process alive |
| `GET /health/ready` | 200 | App ready + DB connected |
| `GET /health/startup` | 200 | Boot complete |
| `GET /metrics` | 200 | Prometheus metrics |

A `degraded` status on `/health/ready` means the app is running but the database is unreachable. Check `DATABASE_URL` and network connectivity.

---

## Rollback Procedures

### Railway

Railway keeps a deployment history. To roll back:

1. Railway dashboard → Deployments → select a previous successful deployment → **Redeploy**

Or via CLI:

```bash
railway rollback
```

### Database Rollback

```bash
# Roll back the last migration
railway run alembic downgrade -1

# Roll back to a specific revision
railway run alembic downgrade <revision_id>
```

> Always take a database snapshot before rolling back migrations in production.

---

## Troubleshooting

### Service fails to start

1. Check Railway logs: `railway logs`
2. Verify all required environment variables are set (especially `JWT_SECRET_KEY` and `DATABASE_URL`)
3. Confirm the Docker build succeeds locally: `docker build -t axiom-test .`

### `/health/ready` returns 503 with `database: error`

1. Verify `DATABASE_URL` is correctly set in Railway variables
2. Check the PostgreSQL plugin is running in the Railway dashboard
3. Confirm the database has been migrated: `railway run alembic current`

### `JWT_SECRET_KEY` warning in logs

The application logs a warning if `JWT_SECRET_KEY` is set to the insecure default in production. Generate a secure key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Workers not starting

If `--workers 2` causes issues on Railway's free tier (memory limits), reduce to `--workers 1` in `railway.toml`.
