locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "firebase.googleapis.com",
    "firebasehosting.googleapis.com",
    "firebaserules.googleapis.com",
    "firestore.googleapis.com",
    "identitytoolkit.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "serviceusage.googleapis.com",
    "sts.googleapis.com",
  ])

  terraform_runner_email = "${var.terraform_service_account_id}@${var.project_id}.iam.gserviceaccount.com"
  github_repository      = "${var.github_owner}/${var.github_repo}"
  github_principal_set   = "principalSet://iam.googleapis.com/projects/${google_firebase_project.default.project_number}/locations/global/workloadIdentityPools/${var.wif_pool_id}/attribute.repository/${local.github_repository}"
}

resource "google_project_service" "required" {
  for_each = local.required_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_billing_budget" "project" {
  count = var.billing_account_id == "" ? 0 : 1

  billing_account = var.billing_account_id
  display_name    = "Garmin Trainer monthly GCP budget"

  budget_filter {
    projects        = ["projects/${google_firebase_project.default.project_number}"]
    calendar_period = "MONTH"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }

  threshold_rules {
    threshold_percent = 0.8
  }

  threshold_rules {
    threshold_percent = 1.0
  }

  depends_on = [google_project_service.required]
}

resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.required]
}

resource "google_firebase_web_app" "pwa" {
  provider     = google-beta
  project      = google_firebase_project.default.project
  display_name = "Garmin Trainer PWA"

  lifecycle {
    prevent_destroy = true
  }
}

data "google_firebase_web_app_config" "pwa" {
  provider   = google-beta
  project    = var.project_id
  web_app_id = google_firebase_web_app.pwa.app_id
}

resource "google_firebase_hosting_site" "pwa" {
  provider = google-beta
  project  = google_firebase_project.default.project
  site_id  = var.project_id
  app_id   = google_firebase_web_app.pwa.app_id

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_identity_platform_config" "auth" {
  project = var.project_id

  sign_in {
    allow_duplicate_emails = false

    email {
      enabled           = true
      password_required = true
    }
  }

  authorized_domains = [
    "localhost",
    "${var.project_id}.firebaseapp.com",
    "${var.project_id}.web.app",
  ]

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [
    google_firebase_project.default,
    google_project_service.required,
  ]
}

resource "google_iam_workload_identity_pool" "github_actions" {
  project                   = var.project_id
  workload_identity_pool_id = var.wif_pool_id
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
  workload_identity_pool_provider_id = var.wif_provider_id
  display_name                       = "GitHub repository provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  attribute_condition = "assertion.repository == '${local.github_repository}' && assertion.ref == 'refs/heads/${var.github_deploy_branch}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "github_terraform" {
  project      = var.project_id
  account_id   = var.terraform_service_account_id
  display_name = "GitHub Actions Terraform"
}

# Preserve the bootstrap binding that lets this repository impersonate the
# Terraform service account. It grants identity federation only, not GCP roles.
resource "google_service_account_iam_member" "github_workload_identity_user" {
  service_account_id = google_service_account.github_terraform.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.github_principal_set
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = "garmin-trainer-runtime"
  display_name = "Garmin Trainer Cloud Run runtime"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "runtime_firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runtime.email}"

  depends_on = [google_project_service.required]
}

# GitHub Actions deploys application artifacts only. Terraform infrastructure
# changes remain reviewed and applied separately; no project Owner/Editor role.
resource "google_project_iam_member" "github_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${local.terraform_runner_email}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "github_firebase_hosting_admin" {
  project = var.project_id
  role    = "roles/firebasehosting.admin"
  member  = "serviceAccount:${local.terraform_runner_email}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "github_firebase_rules_admin" {
  project = var.project_id
  role    = "roles/firebaserules.admin"
  member  = "serviceAccount:${local.terraform_runner_email}"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "github_service_usage_consumer" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${local.terraform_runner_email}"

  depends_on = [google_project_service.required]
}

resource "google_artifact_registry_repository" "app" {
  project       = var.project_id
  location      = var.region
  repository_id = "garmin-trainer"
  description   = "Container images for Garmin Trainer"
  format        = "DOCKER"

  depends_on = [google_project_service.required]
}

resource "google_artifact_registry_repository_iam_member" "github_image_writer" {
  project    = var.project_id
  location   = google_artifact_registry_repository.app.location
  repository = google_artifact_registry_repository.app.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${local.terraform_runner_email}"
}

resource "google_firestore_database" "default" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "garmin_personal_api_key" {
  project   = var.project_id
  secret_id = "garmin-personal-api-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "llm_api_key" {
  project   = var.project_id
  secret_id = "llm-api-key"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "runtime_garmin_secret_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.garmin_personal_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_llm_secret_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.llm_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

# IAM-authenticated bootstrap service. The public Google hello image is
# temporary until the FastAPI application image is built.
resource "google_cloud_run_v2_service" "api" {
  project  = var.project_id
  name     = var.cloud_run_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.runtime.email
    max_instance_request_concurrency = 80
    timeout                          = "60s"

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = var.container_image

      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "ALLOWED_USER_EMAIL"
        value = var.allowed_user_email
      }

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        value = "https://${var.project_id}.web.app,https://${var.project_id}.firebaseapp.com,http://localhost:5173"
      }

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_artifact_registry_repository.app,
    google_project_iam_member.runtime_firestore_user,
  ]

  # GitHub Actions releases immutable image tags. Terraform manages the service
  # configuration while the deployment workflow owns the currently running image.
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

# Firebase Hosting forwards /api/** to Cloud Run. The service must accept the
# hosting proxy invocation; the FastAPI app still requires a verified Firebase
# ID token and an exact email allowlist for every non-health endpoint.
resource "google_cloud_run_v2_service_iam_member" "firebase_hosting_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_service_account_iam_member" "github_runtime_service_account_user" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.terraform_runner_email}"
}
