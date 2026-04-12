from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_runs_cross_and_helm_validation() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "test.yml").read_text()

    assert "verify_cross.sh" in workflow
    assert "helm lint ./charts/vertex-openai-proxy" in workflow
    assert "helm template vertex-openai-proxy ./charts/vertex-openai-proxy" in workflow


def test_release_doc_mentions_cross_and_helm_gates() -> None:
    release_doc = (PROJECT_ROOT / "docs" / "release.md").read_text()

    assert "verify_cross.sh" in release_doc
    assert "helm lint" in release_doc
    assert "helm template" in release_doc
