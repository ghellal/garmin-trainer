# These resources were created by scripts/bootstrap-wif.sh. Import them into
# Terraform state rather than attempting to create duplicate WIF resources.
import {
  to = google_iam_workload_identity_pool.github_actions
  id = "projects/${var.project_id}/locations/global/workloadIdentityPools/${var.wif_pool_id}"
}

import {
  to = google_iam_workload_identity_pool_provider.github
  id = "projects/${var.project_id}/locations/global/workloadIdentityPools/${var.wif_pool_id}/providers/${var.wif_provider_id}"
}

import {
  to = google_service_account.github_terraform
  id = "projects/${var.project_id}/serviceAccounts/${local.terraform_runner_email}"
}
