#!/usr/bin/env bash
set -euo pipefail

# One-time bootstrap for GitHub Actions Workload Identity Federation.
# Run from Google Cloud Shell with gcloud authenticated as a project admin.
# This intentionally grants no Cloud Run, Artifact Registry, or other
# infrastructure permissions; manage those separately with Terraform.

# Replace these placeholders before running.
PROJECT_ID="ai-assistant-kira"
GITHUB_OWNER="ghellal"
GITHUB_REPO="garmin-trainer"
GITHUB_DEPLOY_BRANCH="main"

# Stable resource names; change only if these already exist for another setup.
POOL_ID="github-actions"
PROVIDER_ID="github"
TERRAFORM_SA_ID="github-terraform"

for value in "$PROJECT_ID" "$GITHUB_OWNER" "$GITHUB_REPO"; do
  if [[ "$value" == REPLACE_* ]]; then
    echo "Replace all REPLACE_WITH_* placeholders near the top of this file first." >&2
    exit 1
  fi
done

if [[ -z "$GITHUB_DEPLOY_BRANCH" ]]; then
  echo "GITHUB_DEPLOY_BRANCH must not be empty." >&2
  exit 1
fi

gcloud config set project "$PROJECT_ID" >/dev/null

# These are the only APIs enabled by this bootstrap. Service Usage must
# already be available in the project for gcloud services enable to work.
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  --project="$PROJECT_ID"

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
TERRAFORM_SA_EMAIL="${TERRAFORM_SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$TERRAFORM_SA_EMAIL" \
  --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$TERRAFORM_SA_ID" \
    --project="$PROJECT_ID" \
    --display-name="GitHub Actions Terraform"
fi

if ! gcloud iam workload-identity-pools describe "$POOL_ID" \
  --project="$PROJECT_ID" \
  --location="global" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL_ID" \
    --project="$PROJECT_ID" \
    --location="global" \
    --display-name="GitHub Actions"
fi

if ! gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="$POOL_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
    --project="$PROJECT_ID" \
    --location="global" \
    --workload-identity-pool="$POOL_ID" \
    --display-name="GitHub repository provider" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository == '${GITHUB_OWNER}/${GITHUB_REPO}' && assertion.ref == 'refs/heads/${GITHUB_DEPLOY_BRANCH}'"
fi

gcloud iam service-accounts add-iam-policy-binding "$TERRAFORM_SA_EMAIL" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_OWNER}/${GITHUB_REPO}"

echo
echo "WIF bootstrap complete. No infrastructure permissions were granted."
echo "Set these as GitHub Actions variables (not secrets):"
echo "GCP_PROJECT_ID=${PROJECT_ID}"
echo "GCP_WIF_PROVIDER=projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
echo "GCP_TERRAFORM_SERVICE_ACCOUNT=${TERRAFORM_SA_EMAIL}"
echo
echo "The provider only accepts push/workflow_dispatch runs on ${GITHUB_DEPLOY_BRANCH}."
