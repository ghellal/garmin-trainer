variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for the Terraform state bucket."
  type        = string
  default     = "europe-west1"
}

variable "terraform_service_account_id" {
  description = "The WIF service account created by scripts/bootstrap-wif.sh."
  type        = string
  default     = "github-terraform"
}
