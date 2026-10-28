locals {
  terraform_runner_email = "${var.terraform_service_account_id}@${var.project_id}.iam.gserviceaccount.com"

  provisioner_roles = toset([
    "roles/artifactregistry.admin",
    "roles/datastore.owner",
    "roles/firebase.admin",
    "roles/iam.serviceAccountAdmin",
    "roles/identitytoolkit.admin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/serviceusage.serviceUsageAdmin",
  ])
}

# This bootstrap grants the WIF runner the project permissions needed by the
# main Terraform root. Project IAM Admin must be granted once by an authorized
# project administrator before this pipeline can apply these bindings.
resource "google_project_iam_member" "terraform_provisioner" {
  for_each = local.provisioner_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${local.terraform_runner_email}"
}
