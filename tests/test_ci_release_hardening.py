from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_runs_cross_and_helm_validation() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "test.yml").read_text()

    assert "verify_cross.sh" in workflow
    assert "helm lint ./charts/vertex-openai-proxy" in workflow
    assert "helm template vertex-openai-proxy ./charts/vertex-openai-proxy" in workflow
    assert "auth.internalBearerToken=ci-smoke-token" in workflow
    assert "Verify Helm chart fails closed without auth secret" in workflow
    assert "Set auth.internalBearerToken or auth.existingSecret" in workflow


def test_release_doc_mentions_cross_and_helm_gates() -> None:
    release_doc = (PROJECT_ROOT / "docs" / "release.md").read_text()

    assert "verify_cross.sh" in release_doc
    assert "helm lint" in release_doc
    assert "helm template" in release_doc
    assert "fails closed" in release_doc


def test_release_workflow_builds_public_artifacts_without_cluster_deploy() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "release.yml").read_text()

    assert "docker/build-push-action" in workflow
    assert "ghcr.io" in workflow
    assert "helm package" in workflow
    assert "workflow_dispatch" in workflow
    assert "release:" in workflow
    assert "kubectl" not in workflow
    assert "helm upgrade" not in workflow
    assert "gcloud" not in workflow
