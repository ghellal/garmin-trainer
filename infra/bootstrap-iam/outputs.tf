output "terraform_runner_email" {
  description = "WIF service account receiving the infrastructure roles."
  value       = "${var.terraform_service_account_id}@${var.project_id}.iam.gserviceaccount.com"
}

output "provisioner_roles" {
  description = "Project-level roles granted to the Terraform runner."
  value       = sort(tolist(local.provisioner_roles))
}
