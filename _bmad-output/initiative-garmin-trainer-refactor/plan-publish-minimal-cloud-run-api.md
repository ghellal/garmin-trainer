---
title: Publish the minimal authenticated API on Cloud Run
type: feature
ticket: ''
created: '2026-11-09'
status: in-progress
baseline_revision: 'b977d20806f975e5006f173dbc584aae305a1556'
route: full
route_source: auto
risk: high
review: quick
review_source: pinned
lenses_ran: [quick]
review_loop_iteration: 0
context:
  - AGENTS.md
  - .github/workflows/deploy.yml
  - api/app/main.py
  - infra/README.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Cloud Run still has the bootstrap image rather than the repository's minimal FastAPI service. The user wants a working minimal service available publicly now, without adding a product feature.

**Approach:** Deploy the existing API container, make the Cloud Run service publicly invokable for the intended public entry points, and verify the result. “Public” means the Cloud Run invoker allows `allUsers`; it does not remove Firebase token verification or the verified-email allowlist from `/api/v1/me`.

## Boundaries & Constraints

**Always:** Use the existing `api/` container and current Terraform/Cloud Run service. For this initial release, retain the `allUsers` Cloud Run invoker binding while keeping `/healthz` minimal and public and server-side Firebase authentication plus the single-user allowlist on application routes. The user has deferred API Gateway with private Cloud Run as a separate future project item, not part of this deployment. Use the protected GitHub Actions workflow on `main` for every apply/deployment. Report the exact Terraform resource actions before applying. Because this GitHub repository is public and saved Terraform plans can contain sensitive values, never publish plans or values in GitHub logs/artifacts. With the user's approval, store exact plan files plus commit/target/checksum metadata only in the private, public-access-prevented GCS state bucket. Apply only the downloaded plan bytes after checksum and age checks; expire plans for apply after 24 hours and delete every object version after successful apply.

**Never:** Add Garmin, coaching, chat, or other product features; make authenticated API routes anonymous; run local `terraform apply` or mutating `gcloud` commands; deploy Firebase Hosting as part of the API-only release; expose Terraform plan values, credentials, or secret payloads in the public repository.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Plan review | `mode=plan`, target `api`, current `main` | No apply; report only resource addresses/actions and store exact plans plus commit/target/checksums privately | Stop if auth, plan, private storage, or checksum generation fails |
| Approved apply | `mode=apply`, reviewed plan run ID, valid age and checksums | Download and verify the reviewed plan bytes, apply those exact plans, build/push API image, update Cloud Run; skip Hosting | Abort before apply on missing/expired/mismatched plan or checksum |
| Public health | Unauthenticated request to service `/healthz` | HTTP 200 with `{"status":"ok"}` | Deployment fails verification otherwise |
| Protected identity | Unauthenticated request to `/api/v1/me` | HTTP 401; verified allowlisted Firebase token remains required | Never weaken API auth to make the service publicly invokable |

</frozen-after-approval>

## Code Map

- `.github/workflows/deploy.yml` -- current single-job workflow runs Terraform plan/apply immediately, then builds/deploys API and PWA. Add plan/apply review modes and API-only target while retaining existing full-deploy behavior.
- `infra/main.tf` -- Cloud Run service configuration and `allUsers` invoker binding; Terraform owns both.
- `infra/bootstrap-iam/main.tf` -- the WIF runner's project roles; add Workload Identity Pool Admin so the main root can read/manage the imported pool and provider.
- `infra/bootstrap-state/main.tf` -- existing state bucket is private, enforces public access prevention, and grants the WIF runner object-admin access; the user approved temporary Terraform plan files there, never in GitHub artifacts.
- `api/app/main.py` -- already provides public `/healthz` and Firebase-verified `/api/v1/me`; no feature code change is required.
- `api/Dockerfile`, `api/requirements.txt` -- existing non-root Python 3.13 API image, listening on port 8080.
- `api/tests/test_main.py` -- existing tests prove health is public and identity remains authenticated/allowlisted.
- `infra/README.md` -- currently documents the immediate plan-and-apply workflow and its broader Hosting deployment; update it to explain the review/apply path and API-only mode.

## Tasks & Acceptance

**Execution:**
- [ ] `.github/workflows/deploy.yml` -- store exact `.tfplan` files under the private GCS run prefix after verifying bucket public-access prevention; apply mode validates manifest commit/target/age, downloads and checksums the exact files, applies those bytes, deletes all versions after success, and deploys the API; `api` skips Hosting while `all` preserves current behavior.
- [x] `infra/bootstrap-iam/main.tf` and `.github/workflows/deploy.yml` -- add the WIF pool admin permission and a `bootstrap-iam` target so its exact IAM plan can be reviewed/applied before the main root needs that permission.
- [x] `api/tests/test_deploy_workflow.py` -- assert plan mode cannot apply, apply requires a same-commit/target manifest and matching checksums before Terraform apply, destructive actions require confirmation, bootstrap-only mode stops before the main root/API, and API-only mode skips Hosting; keep the public/protected route checks covered by `test_main.py`.
- [ ] `.github/workflows/deploy.yml` -- after API deployment, read-only verify `allUsers` invoker, unauthenticated `/healthz` returns 200, and unauthenticated `/api/v1/me` returns 401. Do not print plan values or secret environment values.
- [x] `infra/README.md` -- document the plan review and API-only dispatch, clarify that public Cloud Run invocation is not anonymous application authorization, and retain the no-local-apply rule.

**Acceptance Criteria:**
- Given a plan dispatch on `main`, when Terraform planning completes, then no resource is applied and the public workflow output contains only resource actions/addresses, not values.
- Given the initial runner lacks permission to read the imported WIF pool, when `target=bootstrap-iam` is planned and reviewed/applied, then only the bootstrap IAM root is applied and the WIF pool admin role is reported before authorization.
- Given an apply dispatch referencing the reviewed plan, when the commit, target, age, or either saved-plan checksum differs, then the workflow aborts before either Terraform apply.
- Given matching saved-plan checksums, when the API-only apply completes, then those exact saved plans are applied, the API image is deployed to `garmin-trainer-api`, and Firebase Hosting is not deployed.
- Given the resulting Cloud Run service, when requests are unauthenticated, then `/healthz` returns 200 and `/api/v1/me` returns 401; valid Firebase authentication and the allowlist remain enforced.
- Given the plan contains destructive actions or Terraform fails, when the plan is reviewed, then no apply is run until the exact actions and recovery path are explicitly reviewed.

## Implementation Notes

The GitHub repository is public. The user approved temporarily storing exact Terraform plan files in the existing GCS state bucket, which enforces public access prevention. The workflow stores a manifest with commit/target/expiry and file checksums, but never logs or uploads plans to GitHub. Apply mode downloads and verifies the exact bytes before applying; on success it deletes all object versions for that run. Plans older than 24 hours are refused for apply. Runner temp paths are exported from a shell step rather than referenced from job-level expressions.

Added workflow guard tests using the Python standard library and the existing API test suite. The bootstrap IAM plan has been approved and applied; main infrastructure/API apply and post-deployment checks are still pending.

Local verification: API suite 12 passed; Terraform format check and validation passed for `infra`, `infra/bootstrap-iam`, and `infra/bootstrap-state`; workflow YAML parsed and all 19 multiline Bash steps passed `bash -n`; `git diff --check` passed.

The deployment workflow is pushed to `main`; the bootstrap IAM apply completed. The API-only plan run `42537780917` was reviewed and approved, but cross-run checksum verification failed before apply. A new plan run is required for the exact-plan-file workflow; Cloud Run remains unchanged.

Apply run `42651323812` applied bootstrap IAM successfully but failed during the main infrastructure apply; the API image and Cloud Run deployment steps were skipped. Terraform may have partially applied main-root changes. The detailed apply log was on the ephemeral runner, so the workflow now emits only a sanitized first error summary on apply failure; the next operation must be a fresh plan-only run to reconcile current state.

After the workflow commit was pushed, plan-only run `42536078311` failed in the main infrastructure planning step; apply and deployment steps did not run. Terraform diagnostics were intentionally suppressed, so the workflow now emits only a sanitized first error-summary line on a future plan failure, with the full log still confined to the ephemeral runner.

Plan-only run `42536352154` identified the missing `iam.workloadIdentityPools.get` permission while reading the imported WIF pool. The workflow now supports a bootstrap-only target, and `infra/bootstrap-iam` grants `roles/iam.workloadIdentityPoolAdmin`; the approved bootstrap IAM plan was applied successfully in run `42537682219`.

The `bootstrap-iam` target plans/applies only the bootstrap IAM root and skips main infrastructure planning, API image deployment, and Hosting.

The first bootstrap-only plan showed sanitized resource actions, but manifest storage stopped because the bucket check used the wrong gcloud output-field name. The workflow now reads the documented `public_access_prevention` field and echoes sanitized resource actions into logs as well as the job summary; no manifest or IAM change was written by that failed plan run.

Apply attempts `42537333213` (bootstrap), `42538036619` and `42538475139` (API) stopped before Terraform apply because cross-run fingerprints differed. The user approved switching to exact plan files stored only in the private GCS bucket, with checksums and age checks; no plans are stored in public GitHub artifacts.

## Plan Change Log

- User-authorized amendment after repeated cross-run fingerprint mismatches: save exact Terraform plans only in the private GCS state bucket, bind them to commit/target/24-hour expiry with checksums, apply those exact bytes, and delete all stored versions after successful apply. This avoids regenerating a plan that cannot be proven identical; no plan file or value may appear in public GitHub logs/artifacts.

## Review Triage Log

No findings returned by the Quick review lens.

## Verification

**Commands:**
- `python -m pytest tests` from `api/` -- all existing auth and health tests pass.
- `terraform fmt -check -recursive infra` and `terraform -chdir=infra validate` plus `terraform -chdir=infra/bootstrap-iam validate` -- formatting and configuration validate; no local apply.
- `git diff --check` -- no whitespace errors in changes.
- GitHub Actions plan mode -- outputs a sanitized resource summary and stores exact plans privately without applying; inspect and report exact create/change/destroy actions before apply.
- GitHub Actions apply mode -- downloads checksum-verified plan bytes, deploys API-only, removes stored plan object versions after success, and passes the post-deploy public-health/protected-API checks.
