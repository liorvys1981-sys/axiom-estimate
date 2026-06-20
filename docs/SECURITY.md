# Security Guide

## Secret Management

### Principles

- **No secrets in the repository.** Environment variables, `.env` files, and hardcoded credentials must never be committed. The `.gitignore` excludes `.env` and `.env.*` files.
- **Rotate secrets regularly.** JWT keys and database passwords should be rotated at least quarterly.
- **Least privilege.** Database users should have only the permissions required (SELECT, INSERT, UPDATE, DELETE on application tables — not CREATE, DROP, or superuser).

### Generating Secrets

```bash
# JWT secret key (256-bit, hex-encoded)
python -c "import secrets; print(secrets.token_hex(32))"

# Alternative using OpenSSL
openssl rand -hex 32
```

### Railway Secret Management

Store all secrets in Railway's variable management (dashboard → Service → Variables). Railway encrypts variables at rest and injects them as environment variables at runtime.

**Required secrets for production:**

| Variable | Description |
|----------|-------------|
| `JWT_SECRET_KEY` | Cryptographically random 32+ byte hex string |
| `DATABASE_URL` | PostgreSQL connection string (set automatically by Railway PostgreSQL plugin) |

**Never use the default `dev-insecure-change-me` value in production.** The application will log a warning if it detects this.

---

## CORS Configuration

CORS is configured via the `CORS_ORIGINS` environment variable.

### Development

```
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### Production

```
CORS_ORIGINS=["https://axiomestimate.com"]
```

The application's `effective_cors_origins` property automatically filters out localhost origins in production mode, providing a safety net even if the variable is misconfigured.

**Never use `allow_origins=["*"]` in production.** Wildcard CORS allows any website to make authenticated requests on behalf of your users.

---

## Security Headers

The `SecurityHeadersMiddleware` adds the following headers to every response:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Content-Security-Policy` | `default-src 'self'` | Restrict resource loading |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Disable browser APIs |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS (production only) |

---

## Authentication and Authorization

### Current State (MVP)

JWT authentication is configured but not yet enforced on API endpoints. The `JWT_SECRET_KEY` setting is present and validated.

### Roadmap

- Enforce JWT validation on all `/api/v1/*` endpoints via a FastAPI dependency
- Implement per-shop API keys for machine-to-machine access
- Add Stripe billing integration to gate access by subscription status
- Role-based access control (shop owner vs. technician vs. admin)

### JWT Best Practices

- Use short expiry times (`JWT_EXPIRE_MINUTES=60` is the default)
- Implement token refresh flows rather than long-lived tokens
- Store tokens in `httpOnly` cookies (not `localStorage`) in browser clients
- Validate `iss`, `aud`, and `exp` claims on every request

---

## Container Security

### Non-Root User

The Dockerfile creates and runs as `appuser` (UID 1000). This limits the blast radius of a container escape.

### Read-Only Filesystem

The Kubernetes manifests configure `readOnlyRootFilesystem: true` with explicit writable volume mounts for temporary files. This prevents an attacker from modifying application code at runtime.

### Image Scanning

Integrate container image scanning into CI:

```yaml
# .github/workflows/ci.yml addition
- name: Scan image for vulnerabilities
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: axiom-api-gateway:${{ github.sha }}
    severity: HIGH,CRITICAL
    exit-code: 1
```

---

## Data Protection

### Sensitive Fields

- Vehicle VINs are personally identifiable in some jurisdictions — treat as PII
- Client IDs map to real businesses — protect against enumeration
- Photo URLs may contain sensitive damage imagery — use signed URLs with expiry

### Database Security

- Use parameterized queries exclusively (SQLAlchemy ORM enforces this)
- Never interpolate user input into SQL strings
- Enable PostgreSQL SSL (`?sslmode=require` in `DATABASE_URL`)
- Restrict database network access to the application service only

### Input Validation

All API inputs are validated by Pydantic models before reaching business logic:
- VIN: exactly 17 characters
- Year: 1900–2100
- Make/model: 1–64 characters
- Damage description: 1–2048 characters
- Photo URLs: maximum 20 items

---

## Incident Response

### Suspected Secret Compromise

1. **Immediately rotate** the compromised secret in Railway variables
2. **Invalidate all active sessions** (rotate `JWT_SECRET_KEY` — this invalidates all existing tokens)
3. **Review logs** for unauthorized access patterns
4. **Notify affected parties** if customer data was accessed

### Suspected Data Breach

1. Isolate the affected service (Railway dashboard → Service → pause)
2. Preserve logs for forensic analysis
3. Identify the scope of data accessed
4. Follow applicable breach notification requirements (GDPR, CCPA, etc.)
5. Conduct a post-mortem and implement preventive controls

### Security Vulnerability Reporting

Report security vulnerabilities privately to the engineering team. Do not open public GitHub issues for security findings.
