#!/bin/bash
# scripts/gke_deploy.sh
# AXIOM ESTIMATE — GKE Autopilot Deployment Script
# Version: 2.1.0
#
# Prerequisites (manual — run once before this script):
#   1. gcloud CLI authenticated: gcloud auth login && gcloud auth configure-docker
#   2. kubectl configured: gcloud container clusters get-credentials <CLUSTER> --region <REGION>
#   3. Terraform-provisioned infrastructure (terraform/gke-autopilot.tf)
#   4. GCP secrets created in Secret Manager (axiom-database-url, axiom-jwt-secret, etc.)
#   5. Docker images built and pushed to Artifact Registry
#
# Usage:
#   export PROJECT_ID=my-gcp-project
#   export AUTHORIZED_NETWORKS=203.0.113.0/24   # Your corporate/VPN CIDR
#   ./scripts/gke_deploy.sh

set -euo pipefail
IFS=$'\n\t'

# ── Configuration (override via environment variables) ─────────────────────
PROJECT_ID="${PROJECT_ID:-axiom-estimate-prod}"
REGION="${REGION:-us-east1}"
CLUSTER_NAME="${CLUSTER_NAME:-axiom-autopilot-prod}"
NAMESPACE="${NAMESPACE:-axiom-production}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-${REGION}-docker.pkg.dev/${PROJECT_ID}/axiom}"

# SECURITY: Restrict to your VPN/corporate IP range.
# Do NOT use 0.0.0.0/0 — that allows the entire internet to reach the control plane.
AUTHORIZED_NETWORKS="${AUTHORIZED_NETWORKS:-}"

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_success() { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Helpers ────────────────────────────────────────────────────────────────
require_tool() {
  if ! command -v "$1" &>/dev/null; then
    log_error "Required tool '$1' not found. Please install it."
    exit 1
  fi
}

check_prerequisites() {
  log_info "Checking prerequisites..."
  require_tool gcloud
  require_tool kubectl
  require_tool docker

  if [[ -z "${AUTHORIZED_NETWORKS}" ]]; then
    log_error "AUTHORIZED_NETWORKS is not set."
    log_error "Set it to your corporate/VPN CIDR, e.g.: export AUTHORIZED_NETWORKS=203.0.113.0/24"
    log_error "Never use 0.0.0.0/0 — it exposes the GKE control plane to the entire internet."
    exit 1
  fi

  gcloud auth print-access-token &>/dev/null || {
    log_error "Not authenticated with gcloud. Run: gcloud auth login"
    exit 1
  }
  log_success "Prerequisites OK"
}

# ── Cluster connectivity ───────────────────────────────────────────────────
configure_kubectl() {
  log_info "Fetching kubeconfig for cluster ${CLUSTER_NAME}..."
  gcloud container clusters get-credentials "${CLUSTER_NAME}" \
    --region "${REGION}" \
    --project "${PROJECT_ID}"
  log_success "kubectl configured"
}

# ── Artifact Registry ──────────────────────────────────────────────────────
configure_registry() {
  log_info "Authenticating Docker to Artifact Registry..."
  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
  log_success "Docker authenticated"
}

ensure_registry_exists() {
  log_info "Checking Artifact Registry repository..."
  if ! gcloud artifacts repositories describe axiom \
      --location="${REGION}" --project="${PROJECT_ID}" &>/dev/null; then
    log_info "Creating Artifact Registry repository 'axiom'..."
    gcloud artifacts repositories create axiom \
      --repository-format=docker \
      --location="${REGION}" \
      --project="${PROJECT_ID}" \
      --description="AXIOM ESTIMATE Docker images"
    log_success "Registry created"
  else
    log_success "Registry already exists"
  fi
}

# ── Docker build & push ────────────────────────────────────────────────────
build_and_push() {
  local service="$1"
  local dockerfile="${2:-Dockerfile}"
  local context="${3:-.}"
  local image="${REGISTRY}/${service}:${IMAGE_TAG}"

  log_info "Building ${service} → ${image}"
  docker build -f "${dockerfile}" -t "${image}" "${context}"
  docker push "${image}"
  log_success "${service} pushed"
}

build_images() {
  log_info "Building and pushing Docker images..."
  build_and_push "api-gateway" "Dockerfile" "."
  # Add additional services here once they have their own Dockerfiles:
  # build_and_push "office1-estimator" "services/office1/Dockerfile" "services/office1"
  # build_and_push "office2-insurance"  "services/office2/Dockerfile" "services/office2"
  log_success "All images pushed"
}

# ── Kubernetes manifests ───────────────────────────────────────────────────
apply_manifests() {
  log_info "Applying Kubernetes manifests..."

  # Order matters: namespace first, then config, then workloads
  kubectl apply -f k8s/namespace.yaml
  kubectl apply -f k8s/configmaps/
  kubectl apply -f k8s/secrets/
  kubectl apply -f k8s/deployments/
  kubectl apply -f k8s/services/
  kubectl apply -f k8s/ingress/
  kubectl apply -f k8s/hpa/
  kubectl apply -f k8s/cronjobs/
  kubectl apply -f k8s/monitoring/ || log_warn "Monitoring manifests failed (Prometheus Operator may not be installed)"

  log_success "Manifests applied"
}

# ── Rollout verification ───────────────────────────────────────────────────
verify_rollout() {
  log_info "Waiting for api-gateway rollout..."
  kubectl rollout status deployment/api-gateway -n "${NAMESPACE}" --timeout=300s
  log_success "api-gateway rollout complete"

  log_info "Pod status:"
  kubectl get pods -n "${NAMESPACE}"
}

# ── Main ───────────────────────────────────────────────────────────────────
main() {
  echo ""
  echo -e "${BLUE}════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}  AXIOM ESTIMATE — GKE Autopilot Deployment     ${NC}"
  echo -e "${BLUE}  Project : ${PROJECT_ID}                       ${NC}"
  echo -e "${BLUE}  Region  : ${REGION}                           ${NC}"
  echo -e "${BLUE}  Tag     : ${IMAGE_TAG}                        ${NC}"
  echo -e "${BLUE}════════════════════════════════════════════════${NC}"
  echo ""

  check_prerequisites
  configure_registry
  ensure_registry_exists
  configure_kubectl
  build_images
  apply_manifests
  verify_rollout

  echo ""
  log_success "Deployment complete ✓"
  echo ""
  echo "  API docs  : https://api.axiomestimate.com/docs"
  echo "  Health    : https://api.axiomestimate.com/health/ready"
  echo ""
}

main "$@"
