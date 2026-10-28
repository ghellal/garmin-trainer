# Repository instructions

## Change and deployment safety

- **Never run `terraform apply` locally.** Infrastructure applies must run only through the protected GitHub Actions `workflow_dispatch` pipeline on `main`, and only when the user explicitly asks to deploy in the current request.
- `terraform fmt`, `terraform validate`, and `terraform plan` are safe to run when configuration and credentials are available. Before an authorized apply, review the exact plan and report resources to be created, changed, or destroyed. Do not use `-auto-approve` unless explicitly requested.
- Do not run `gcloud` commands that enable APIs, change IAM, create resources, or deploy services without explicit authorization. The WIF bootstrap script is a one-time setup reference; do not execute it automatically.
- Do not dispatch the GitHub deployment workflow without explicit authorization in the current request.
- Do not bypass organization policy restricting public Cloud Run invocation. If Firebase Hosting cannot invoke Cloud Run under the current policy, explain the constraint and ask before proposing or applying an architectural change.
- Prefer Terraform for GCP resource changes. Avoid out-of-band console or `gcloud` changes except for the explicitly authorized WIF bootstrap or user-directed recovery.

## Secrets and user data

- Never read, print, log, stage, or commit `.env`, `.env.local`, `*.tfvars`, Terraform state, backend configuration, access tokens, or secret payloads.
- Keep credentials in local ignored environment files or Google Secret Manager. Do not put secret values in Terraform variables/state, GitHub variables, workflow logs, or source code.
- Do not fetch Garmin health/activity data unless the user explicitly asks for that data operation.
- Before committing, verify that local credentials, Terraform state, plans, and build output are ignored and unstaged.

## Project conventions

- Preserve the existing Python CLI while extending the web app.
- The current foundation is a React/Vite PWA, FastAPI API, Firebase email/password auth with verified-email allowlisting, Firestore in `europe-west1`, Cloud Run, and Terraform.
- The API must validate Firebase ID tokens and the configured single-user allowlist. CORS is not an authorization mechanism; do not remove server-side auth checks.
- Firestore is accessed by the API only; keep browser Firestore rules deny-all unless the user explicitly changes that design.
- Keep `SPEC.md`, `ROADMAP.md`, `infra/README.md`, and this file consistent with architectural changes.

## Validation

- API tests: from `api/`, run `python -m pytest tests`.
- PWA: from `web/`, run `npm ci` and `npm run build`.
- Terraform: run `terraform fmt -check -recursive infra`, then validate both `infra/bootstrap-state` and `infra` without applying.
- GitHub deployment is currently gated and must remain disabled until explicitly authorized.
