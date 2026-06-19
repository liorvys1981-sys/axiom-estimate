# terraform/gke-autopilot.tf
# AXIOM ESTIMATE — GKE Autopilot Infrastructure
#
# Prerequisites / Bootstrap notes
# ────────────────────────────────
# 1. The GCS backend bucket ("axiom-terraform-state") must exist BEFORE running
#    `terraform init`.  Create it once manually:
#      gcloud storage buckets create gs://axiom-terraform-state \
#        --location=us-east1 --uniform-bucket-level-access
#
# 2. Enable required APIs on the project:
#      gcloud services enable container.googleapis.com \
#        sqladmin.googleapis.com redis.googleapis.com \
#        secretmanager.googleapis.com artifactregistry.googleapis.com \
#        servicenetworking.googleapis.com --project=<PROJECT_ID>
#
# 3. Private Service Connect for Cloud SQL requires a VPC peering range.
#    The "default" network is used here for simplicity; for production consider
#    a dedicated VPC.

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "axiom-terraform-state"
    prefix = "axiom/production"
  }
}

# ── Variables ────────────────────────────────────────────────────────────────

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
  # Override via: terraform apply -var='project_id=my-project'
  # or export TF_VAR_project_id=my-project
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-east1"
}

variable "cluster_name" {
  description = "GKE Cluster name"
  type        = string
  default     = "axiom-autopilot-prod"
}

variable "db_tier" {
  description = "Cloud SQL machine tier"
  type        = string
  default     = "db-g1-small"
}

variable "redis_memory_gb" {
  description = "Memorystore Redis memory in GB"
  type        = number
  default     = 1
}

# ── Providers ────────────────────────────────────────────────────────────────

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ── GKE Autopilot Cluster ────────────────────────────────────────────────────

resource "google_container_cluster" "axiom_autopilot" {
  provider = google-beta

  name     = var.cluster_name
  location = var.region

  enable_autopilot = true

  release_channel {
    channel = "STABLE"
  }

  network    = "default"
  subnetwork = "default"

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  security_posture_config {
    mode               = "BASIC"
    vulnerability_mode = "VULNERABILITY_BASIC"
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
    managed_prometheus {
      enabled = true
    }
  }

  resource_labels = {
    env     = "production"
    app     = "axiom-estimate"
    managed = "terraform"
  }

  deletion_protection = true
}

# ── Service Account for GKE pods ─────────────────────────────────────────────

resource "google_service_account" "axiom_gke_sa" {
  account_id   = "axiom-gke-sa"
  display_name = "AXIOM GKE Service Account"
  description  = "SA for AXIOM pods — access to Secret Manager via Workload Identity"
}

resource "google_service_account_iam_binding" "workload_identity" {
  service_account_id = google_service_account.axiom_gke_sa.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[axiom-production/axiom-service-account]"
  ]
}

resource "google_project_iam_member" "secret_manager_access" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.axiom_gke_sa.email}"
}

# ── Cloud SQL PostgreSQL ──────────────────────────────────────────────────────

resource "google_sql_database_instance" "axiom_postgres" {
  name             = "axiom-postgres-prod"
  database_version = "POSTGRES_15"
  region           = var.region

  deletion_protection = true

  settings {
    tier              = var.db_tier
    availability_type = "REGIONAL"

    disk_config {
      disk_type       = "PD_SSD"
      disk_size       = 20
      disk_autoresize = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = true
      backup_retention_settings {
        retained_backups = 30
      }
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = "projects/${var.project_id}/global/networks/default"
    }

    database_flags {
      name  = "max_connections"
      value = "200"
    }

    insights_config {
      query_insights_enabled = true
      query_plans_per_minute = 5
    }

    user_labels = {
      env = "production"
      app = "axiom-estimate"
    }
  }
}

resource "google_sql_database" "axiom_db" {
  name     = "axiom_production"
  instance = google_sql_database_instance.axiom_postgres.name
}

# ── Memorystore Redis ─────────────────────────────────────────────────────────

resource "google_redis_instance" "axiom_redis" {
  name           = "axiom-redis-prod"
  tier           = "STANDARD_HA"
  memory_size_gb = var.redis_memory_gb
  region         = var.region
  redis_version  = "REDIS_7_0"

  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  labels = {
    env = "production"
    app = "axiom-estimate"
  }
}

# ── Artifact Registry ─────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "axiom_registry" {
  location      = var.region
  repository_id = "axiom"
  format        = "DOCKER"
  description   = "AXIOM ESTIMATE Docker images"

  labels = {
    env = "production"
  }
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "cluster_name" {
  value       = google_container_cluster.axiom_autopilot.name
  description = "GKE Cluster name"
}

output "cluster_endpoint" {
  value       = google_container_cluster.axiom_autopilot.endpoint
  sensitive   = true
  description = "GKE Cluster endpoint (sensitive)"
}

output "sql_connection_name" {
  value       = google_sql_database_instance.axiom_postgres.connection_name
  description = "Cloud SQL connection name for Cloud SQL Auth Proxy"
}

output "redis_host" {
  value       = google_redis_instance.axiom_redis.host
  sensitive   = true
  description = "Memorystore Redis host"
}

output "registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/axiom"
  description = "Artifact Registry base URL for Docker images"
}
