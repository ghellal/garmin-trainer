locals {
  state_bucket_name = "${var.project_id}-tfstate"
  terraform_runner  = "${var.terraform_service_account_id}@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_service" "storage_api" {
  project            = var.project_id
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_storage_bucket" "terraform_state" {
  project                     = var.project_id
  name                        = local.state_bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  depends_on = [google_project_service.storage_api]
}

# The WIF identity can read/write Terraform state, but receives no project-wide
# infrastructure permissions here. Those will be granted separately by Terraform.
resource "google_storage_bucket_iam_member" "terraform_state_objects" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.terraform_runner}"
}

resource "google_storage_bucket_iam_member" "terraform_state_bucket_metadata" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.bucketViewer"
  member = "serviceAccount:${local.terraform_runner}"
}
