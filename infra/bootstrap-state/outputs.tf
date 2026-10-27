output "state_bucket_name" {
  description = "Use this bucket in infra/backend.hcl."
  value       = google_storage_bucket.terraform_state.name
}

output "backend_configuration" {
  description = "GCS backend values for the main infrastructure configuration."
  value = {
    bucket = google_storage_bucket.terraform_state.name
    prefix = "garmin-trainer"
  }
}
