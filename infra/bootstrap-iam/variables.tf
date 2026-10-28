variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "terraform_service_account_id" {
  description = "WIF service account ID created by the WIF bootstrap."
  type        = string
  default     = "github-terraform"
}
