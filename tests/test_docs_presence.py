from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_harness_docs_exist() -> None:
    for relative_path in [
        "CHANGELOG.md",
        "docs/alerts.md",
        "docs/harness.md",
        "docs/private-handoff.md",
        "docs/release.md",
        "docs/runbook.md",
        "docs/operations-transition.md",
    ]:
        assert (PROJECT_ROOT / relative_path).exists()


def test_helm_example_values_exist() -> None:
    for relative_path in [
        "charts/vertex-openai-proxy/examples/values-small.yaml",
        "charts/vertex-openai-proxy/examples/values-balanced-hpa.yaml",
        "charts/vertex-openai-proxy/examples/values-heavy-ingestion.yaml",
        "charts/vertex-openai-proxy/examples/values-production.yaml",
    ]:
        assert (PROJECT_ROOT / relative_path).exists()


def test_release_docs_cover_versioning_and_release_notes() -> None:
    release_doc = (PROJECT_ROOT / "docs" / "release.md").read_text()

    assert "Versioning Policy" in release_doc
    assert "Release Note Template" in release_doc
    assert "Chart version" in release_doc
    assert "app version" in release_doc


def test_runbook_covers_rollout_and_rollback() -> None:
    runbook = (PROJECT_ROOT / "docs" / "runbook.md").read_text()

    assert "Rollout" in runbook
    assert "Rollback" in runbook
    assert "/readyz" in runbook
    assert "helm upgrade" in runbook


def test_alerts_cover_runtime_and_shedding_metrics() -> None:
    alerts = (PROJECT_ROOT / "docs" / "alerts.md").read_text()

    assert "vertex_proxy_runtime_mode" in alerts
    assert "vertex_proxy_request_shed_total" in alerts
    assert "p95" in alerts


def test_private_handoff_doc_covers_infra_boundary() -> None:
    handoff = (PROJECT_ROOT / "docs" / "private-handoff.md").read_text()

    assert "Argo CD" in handoff or "Flux" in handoff or "Helm release" in handoff
    assert "INTERNAL_BEARER_TOKEN" in handoff
    assert "Workload Identity" in handoff
    assert "private" in handoff.lower()
