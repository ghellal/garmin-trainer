# Terraform infrastructure

Terraform provisions the Google Cloud resources for the MVP. The one-time WIF
pool/provider/service-account bootstrap is in `../scripts/bootstrap-wif.sh`;
the main configuration imports those existing resources into Terraform state.

## Prerequisites

- Terraform `>= 1.5.0` and Google Cloud CLI for local read-only diagnostics.
- The WIF bootstrap has already run. The project must contain the pool/provider
  IDs and `github-terraform` service account from that script.
- A billing-enabled project is required for the Firebase/Identity Platform
  configuration managed by this Terraform root.
- **Never run `terraform apply` locally.** Infrastructure apply and application
  deploys are performed only by the GitHub Actions `workflow_dispatch` pipeline.

## 1. Bootstrap the remote state bucket

The state bucket was created by the one-time bootstrap and is already used by
the main Terraform backend. Its bootstrap state remains local and ignored by
Git. Do not rerun the bootstrap apply locally.

```powershell
terraform -chdir=infra/bootstrap-state init
terraform -chdir=infra/bootstrap-state validate
```

Keep the bootstrap local state file safe and backed up. It is ignored by Git.

## Main infrastructure apply and deployment

```powershell
Copy-Item infra/terraform.tfvars.example infra/terraform.tfvars
Copy-Item infra/backend.hcl.example infra/backend.hcl
# Fill local config only if you need a read-only local plan.
terraform -chdir=infra init -backend-config=backend.hcl
terraform -chdir=infra plan
```

Use **Actions → Apply infrastructure and deploy → Run workflow** on `main`.
The workflow passes Terraform inputs through `TF_VAR_*` environment variables,
creates an ignored backend config, runs a plan and applies that saved plan,
builds the API image, and deploys the PWA.
The initial Cloud Run revision uses Google's public hello image until this
workflow replaces it. Firebase Hosting's `/api/**` rewrite requires a public
Cloud Run invoker binding, but FastAPI verifies a Firebase ID token and the
configured verified-email allowlist on every API route except `/healthz`.

The project ID, GitHub owner/repository, and allowlisted e-mail are configuration,
not secrets. The local `.tfvars` and backend config files are ignored by Git.
Never put Garmin or LLM secret values in Terraform variables/state. Terraform
creates Secret Manager containers only; secret payloads are added separately
and are not wired into the bootstrap revision yet.

Firebase Authentication uses email/password. A user can register, but the API
only authorizes the configured, verified `allowed_user_email`. The pipeline
expects `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SERVICE_ACCOUNT`,
`GCP_BILLING_ACCOUNT_ID`, and optionally `GCP_REGION`/`GCP_MONTHLY_BUDGET_USD`
as GitHub Actions variables; `ALLOWED_USER_EMAIL` must be a GitHub Actions
secret. The Firebase web config is read from Terraform outputs and is public
client configuration. Never store the Garmin or LLM credentials in GitHub.

If enabled, the default USD 6/month budget is a project-wide notification only,
not a spending cap. It covers all project usage, not compute alone.

## IAM and GitHub Actions status

WIF authenticates GitHub Actions as `github-terraform`. The workflow first
applies `infra/bootstrap-iam/`, which manages the runner's infrastructure
roles, then applies the main stack. The runner cannot grant itself its initial
permissions: an administrator must bootstrap `roles/resourcemanager.projectIamAdmin`
on this service account in the GCP console. This one-time role grant is not a
Terraform apply; it is required for the pipeline to grant/manage project roles.
If the project budget is enabled, the billing account administrator must also
grant `roles/billing.budgets.admin` to the service account on that billing
account.

The bootstrap stack grants `roles/serviceusage.serviceUsageAdmin`,
`roles/firebase.admin`, `roles/identitytoolkit.admin`, `roles/datastore.owner`,
`roles/secretmanager.admin`, `roles/iam.serviceAccountAdmin`,
`roles/artifactregistry.admin`, and `roles/run.admin`. Some of these roles allow
the pipeline identity to access Firestore data or Secret Manager values; treat
the WIF identity and protected workflow as highly privileged. Project IAM
Admin can grant other project roles, so scope it to this project, restrict WIF
to this repository and `main`, and require approval on the GitHub `production`
environment. Do not grant project Owner/Editor for convenience.

The GitHub WIF provider is restricted to this repository and the `main` branch.
`terraform-checks.yml` validates code without GCP credentials. The deployment
workflows are manual-only (`workflow_dispatch`): first run **Bootstrap Terraform
IAM**, then run **Apply infrastructure and deploy**. The latter applies the main
infrastructure plan, then deploys Cloud Run, Firebase Hosting, and deny-all
Firestore rules. No local apply is part of the process.
