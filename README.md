# AXIOM ESTIMATE

Autonomous automotive damage-estimation platform for independent repair shops in Florida.

**Multi-agent AI pipeline** — damage vision, insurance claims, total-loss valuation, mechanic's lien, audit, CPO inspection, and GPU brokerage services — exposed through a single FastAPI gateway.

---

## Table of Contents

1. [What is this?](#what-is-this)
2. [Repository structure](#repository-structure)
3. [Local development](#local-development)
4. [Running tests](#running-tests)
5. [Docker](#docker)
6. [Railway](#railway)
7. [Kubernetes](#kubernetes)
8. [Terraform](#terraform)
9. [Deployment script](#deployment-script)
10. [MVP vs Roadmap](#mvp-vs-roadmap)

---

## What is this?

AXIOM ESTIMATE is a SaaS platform that automates the estimate-and-claims workflow for auto body shops. A shop submits photos of a damaged vehicle; AXIOM's AI offices process the images, cross-reference parts/pricing, validate insurance requirements, and return a structured repair estimate.

**Pricing model** — monthly subscription ($99/shop) plus per-job fees per AI office:

| Office | Service | Price |
|--------|---------|-------|
| 1 | AI Damage Estimator (vision) | $9/job |
| 2 | Insurance Claims | $13/job |
| 3 | Total Loss Actuary | $26/job |
| 4 | Mechanic's Lien Filing | $64/filing |
| 5 | Audit Chamber | $8/job |
| 6 | CPO Inspection | $17/job |
| 7 | GPU Brokerage | 70/30 revenue share |

---

## Repository structure

```
axiom-estimate/
├── app/                        # FastAPI application (api-gateway service)
│   ├── main.py                 # Application entry-point
│   ├── api/v1/
│   │   ├── health.py           # /health/live, /health/ready, /health/startup
│   │   └── estimates.py        # /api/v1/estimates
│   ├── core/
│   │   ├── config.py           # Settings from environment variables
│   │   └── health.py           # Readiness / liveness state
│   └── models/
│       └── estimate.py         # Pydantic request/response models
├── tests/                      # pytest test suite
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml          # Namespace, ServiceAccount, RBAC, Quotas
│   ├── configmaps/
│   ├── secrets/                # Placeholder + ExternalSecret (Secret Manager)
│   ├── deployments/            # api-gateway, office1, office2
│   ├── services/
│   ├── ingress/                # nginx + cert-manager ClusterIssuer
│   ├── hpa/                    # HorizontalPodAutoscaler
│   ├── cronjobs/               # Daily reporting agent
│   └── monitoring/             # ServiceMonitor, PrometheusRule, PDBs
├── terraform/
│   └── gke-autopilot.tf        # GKE Autopilot + Cloud SQL + Redis + Artifact Registry
├── scripts/
│   └── gke_deploy.sh           # End-to-end deployment script
├── .github/workflows/
│   └── ci.yml                  # Lint + test + Docker build CI
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Local development

### Prerequisites

- Python 3.11+
- (Optional) Docker Desktop

### Install and run

```bash
# Clone
git clone https://github.com/liorvys1981-sys/axiom-estimate.git
cd axiom-estimate

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the API
uvicorn app.main:app --reload --port 8000
```

The API is now available at <http://localhost:8000>.

Interactive docs: <http://localhost:8000/docs>

### Environment variables

All settings have safe defaults for local development. Copy `.env.example` (coming soon) or export variables directly:

```bash
export APP_ENV=development
export LOG_LEVEL=DEBUG
export JWT_SECRET_KEY=local-dev-secret-change-me
```

---

## Running tests

```bash
pytest tests/ -v
```

Expected output: 12 tests, all passing.

---

## Docker

### Build

```bash
docker build -t axiom-api-gateway:local .
```

### Run

```bash
docker run -p 8000:8000 \
  -e APP_ENV=development \
  -e JWT_SECRET_KEY=local-dev-secret \
  axiom-api-gateway:local
```

### Docker Compose (local stack)

```bash
docker compose up --build
```

The API gateway starts on port 8000 with live-reload volume-mounted source.

---

## Railway

This repository can be deployed directly on Railway using the included `Dockerfile`.

### Required variables

Set these variables in the Railway service:

```bash
APP_ENV=production
LOG_LEVEL=INFO
SERVICE_NAME=api-gateway
JWT_SECRET_KEY=replace-with-a-secure-random-secret
```

### Port binding

The container startup command supports Railway's dynamic `PORT` variable automatically and falls back to port `8000` for local Docker runs.

### Health check

After deployment, verify these endpoints:

- `/`
- `/docs`
- `/health/live`
- `/health/ready`

---

## Kubernetes

### Cluster assumptions

- GKE Autopilot (provisioned via Terraform)
- `axiom-production` namespace
- External Secrets Operator installed (for Secret Manager integration)
- nginx-ingress controller installed
- cert-manager installed

### Apply all manifests

```bash
# Namespace and RBAC first
kubectl apply -f k8s/namespace.yaml

# Config and secrets
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/

# Workloads
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/
kubectl apply -f k8s/ingress/
kubectl apply -f k8s/hpa/
kubectl apply -f k8s/cronjobs/

# Monitoring (requires Prometheus Operator)
kubectl apply -f k8s/monitoring/
```

### Key fixes from original drafts

| Issue | Fix |
|-------|-----|
| `RoleBinding.roleRef.apiRef` (invalid field) | Changed to `name` |
| `ServiceMonitor` selector used `app: axiom-estimate` (no match) | Updated to match actual service labels |
| PDB `pdb-offices-234567` used `component: office` (no match) | Split into per-service PDBs with correct labels |
| `0.0.0.0/0` in authorized networks | Removed; `gke_deploy.sh` requires explicit `AUTHORIZED_NETWORKS` |

---

## Terraform

```bash
cd terraform

# Bootstrap the state bucket first (once):
gcloud storage buckets create gs://axiom-terraform-state \
  --location=us-east1 --uniform-bucket-level-access

# Initialize and plan
terraform init
terraform plan -var="project_id=axiom-estimate-prod"

# Apply
terraform apply -var="project_id=axiom-estimate-prod"
```

> **Note:** `project_id` has no default to avoid accidental deploys. Always pass it explicitly or set `TF_VAR_project_id`.

Provisioned resources: GKE Autopilot cluster, Cloud SQL PostgreSQL 15, Memorystore Redis 7, Artifact Registry.

---

## Deployment script

```bash
export PROJECT_ID=axiom-estimate-prod
export AUTHORIZED_NETWORKS=203.0.113.10/32   # Your IP / VPN CIDR — NEVER 0.0.0.0/0
export IMAGE_TAG=v2.0.0

chmod +x scripts/gke_deploy.sh
./scripts/gke_deploy.sh
```

The script will:
1. Validate prerequisites (gcloud, kubectl, docker)
2. Authenticate Docker to Artifact Registry
3. Build and push the `api-gateway` image
4. Apply all Kubernetes manifests in dependency order
5. Wait for the `api-gateway` rollout to complete

---

## MVP vs Roadmap

### ✅ MVP (this PR)

- FastAPI api-gateway with health endpoints and `/api/v1/estimates`
- Kubernetes manifests for `api-gateway`, `office1-estimator`, `office2-insurance`
- HPA, PDB, Ingress, CronJob, ServiceMonitor
- GKE Autopilot Terraform (Cloud SQL + Redis + Artifact Registry)
- Sanitized deployment script (no `0.0.0.0/0`, parameterized)
- CI: lint + test + Docker build

### 🔜 Roadmap

- Persistent database layer (SQLAlchemy + Cloud SQL)
- Authentication/authorization (JWT, Stripe billing)
- Office services 3–7 (total-loss, lien, audit, CPO, GPU)
- Async job processing (Cloud Tasks or Pub/Sub)
- Frontend dashboard
- Canary deployment strategy
- Full observability stack (Grafana dashboards)
