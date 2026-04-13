from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_harness_docs_exist() -> None:
    for relative_path in [
        "CHANGELOG.md",
        "docs/alerts.md",
        "docs/canary-checklist.md",
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
        "examples/private-infra/values-common.yaml",
        "examples/private-infra/values-canary.yaml",
        "examples/private-infra/values-stable.yaml",
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


def test_canary_checklist_covers_verification_and_rollback() -> None:
    checklist = (PROJECT_ROOT / "docs" / "canary-checklist.md").read_text()

    assert "/livez" in checklist
    assert "/readyz" in checklist
    assert "vertex_proxy_request_shed_total" in checklist
    assert "rollback" in checklist.lower()


def test_private_infra_values_examples_cover_common_canary_and_stable() -> None:
    common = (PROJECT_ROOT / "examples/private-infra/values-common.yaml").read_text()
    canary = (PROJECT_ROOT / "examples/private-infra/values-canary.yaml").read_text()
    stable = (PROJECT_ROOT / "examples/private-infra/values-stable.yaml").read_text()

    assert "auth:" in common
    assert "existingSecret" in common
    assert "vertexProjectId" in common
    assert "replicaCount" in canary
    assert "replicaCount" in stable
    assert "image:" in stable


def test_readme_documents_multi_chat_model_configuration() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "VERTEX_CHAT_MODELS" in readme
    assert "VERTEX_CHAT_MODEL_ALIASES" in readme
    assert "genos-flash" in readme


def test_compatibility_doc_mentions_alias_and_raw_chat_model_support() -> None:
    compatibility = (PROJECT_ROOT / "docs" / "compatibility.md").read_text()

    assert "alias" in compatibility.lower()
    assert "raw model" in compatibility.lower()
    assert "single-model" in compatibility.lower()


def test_production_values_example_shows_multi_chat_model_settings() -> None:
    values = (PROJECT_ROOT / "charts/vertex-openai-proxy/examples/values-production.yaml").read_text()

    assert "vertexChatModel:" in values
    assert "vertexChatModels:" in values
    assert "vertexChatModelAliases:" in values
