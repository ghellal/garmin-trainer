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

**Always:** Use the existing `api/` container and current Terraform/Cloud Run service. For this initial release, retain the `allUsers` Cloud Run invoker binding while keeping `/healthz` minimal and public and server-side Firebase authentication plus the single-user allowlist on application routes. The user has deferred API Gateway with private Cloud Run as a separate future project item, not part of this deployment. Use the protected GitHub Actions workflow on `main` for every apply/deployment. Report the exact Terraform resource actions before applying. Because this GitHub repository is public and saved Terraform plans can contain sensitive values, do not publish plan files or plan values in GitHub logs/artifacts; keep only a non-sensitive plan fingerprint in the private, public-access-prevented state bucket. An apply must verify the fingerprint and apply only the plan generated in that same apply run.

**Never:** Add Garmin, coaching, chat, or other product features; make authenticated API routes anonymous; run local `terraform apply` or mutating `gcloud` commands; deploy Firebase Hosting as part of the API-only release; expose Terraform plan values, credentials, or secret payloads in the public repository.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Plan review | `mode=plan`, target `api`, current `main` | No apply; report only resource addresses/actions and save commit/target/plan fingerprints privately | Stop if auth, plan, or private manifest write fails |
| Approved apply | `mode=apply`, reviewed plan run ID, unchanged commit/state | Re-plan, verify fingerprints, apply the same saved plans, build/push API image, update Cloud Run; skip Hosting | Abort before apply on missing/stale/mismatched plan or fingerprint |
| Public health | Unauthenticated request to service `/healthz` | HTTP 200 with `{"status":"ok"}` | Deployment fails verification otherwise |
| Protected identity | Unauthenticated request to `/api/v1/me` | HTTP 401; verified allowlisted Firebase token remains required | Never weaken API auth to make the service publicly invokable |

</frozen-after-approval>

## Code Map

- `.github/workflows/deploy.yml` -- current single-job workflow runs Terraform plan/apply immediately, then builds/deploys API and PWA. Add plan/apply review modes and API-only target while retaining existing full-deploy behavior.
- `infra/main.tf` -- Cloud Run service configuration and `allUsers` invoker binding; Terraform owns both.
- `infra/bootstrap-iam/main.tf` -- the WIF runner's project roles; add Workload Identity Pool Admin so the main root can read/manage the imported pool and provider.
- `infra/bootstrap-state/main.tf` -- existing state bucket is private, enforces public access prevention, and grants the WIF runner object-admin access; suitable for non-sensitive plan fingerprints, not saved plan files.
- `api/app/main.py` -- already provides public `/healthz` and Firebase-verified `/api/v1/me`; no feature code change is required.
- `api/Dockerfile`, `api/requirements.txt` -- existing non-root Python 3.13 API image, listening on port 8080.
- `api/tests/test_main.py` -- existing tests prove health is public and identity remains authenticated/allowlisted.
- `infra/README.md` -- currently documents the immediate plan-and-apply workflow and its broader Hosting deployment; update it to explain the review/apply path and API-only mode.

## Tasks & Acceptance

**Execution:**
- [x] `.github/workflows/deploy.yml` -- add `plan`/`apply` and `api`/`all` inputs. Plan mode emits a sanitized resource-action summary and stores only run/commit/target plus fingerprints in the private GCS state bucket. Apply mode validates that manifest, recomputes both Terraform plans, stops on any mismatch, applies only those generated plans, then deploys the API; `api` skips Hosting and Firestore-rule deployment while `all` preserves current behavior.
- [x] `infra/bootstrap-iam/main.tf` and `.github/workflows/deploy.yml` -- add the WIF pool admin permission and a `bootstrap-iam` target so its exact IAM plan can be reviewed/applied before the main root needs that permission.
- [x] `api/tests/test_deploy_workflow.py` -- assert plan mode cannot apply, apply requires a same-commit/target manifest and matching fingerprints before Terraform apply, destructive actions require confirmation, and API-only mode skips Hosting; keep the public/protected route checks covered by `test_main.py`.
- [ ] `.github/workflows/deploy.yml` -- after API deployment, read-only verify `allUsers` invoker, unauthenticated `/healthz` returns 200, and unauthenticated `/api/v1/me` returns 401. Do not print plan values or secret environment values.
- [x] `infra/README.md` -- document the plan review and API-only dispatch, clarify that public Cloud Run invocation is not anonymous application authorization, and retain the no-local-apply rule.

**Acceptance Criteria:**
- Given a plan dispatch on `main`, when Terraform planning completes, then no resource is applied and the public workflow output contains only resource actions/addresses, not values.
- Given the initial runner lacks permission to read the imported WIF pool, when `target=bootstrap-iam` is planned and reviewed/applied, then only the bootstrap IAM root is applied and the WIF pool admin role is reported before authorization.
- Given an apply dispatch referencing the reviewed plan, when the commit, target, or either Terraform plan fingerprint differs, then the workflow aborts before either Terraform apply.
- Given matching fingerprints, when the API-only apply completes, then the API image is deployed to `garmin-trainer-api` and Firebase Hosting is not deployed.
- Given the resulting Cloud Run service, when requests are unauthenticated, then `/healthz` returns 200 and `/api/v1/me` returns 401; valid Firebase authentication and the allowlist remain enforced.
- Given the plan contains destructive actions or Terraform fails, when the plan is reviewed, then no apply is run until the exact actions and recovery path are explicitly reviewed.

## Implementation Notes

The GitHub repository is public, so saved Terraform plan files stay in the ephemeral runner. The workflow canonicalizes `terraform show -json` output and stores only SHA-256 fingerprints and non-sensitive run metadata in the state bucket after checking public access prevention. Apply mode recomputes plans, verifies the reviewed fingerprints, and applies only those same-run plan files. Plan binaries and values are not uploaded or printed. Runner temp paths are exported from a shell step rather than referenced from job-level expressions.

Added workflow guard tests using the Python standard library and the existing API test suite. The live GitHub plan/apply and post-deployment checks remain pending; they cannot run until this workflow change is on `main`.

Local verification: API suite 10 passed; Terraform format check and validation passed for `infra`, `infra/bootstrap-iam`, and `infra/bootstrap-state`; workflow YAML parsed and all 18 multiline Bash steps passed `bash -n`; `git diff --check` passed.

Implementation and code review are complete locally. The workflow was not pushed or dispatched from this build run; Cloud Run remains unchanged until the reviewed `mode=plan`, `target=api` workflow is run on `main`, its resource actions are inspected, and the matching apply is explicitly dispatched.

After the workflow commit was pushed, plan-only run `42536078311` failed in the main infrastructure planning step; apply and deployment steps did not run. Terraform diagnostics were intentionally suppressed, so the workflow now emits only a sanitized first error-summary line on a future plan failure, with the full log still confined to the ephemeral runner.

Plan-only run `42536352154` identified the missing `iam.workloadIdentityPools.get` permission while reading the imported WIF pool. The workflow now supports a bootstrap-only target, and `infra/bootstrap-iam` grants `roles/iam.workloadIdentityPoolAdmin`; the grant remains unapplied pending review of its exact bootstrap IAM plan.

The `bootstrap-iam` target now plans/applies only the bootstrap IAM root and skips main infrastructure planning, API image deployment, and Hosting. Local tests and validation pass; the next required remote step is a plan-only bootstrap run so the exact IAM grant can be reviewed before any apply.

The first bootstrap-only plan showed sanitized resource actions, but manifest storage stopped because the bucket check used the wrong gcloud output-field name. The workflow now reads the documented `public_access_prevention` field and echoes sanitized resource actions into logs as well as the job summary; no manifest or IAM change was written by that failed plan run.

## Plan Change Log


## Review Triage Log

No findings returned by the Quick review lens.

## Verification

**Commands:**
- `python -m pytest tests` from `api/` -- all existing auth and health tests pass.
- `terraform fmt -check -recursive infra` and `terraform -chdir=infra validate` plus `terraform -chdir=infra/bootstrap-iam validate` -- formatting and configuration validate; no local apply.
- `git diff --check` -- no whitespace errors in changes.
- GitHub Actions plan mode -- outputs a sanitized resource summary and writes fingerprints privately without applying; inspect and report exact create/change/destroy actions before apply.
- GitHub Actions apply mode -- applies only after fingerprint match, deploys API-only, and passes the post-deploy public-health/protected-API checks.
