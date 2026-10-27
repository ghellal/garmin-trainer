output "cloud_run_service_name" {
  description = "Initial Firebase-authenticated Cloud Run API service."
  value       = google_cloud_run_v2_service.api.name
}

output "cloud_run_service_url" {
  description = "Cloud Run URL; API routes enforce Firebase ID tokens and the email allowlist."
  value       = google_cloud_run_v2_service.api.uri
}

output "artifact_registry_repository" {
  description = "Docker repository for application images."
  value       = google_artifact_registry_repository.app.name
}

output "terraform_service_account_email" {
  description = "WIF service account used by GitHub Actions."
  value       = google_service_account.github_terraform.email
}

output "firebase_hosting_url" {
  description = "Firebase Hosting URL for the PWA."
  value       = google_firebase_hosting_site.pwa.default_url
}

output "firebase_web_app_config" {
  description = "Public Firebase client configuration for the PWA; not an API secret."
  value = {
    api_key     = data.google_firebase_web_app_config.pwa.api_key
    auth_domain = data.google_firebase_web_app_config.pwa.auth_domain
    project_id  = var.project_id
    app_id      = google_firebase_web_app.pwa.app_id
  }
}
