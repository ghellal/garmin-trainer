from pathlib import Path


WORKFLOW = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "workflows"
    / "deploy.yml"
).read_text(encoding="utf-8")


def step(name: str) -> str:
    marker = f"      - name: {name}"
    start = WORKFLOW.index(marker)
    next_step = WORKFLOW.find("\n      - name: ", start + len(marker))
    return WORKFLOW[start:] if next_step == -1 else WORKFLOW[start:next_step]


def test_plan_mode_is_default_and_only_emits_sanitized_resource_actions() -> None:
    assert "default: plan" in WORKFLOW
    assert "default: api" in WORKFLOW
    assert "terraform -chdir=infra/bootstrap-iam plan" in step("Plan bootstrap IAM")
    assert "terraform -chdir=infra plan" in step("Plan infrastructure")
    assert "terraform apply" not in step("Plan bootstrap IAM")
    assert "terraform apply" not in step("Plan infrastructure")
    for name in ("Plan bootstrap IAM", "Plan infrastructure"):
        failure_handling = step(name)
        assert "grep -m 1 'Error:'" in failure_handling
        assert "[redacted-email]" in failure_handling
        assert "sensitive plan output was suppressed" in failure_handling

    summary = step("Publish sanitized resource-action summary")
    assert ".resource_changes[]?" in summary
    assert ".change.actions" in summary
    assert ".change.importing?" in summary
    assert 'then "import"' in summary
    assert ".address" in summary
    assert ".values" not in summary
    assert 'tee -a "$GITHUB_STEP_SUMMARY"' in summary
    assert "upload-artifact" not in WORKFLOW

    manifest = step("Store private reviewed Terraform plans")
    assert "public_access_prevention" in manifest
    assert "not enforced" in manifest
    assert "schema_version: 2" in manifest
    assert "created_at_epoch" in manifest
    assert "bootstrap_iam_sha256" in manifest
    assert "infra_sha256" in manifest
    assert '"$BOOTSTRAP_IAM_PLAN"' in manifest
    assert '"$INFRA_PLAN"' in manifest
    assert "if-generation-match=0" in manifest
    assert "upload-artifact" not in WORKFLOW


def test_apply_is_bound_to_reviewed_commit_and_plan_before_any_apply() -> None:
    load_manifest = step("Load reviewed plan manifest")
    assert ".schema_version == 2" in load_manifest
    assert ".plan_run_id == $run_id" in load_manifest
    assert ".commit == $commit" in load_manifest
    assert ".target == $target" in load_manifest
    assert "age_seconds > 86400" in load_manifest
    assert '"${plan_prefix}/bootstrap-iam.tfplan"' in load_manifest
    assert '"${plan_prefix}/infra.tfplan"' in load_manifest

    assert "if: env.DEPLOY_MODE == 'plan'" in step("Plan bootstrap IAM")
    assert "if: env.DEPLOY_MODE == 'plan'" in step("Plan infrastructure")
    verify = step("Verify reviewed plan files")
    assert 'sha256sum "$BOOTSTRAP_IAM_PLAN"' in verify
    assert 'sha256sum "$INFRA_PLAN"' in verify
    assert 'if [[ "$CONFIRM_DESTRUCTIVE" != "true" ]]' in step(
        "Require destructive-change review"
    )
    for name in ("Apply bootstrap IAM plan", "Apply infrastructure plan"):
        failure_handling = step(name)
        assert "grep -m 1 'Error:'" in failure_handling
        assert "[redacted-email]" in failure_handling

    verify_index = WORKFLOW.index("      - name: Verify reviewed plan files")
    review_deletes = WORKFLOW.index("      - name: Require destructive-change review")
    apply_bootstrap = WORKFLOW.index("      - name: Apply bootstrap IAM plan")
    apply_infra = WORKFLOW.index("      - name: Apply infrastructure plan")
    assert verify_index < review_deletes < apply_bootstrap < apply_infra
    assert "if: env.DEPLOY_MODE == 'apply'" in step("Apply bootstrap IAM plan")
    assert "if: env.DEPLOY_MODE == 'apply'" in step("Apply infrastructure plan")
    assert "gcloud storage rm --quiet --all-versions" in step(
        "Remove applied Terraform plan objects"
    )


def test_api_only_target_does_not_deploy_firebase_hosting() -> None:
    assert "if: env.DEPLOY_MODE == 'apply' && env.DEPLOY_TARGET == 'all'" in step(
        "Set up Node.js"
    )
    assert "if: env.DEPLOY_MODE == 'apply' && env.DEPLOY_TARGET == 'all'" in step(
        "Build and deploy PWA and Firestore rules"
    )
    assert "if: env.DEPLOY_MODE == 'apply'" in step("Deploy API image")


def test_bootstrap_iam_target_stops_before_infrastructure_and_api() -> None:
    assert "- bootstrap-iam" in WORKFLOW
    assert (
        "if: env.DEPLOY_MODE == 'plan' && env.DEPLOY_TARGET != 'bootstrap-iam'"
        in step("Plan infrastructure")
    )
    assert '.infra_sha256 == "not-applicable"' in step("Load reviewed plan manifest")
    assert 'if [[ "$DEPLOY_TARGET" != "bootstrap-iam" ]]' in step(
        "Verify reviewed plan files"
    )
    assert 'if [[ "$DEPLOY_TARGET" != "bootstrap-iam" ]]' in step(
        "Require destructive-change review"
    )
    for name in (
        "Apply infrastructure plan",
        "Build and push API image",
        "Deploy API image",
    ):
        assert (
            "if: env.DEPLOY_MODE == 'apply' && env.DEPLOY_TARGET != 'bootstrap-iam'"
            in step(name)
        )
    verify = step("Verify public Cloud Run access and API authorization")
    assert "env.DEPLOY_MODE == 'verify'" in verify
    assert "env.DEPLOY_MODE == 'apply' && env.DEPLOY_TARGET != 'bootstrap-iam'" in verify


def test_bootstrap_grants_the_wif_pool_role_required_by_main_terraform() -> None:
    bootstrap_iam = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "bootstrap-iam"
        / "main.tf"
    ).read_text(encoding="utf-8")
    assert '"roles/iam.workloadIdentityPoolAdmin"' in bootstrap_iam


def test_verify_mode_is_read_only_and_checks_the_live_api() -> None:
    assert "- verify" in WORKFLOW
    assert "Verify mode is available for the API target only." in step(
        "Require deployment configuration"
    )
    assert "if: env.DEPLOY_MODE != 'verify'" in step("Set up Terraform")
    assert "if: env.DEPLOY_MODE != 'verify'" in step(
        "Generate Terraform backend configuration"
    )
    verify = step("Verify public Cloud Run access and API authorization")
    assert "env.DEPLOY_MODE == 'verify'" in verify
    assert "for attempt in {1..10}" in verify
    assert 'HTTP ${health_status}' in verify
    assert "Cloud Run URL:" in verify
    assert verify.index("/api/v1/me") < verify.index("if [[ \"$health_ok\"")
    assert '"$api_url/openapi.json"' in verify
    assert ".paths | keys | join" in verify
    assert "terraform apply" not in verify
    assert "always() && env.DEPLOY_MODE == 'apply'" in step(
        "Remove applied Terraform plan objects"
    )


def test_applied_plans_are_cleaned_even_if_post_deploy_checks_fail() -> None:
    cleanup = step("Remove applied Terraform plan objects")
    assert "always()" in cleanup
    assert "steps.apply_bootstrap_iam.outcome == 'success'" in cleanup
    assert "steps.apply_infrastructure.outcome == 'success'" in cleanup
    assert "--all-versions" in cleanup


def test_budget_uses_billing_account_currency() -> None:
    root = Path(__file__).resolve().parents[2]
    main_tf = (root / "infra" / "main.tf").read_text(encoding="utf-8")

    assert "units = tostring(var.monthly_budget_usd)" in main_tf
    assert 'currency_code = "USD"' not in main_tf
    assert "TF_VAR_monthly_budget_usd" in WORKFLOW
    assert "GCP_MONTHLY_BUDGET_AMOUNT" in WORKFLOW
