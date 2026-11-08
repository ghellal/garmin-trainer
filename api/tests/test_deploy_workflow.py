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

    summary = step("Publish sanitized resource-action summary")
    assert ".resource_changes[]?" in summary
    assert ".change.actions" in summary
    assert ".change.importing?" in summary
    assert 'then "import"' in summary
    assert ".address" in summary
    assert ".values" not in summary
    assert "upload-artifact" not in WORKFLOW

    manifest = step("Store private plan fingerprints")
    assert "publicAccessPrevention" in manifest
    assert "schema_version: 1" in manifest
    assert "bootstrap_iam_sha256" in manifest
    assert "infra_sha256" in manifest
    assert "BOOTSTRAP_IAM_PLAN" not in manifest
    assert "INFRA_PLAN" not in manifest


def test_apply_is_bound_to_reviewed_commit_and_plan_before_any_apply() -> None:
    load_manifest = step("Load reviewed plan manifest")
    assert ".plan_run_id == $run_id" in load_manifest
    assert ".commit == $commit" in load_manifest
    assert ".target == $target" in load_manifest

    assert "jq -S -c ." in step("Plan bootstrap IAM")
    assert "jq -S -c ." in step("Plan infrastructure")
    assert 'if [[ "$CONFIRM_DESTRUCTIVE" != "true" ]]' in step(
        "Require destructive-change review"
    )

    verify = WORKFLOW.index("      - name: Verify reviewed plan fingerprints")
    review_deletes = WORKFLOW.index("      - name: Require destructive-change review")
    apply_bootstrap = WORKFLOW.index("      - name: Apply bootstrap IAM plan")
    apply_infra = WORKFLOW.index("      - name: Apply infrastructure plan")
    assert verify < review_deletes < apply_bootstrap < apply_infra
    assert "if: env.DEPLOY_MODE == 'apply'" in step("Apply bootstrap IAM plan")
    assert "if: env.DEPLOY_MODE == 'apply'" in step("Apply infrastructure plan")


def test_api_only_target_does_not_deploy_firebase_hosting() -> None:
    assert "if: env.DEPLOY_MODE == 'apply' && env.DEPLOY_TARGET == 'all'" in step(
        "Set up Node.js"
    )
    assert "if: env.DEPLOY_MODE == 'apply' && env.DEPLOY_TARGET == 'all'" in step(
        "Build and deploy PWA and Firestore rules"
    )
    assert "if: env.DEPLOY_MODE == 'apply'" in step("Deploy API image")
