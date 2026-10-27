# Terraform infrastructure

Terraform provisions the Google Cloud resources for the MVP. The one-time WIF
pool/provider/service-account bootstrap is in `../scripts/bootstrap-wif.sh`;
the main configuration imports those existing resources into Terraform state.

## Prerequisites

- Terraform `>= 1.5.0` and Google Cloud CLI.
- The WIF bootstrap has already run. The project must contain the pool/provider
  IDs and `github-terraform` service account from that script.
- A billing-enabled project is required for the Firebase/Identity Platform
  configuration managed by this Terraform root.
- For the first apply, authenticate Terraform with your own GCP user account.
  The WIF service account cannot apply infrastructure Terraform.

On Windows PowerShell, authenticate for local Terraform with:

```powershell
gcloud auth application-default login
```

## 1. Bootstrap the remote state bucket

The state bucket must exist before Terraform can use it as a backend. This small
bootstrap configuration therefore starts with local state. It creates a
private, versioned GCS bucket and grants the WIF service account access to that
bucket only; it does not grant project infrastructure roles.

```powershell
Copy-Item infra/bootstrap-state/terraform.tfvars.example infra/bootstrap-state/terraform.tfvars
# Edit infra/bootstrap-state/terraform.tfvars and set project_id.
terraform -chdir=infra/bootstrap-state init
terraform -chdir=infra/bootstrap-state plan
terraform -chdir=infra/bootstrap-state apply
```

Keep the bootstrap local state file safe and backed up. It is ignored by Git.

## 2. Configure and initialize the main state

```powershell
Copy-Item infra/terraform.tfvars.example infra/terraform.tfvars
Copy-Item infra/backend.hcl.example infra/backend.hcl
# Edit both files with the project ID, GitHub owner, allowed account email,
# and generated bucket name.
terraform -chdir=infra init -backend-config=backend.hcl
terraform -chdir=infra plan
```

Review the plan carefully. It imports the existing WIF pool, provider and
service account, then creates Firebase Auth/Hosting, Firestore, Secret Manager
secret containers, runtime service account, Artifact Registry repository, and
the Cloud Run service. The initial Cloud Run revision uses Google's public
hello image; it is not the Garmin Trainer application. Firebase Hosting's
`/api/**` rewrite requires a public Cloud Run invoker binding, but FastAPI
verifies a Firebase ID token and the configured verified-email allowlist on
every API route except `/healthz`.

Only after reviewing the plan:

```powershell
terraform -chdir=infra apply
```

The project ID, GitHub owner/repository, and allowlisted e-mail are configuration,
not secrets. The local `.tfvars` and backend config files are ignored by Git.
Never put Garmin or LLM secret values in Terraform variables/state. Terraform
creates Secret Manager containers only; secret payloads are added separately
and are not wired into the bootstrap revision yet.

Firebase Authentication uses email/password. A user can register, but the API
only authorizes the configured, verified `allowed_user_email`. To enable a
project-wide GCP billing alert, set `billing_account_id` in the ignored
`infra/terraform.tfvars`; the default budget is USD 6/month and sends threshold
notifications only. It covers the whole project, not compute alone, and is not
a hard spending cap. Leave the billing account ID empty to defer it.

## IAM and GitHub Actions status

WIF authenticates GitHub Actions as `github-terraform`. Terraform grants it
application deployment permissions (Cloud Run Developer, Firebase Hosting/Rules,
Artifact Registry writer on the app repository, and act-as on the runtime
service account). It also has access to the remote state bucket. It does **not**
receive permission to apply all infrastructure Terraform; the initial and
future infrastructure applies use the project owner's ADC until a separate,
reviewed Terraform automation role is designed. No Owner/Editor role is granted.

The GitHub WIF provider is restricted to the configured repository and deploy
branch. `terraform-checks.yml` validates code but has no GCP credentials. The
application deploy workflow is gated off until the infrastructure apply
completes and repository variables are configured.

Set these GitHub Actions **variables** (not secrets) from Terraform outputs and
the project configuration before setting `GCP_DEPLOY_ENABLED=true`:

- `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SERVICE_ACCOUNT`
- `GAR_REPOSITORY=garmin-trainer`, `CLOUD_RUN_SERVICE=garmin-trainer-api`
- `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID`

The deploy workflow builds the web app with those public Firebase settings,
updates the Cloud Run image, and deploys Hosting plus the deny-all Firestore
rules. It only runs after `GCP_DEPLOY_ENABLED=true` is set.

The Firebase web API key is public client configuration, not a server secret.
Do not put the Garmin Personal API key or any LLM credential in GitHub Actions
variables; use Secret Manager for those values.
