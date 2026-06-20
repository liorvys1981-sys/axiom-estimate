# Operations Guide

## Monitoring and Alerting

### Health Endpoints

Poll these endpoints to verify service health:

| Endpoint | Healthy Response | Action on Failure |
|----------|-----------------|-------------------|
| `GET /health/live` | `{"status": "alive"}` | Container restart |
| `GET /health/ready` | `{"status": "ready", "checks": {"database": {"status": "ok"}}}` | Remove from load balancer |
| `GET /health/startup` | `{"status": "started"}` | Delay traffic routing |

### Prometheus Metrics

The `/metrics` endpoint exposes Prometheus-format metrics. Key metrics to alert on:

| Metric | Alert Condition | Severity |
|--------|----------------|----------|
| `http_requests_total{status_code="5xx"}` | Rate > 1% of total requests | Critical |
| `http_request_duration_seconds{quantile="0.99"}` | > 2 seconds | Warning |
| `db_pool_connections{state="overflow"}` | > 5 | Warning |
| `estimates_created_total` | Rate drops to 0 during business hours | Warning |

### Railway Observability

Railway provides built-in metrics (CPU, memory, network) in the dashboard. For application-level metrics, connect a Prometheus instance to the `/metrics` endpoint.

### Log Aggregation

In production, logs are emitted as JSON (via `python-json-logger`). Key log fields:

| Field | Description |
|-------|-------------|
| `request_id` | Unique ID for distributed tracing |
| `method` | HTTP method |
| `path` | Request path |
| `status_code` | HTTP response status |
| `duration_ms` | Request duration in milliseconds |
| `client_ip` | Client IP address |

Filter for errors: `level:ERROR OR level:CRITICAL`

---

## Backup and Restore

### PostgreSQL Backups (Railway)

Railway PostgreSQL plugin includes automated daily backups with a 7-day retention window. Access backups via the Railway dashboard → PostgreSQL plugin → Backups.

### Manual Backup

```bash
# Dump the production database
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress for storage
gzip backup_*.sql
```

### Restore from Backup

```bash
# Restore to a target database
psql $TARGET_DATABASE_URL < backup_20240101_120000.sql
```

> Always test restores in a staging environment before relying on them for production recovery.

### Backup Verification

Run a monthly restore drill:
1. Create a staging database
2. Restore the latest production backup
3. Run the test suite against the restored database
4. Verify row counts match production

---

## Database Migration Procedures

### Pre-Migration Checklist

- [ ] Take a database snapshot (Railway dashboard → PostgreSQL → Backups → Create backup)
- [ ] Review the migration script for destructive operations (DROP, TRUNCATE, column removal)
- [ ] Test the migration on a staging database first
- [ ] Confirm the migration is reversible (`alembic downgrade -1` works)
- [ ] Schedule during low-traffic window if the migration locks tables

### Applying Migrations

```bash
# Check current state
railway run alembic current

# Preview what will run (dry run)
railway run alembic upgrade head --sql

# Apply migrations
railway run alembic upgrade head

# Verify
railway run alembic current
```

### Rolling Back Migrations

```bash
# Roll back one step
railway run alembic downgrade -1

# Roll back to a specific revision
railway run alembic downgrade 001

# Roll back all migrations (destructive — use with caution)
railway run alembic downgrade base
```

### Zero-Downtime Migration Strategy

For large tables or column changes that would lock the table:

1. Add new column as nullable (no lock)
2. Backfill data in batches
3. Add NOT NULL constraint after backfill
4. Deploy application code that uses the new column
5. Drop the old column in a subsequent migration

---

## Scaling Guidelines

### Vertical Scaling (Railway)

Increase the Railway service's memory and CPU allocation in the dashboard. The application uses 2 uvicorn workers by default — each worker handles requests independently.

### Horizontal Scaling

The application is stateless (no in-memory session state). Multiple Railway instances can run behind the load balancer without coordination.

**Connection pool sizing:** With N instances and 2 workers each, the database will see up to `N × 2 × (pool_size + max_overflow)` = `N × 2 × 15` connections. Ensure the PostgreSQL `max_connections` setting accommodates this.

### Worker Tuning

Adjust workers in `railway.toml`:

```toml
[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4"
```

Rule of thumb: `workers = (2 × CPU cores) + 1`. Railway's starter plan has 1 vCPU, so 2–3 workers is appropriate.

---

## Troubleshooting

### Top 10 Boot Failure Causes

1. **Missing `DATABASE_URL`** — The application starts but `/health/ready` returns `degraded`. Set `DATABASE_URL` in Railway variables.

2. **Invalid `DATABASE_URL` format** — SQLAlchemy raises `ArgumentError` at startup. Verify the URL scheme (`postgresql://` not `postgres://` for SQLAlchemy 2.x — use `postgresql+psycopg2://`).

3. **Database not migrated** — Tables don't exist, causing 500 errors on first request. Run `alembic upgrade head` before deploying.

4. **`JWT_SECRET_KEY` is the insecure default** — A warning is logged in production. Not a boot failure, but a security risk. Rotate immediately.

5. **Port binding failure** — Railway injects `$PORT`; if the start command hardcodes `8000`, the health check fails. The `railway.toml` `startCommand` uses `$PORT` correctly.

6. **`APP_ENV` set to an invalid value** — The `validate_app_env` validator raises a `ValidationError` at startup. Valid values: `development`, `staging`, `production`.

7. **`LOG_LEVEL` set to an invalid value** — Same as above. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

8. **Python dependency conflict** — A `pip install` failure during Docker build. Check `requirements.txt` for version conflicts and rebuild locally.

9. **Non-root user permission error** — If a volume mount or file path requires root access, the `appuser` (UID 1000) will get a `PermissionError`. Ensure writable paths are explicitly mounted.

10. **CORS misconfiguration** — The application starts but browser clients get CORS errors. Verify `CORS_ORIGINS` includes the exact frontend origin (scheme + domain + port).

### Checking Logs

```bash
# Stream live logs
railway logs --tail

# Filter for errors
railway logs | grep '"level":"ERROR"'
```

### Restarting the Service

```bash
# Trigger a redeploy (picks up latest image)
railway up

# Or restart without rebuilding (Railway dashboard → Service → Restart)
```

### Database Connection Issues

```bash
# Test connectivity from Railway environment
railway run python -c "
from app.db.session import check_database_connection
import json
print(json.dumps(check_database_connection(), indent=2))
"
```
