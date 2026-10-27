variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Primary GCP region for application resources."
  type        = string
  default     = "europe-west1"
}

variable "github_owner" {
  description = "GitHub account or organization configured in the WIF provider."
  type        = string
}

variable "github_repo" {
  description = "GitHub repository configured in the WIF provider."
  type        = string
  default     = "garmin-trainer"
}

variable "github_deploy_branch" {
  description = "Branch allowed by the existing WIF provider condition."
  type        = string
  default     = "main"
}

variable "wif_pool_id" {
  description = "Existing Workload Identity Pool ID created by the bootstrap script."
  type        = string
  default     = "github-actions"
}

variable "wif_provider_id" {
  description = "Existing OIDC provider ID created by the bootstrap script."
  type        = string
  default     = "github"
}

variable "terraform_service_account_id" {
  description = "Existing WIF service account ID created by the bootstrap script."
  type        = string
  default     = "github-terraform"
}

variable "cloud_run_service_name" {
  description = "Initial Firebase-authenticated Cloud Run service name."
  type        = string
  default     = "garmin-trainer-api"
}

variable "container_image" {
  description = "Temporary public image until the application container is implemented."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "allowed_user_email" {
  description = "The single verified Firebase Auth email allowed to use the API."
  type        = string

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.allowed_user_email))
    error_message = "allowed_user_email must be a valid email address."
  }
}

variable "billing_account_id" {
  description = "Optional billing account ID for the project budget alert. Leave empty to defer budget creation."
  type        = string
  default     = ""
}

variable "monthly_budget_usd" {
  description = "GCP project-wide monthly budget threshold in USD; notifications only, not a spending cap."
  type        = number
  default     = 6

  validation {
    condition     = var.monthly_budget_usd > 0 && floor(var.monthly_budget_usd) == var.monthly_budget_usd
    error_message = "monthly_budget_usd must be a positive whole-dollar amount."
  }
}
