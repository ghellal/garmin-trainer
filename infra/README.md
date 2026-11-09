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

## Review and deployment workflow

```powershell
Copy-Item infra/terraform.tfvars.example infra/terraform.tfvars
Copy-Item infra/backend.hcl.example infra/backend.hcl
# Fill local config only if you need a read-only local plan.
terraform -chdir=infra init -backend-config=backend.hcl
terraform -chdir=infra plan
```

Use **Actions → Review and deploy infrastructure → Run workflow** on `main`.
The protected `production` environment and WIF identity are used in both modes.
The workflow passes Terraform inputs through `TF_VAR_*` environment variables
and creates ignored backend configuration files on the ephemeral runner.

1. For initial WIF permissions, dispatch with `mode=plan,target=bootstrap-iam`.
   This plans only `infra/bootstrap-iam`; it does not apply or deploy. Review the
   exact IAM changes, including `roles/iam.workloadIdentityPoolAdmin` for the
   Terraform-managed WIF pool/provider. Apply only after reviewing the sanitized
   resource-action summary and logs, using `mode=apply`, the same target, and
   `reviewed_plan_run_id` from that run.
2. After bootstrap IAM succeeds, dispatch with `mode=plan` and choose
   `target=api` or `target=all`. This plans both `infra/bootstrap-iam` and
   `infra`, but does not apply or deploy. Its workflow summary and logs contain
   only Terraform resource actions and addresses. It writes the exact saved
   plans plus a manifest (commit, target, run ID, expiry, and checksums) under
   `garmin-trainer/release-plans/` in the Terraform state bucket. That bucket
   enforces public access prevention. Plan files can contain sensitive values;
   they are never uploaded to GitHub artifacts or printed in workflow logs.
3. Review the exact resource actions and addresses in the completed plan run.
   Before approving any destructive action, explicitly review its recovery path.
   Dispatch again on the same commit with `mode=apply`, the same target, and
   `reviewed_plan_run_id` set to the plan run ID. If a plan contains a delete or
   replacement, also enable `confirm_destructive` only after that review.
   Apply mode loads the private manifest, rejects plans older than 24 hours,
   downloads the saved plan files, verifies their checksums, then applies those
    exact bytes. A missing, expired, or mismatched plan aborts before Terraform
    apply. After a fully successful deployment, the workflow removes all stored
    object versions for that plan run. If a plan is never applied or deployment
    fails, its files remain private in the bucket until cleaned up.

Use `mode=verify,target=api` to recheck a live Cloud Run service without applying
Terraform or rebuilding the image. This read-only mode reports the service URL,
checks the `allUsers` invoker binding, retries transient health-check failures,
and confirms that unauthenticated `/healthz` returns 200 while `/api/v1/me` still
returns 401.

With `target=api`, a successful apply builds and pushes the existing `api/`
container and updates `garmin-trainer-api`; it does not deploy Firebase Hosting
or Firestore rules. `target=all` retains the existing broader behavior and also
builds and deploys the PWA and deny-all Firestore rules. Both targets reconcile
the Terraform roots before application deployment.

The Cloud Run service has a public `allUsers` invoker binding to support its
public entry points. This is not anonymous application authorization:
`/healthz` is intentionally public and minimal, while FastAPI still verifies a
Firebase ID token and the configured verified-email allowlist on every
application route such as `/api/v1/me`. After API deployment, the workflow
checks the invoker binding, verifies unauthenticated `/healthz` returns HTTP 200,
and verifies unauthenticated `/api/v1/me` returns HTTP 401.

Never run `terraform apply` locally. Apply and deployment must use the protected
GitHub Actions workflow on `main`; do not dispatch apply until the exact plan
actions have been reviewed.

The project ID, GitHub owner/repository, and allowlisted e-mail are configuration,
not secrets. The local `.tfvars` and backend config files are ignored by Git.
Never put Garmin or LLM secret values in Terraform variables/state. Terraform
creates Secret Manager containers only; secret payloads are added separately
and are not wired into the bootstrap revision yet.

Firebase Authentication uses email/password. A user can register, but the API
only authorizes the configured, verified `allowed_user_email`. The pipeline
expects `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_TERRAFORM_SERVICE_ACCOUNT`,
and `GCP_BILLING_ACCOUNT_ID` as GitHub Actions variables. `GCP_REGION` and
`GCP_MONTHLY_BUDGET_AMOUNT` are optional; the latter is expressed in the billing
account's currency, with `GCP_MONTHLY_BUDGET_USD` accepted as a legacy alias.
`ALLOWED_USER_EMAIL` must be a GitHub Actions secret. The Firebase web config is
read from Terraform outputs and is public client configuration. Never store the
Garmin or LLM credentials in GitHub.

If enabled, the default 6-unit/month budget uses the billing account's currency.
It is a project-wide notification only, not a spending cap, and covers all project
usage, not compute alone.

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
`roles/iam.workloadIdentityPoolAdmin`, `roles/artifactregistry.admin`, and
`roles/run.admin`. Some of these roles allow
the pipeline identity to access Firestore data or Secret Manager values; treat
the WIF identity and protected workflow as highly privileged. Project IAM
Admin can grant other project roles, so scope it to this project, restrict WIF
to this repository and `main`, and require approval on the GitHub `production`
environment. Do not grant project Owner/Editor for convenience.

The GitHub WIF provider is restricted to this repository and the `main` branch.
`terraform-checks.yml` validates code without GCP credentials. Deployment is
manual-only (`workflow_dispatch`) through **Review and deploy infrastructure**.
Use its plan mode before apply; the apply mode applies only after the reviewed
plan run, commit, target, and both Terraform fingerprints match. No local apply
is part of the process.
