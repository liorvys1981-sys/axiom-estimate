# Security Audit — AXIOM ESTIMATE API Gateway

**Audit Date:** 2024-01-01  
**Scope:** `app/` directory, `Dockerfile`, `docker-compose.yml`, `k8s/`, `requirements.txt`  
**Status:** MVP hardening complete — items marked 🔜 are roadmap items

---

## Summary

| Dimension | Finding | Severity | Status |
|-----------|---------|----------|--------|
| Secrets in repo | No hardcoded secrets found | ✅ Pass | Resolved |
| CORS | Wildcard `*` replaced with env-driven origins | 🟡 Medium | ✅ Fixed |
| Authentication | JWT configured, not yet enforced on endpoints | 🟡 Medium | 🔜 Roadmap |
| Container security | Non-root user, read-only FS in k8s | ✅ Pass | Resolved |
| Dependencies | No known critical CVEs at audit date | ✅ Pass | Monitor |
| Security headers | Added via `SecurityHeadersMiddleware` | 🟡 Medium | ✅ Fixed |
| Database | Parameterized queries via SQLAlchemy ORM | ✅ Pass | Resolved |
| Error handling | Stack traces hidden in production | 🟡 Medium | ✅ Fixed |
| Input validation | Pydantic models enforce all field constraints | ✅ Pass | Resolved |
| OpenAPI exposure | Schema disabled in production | 🟡 Medium | ✅ Fixed |

---

## Detailed Findings

### 1. Secrets in Repository

**Finding:** No hardcoded secrets, API keys, or credentials found in the codebase.

**Evidence:**
- `JWT_SECRET_KEY` defaults to `dev-insecure-change-me` — clearly marked as insecure
- `.gitignore` excludes `.env` and `.env.*` files
- `.env.example` contains only placeholder values
- `k8s/secrets/` uses Kubernetes ExternalSecret (Secret Manager integration) — no real values

**Recommendation:** Add a pre-commit hook or CI check (e.g., `detect-secrets`, `truffleHog`) to prevent accidental secret commits.

---

### 2. CORS Configuration

**Finding (Before):** `allow_origins=["*"]` was used unconditionally, allowing any origin to make credentialed requests.

**Fix Applied:** CORS origins are now driven by the `CORS_ORIGINS` environment variable. The `effective_cors_origins` property filters out localhost origins in production mode as a safety net.

```python
# Before
allow_origins=["*"] if not settings.is_production else ["https://axiomestimate.com"]

# After
allow_origins=settings.effective_cors_origins  # env-driven, validated
```

**Remaining Risk:** If `CORS_ORIGINS` is not set in production, the application falls back to `["https://axiomestimate.com"]`. Verify this domain is correct before go-live.

---

### 3. Authentication / Authorization

**Finding:** JWT configuration (`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`) is present but no endpoints enforce authentication. All API routes are publicly accessible.

**Risk:** Any unauthenticated client can submit estimates and read estimate data.

**Roadmap Fix:**
```python
# FastAPI dependency to enforce JWT on protected routes
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def require_auth(token = Depends(security)):
    # Validate JWT token
    ...
```

**Priority:** High — implement before accepting real customer data.

---

### 4. Container Security

**Finding:** Container security is well-configured.

**Evidence:**
- Dockerfile runs as `appuser` (UID 1000) — not root
- Multi-stage build minimizes the attack surface (no build tools in runtime image)
- Kubernetes manifests set `readOnlyRootFilesystem: true` and `allowPrivilegeEscalation: false`
- `securityContext.runAsNonRoot: true` enforced in k8s deployments

**Recommendation:** Add `--no-new-privileges` to Docker run flags for local development.

---

### 5. Dependency Vulnerabilities

**Finding:** No known critical CVEs in the current dependency set at audit date.

**Dependencies audited:**
- `fastapi==0.111.0` — no known CVEs
- `uvicorn==0.30.1` — no known CVEs
- `pydantic==2.7.1` — no known CVEs
- `sqlalchemy==2.0.31` — no known CVEs
- `psycopg2-binary==2.9.9` — no known CVEs

**Recommendation:** Add automated dependency scanning to CI:

```yaml
- name: Check for vulnerabilities
  run: pip install safety && safety check -r requirements.txt
```

---

### 6. Security Headers

**Finding (Before):** No security headers were set on responses.

**Fix Applied:** `SecurityHeadersMiddleware` adds the following headers to every response:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (production only) |

**Recommendation:** Run the response through [securityheaders.com](https://securityheaders.com) after deployment to verify.

---

### 7. Database Security

**Finding:** SQLAlchemy ORM is used exclusively — no raw SQL string interpolation found.

**Evidence:**
- All queries go through SQLAlchemy's parameterized query interface
- Pydantic models validate and sanitize all input before it reaches the database layer
- Database URL is injected via environment variable — not hardcoded

**Recommendation:**
- Enable SSL on the PostgreSQL connection: append `?sslmode=require` to `DATABASE_URL`
- Create a dedicated database user with minimal permissions (not the superuser)

---

### 8. Error Handling / Information Disclosure

**Finding (Before):** Unhandled exceptions could expose stack traces, file paths, and internal details to API clients.

**Fix Applied:** `ErrorHandlingMiddleware` catches all unhandled exceptions. In production, only a generic error message and request ID are returned. Full context (traceback, exception type) is logged server-side only.

---

### 9. Input Validation

**Finding:** All API inputs are validated by Pydantic models before reaching business logic.

**Validated fields:**
- `vehicle_vin`: exactly 17 characters (Pydantic `min_length=17, max_length=17`)
- `vehicle_year`: 1900–2100 (Pydantic `ge=1900, le=2100`)
- `vehicle_make`, `vehicle_model`: 1–64 characters
- `damage_description`: 1–2048 characters
- `photo_urls`: maximum 20 items

**Recommendation:** Add VIN checksum validation (the 9th character is a check digit) to catch obviously invalid VINs.

---

### 10. OpenAPI Schema Exposure

**Finding (Before):** The OpenAPI schema (`/openapi.json`, `/docs`, `/redoc`) was exposed in all environments, revealing the full API surface to potential attackers.

**Fix Applied:** `openapi_url` is set to `None` in production, disabling the schema endpoint. `/docs` and `/redoc` are also disabled as a consequence.

**Note:** If internal teams need API documentation in production, consider protecting `/docs` behind authentication rather than disabling it entirely.

---

## Recommendations Not Yet Implemented

| Item | Priority | Effort |
|------|----------|--------|
| Enforce JWT on all `/api/v1/*` endpoints | High | Medium |
| Add rate limiting (slowapi or nginx) | High | Low |
| VIN checksum validation | Medium | Low |
| Automated dependency scanning in CI | Medium | Low |
| PostgreSQL SSL enforcement | High | Low |
| Pre-commit secret scanning hook | Medium | Low |
| API key authentication for machine-to-machine | Medium | High |
