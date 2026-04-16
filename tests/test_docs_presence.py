from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_harness_docs_exist() -> None:
    for relative_path in [
        "CHANGELOG.md",
        "docs/alerts.md",
        "docs/canary-checklist.md",
        "docs/configuration.md",
        "docs/harness.md",
        "docs/private-handoff.md",
        "docs/quickstart.md",
        "docs/release.md",
        "docs/runbook.md",
        "docs/validation.md",
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
    assert "vertexChatModels:" in common
    assert "vertexChatModelAliases:" in common
    assert "genos-flash" in common
    assert "genos-pro" in common
    assert "replicaCount" in canary
    assert "fullnameOverride: vertex-openai-proxy-canary" in canary
    assert "replicaCount" in stable
    assert "fullnameOverride: vertex-openai-proxy-stable" in stable
    assert "image:" in stable


def test_readme_documents_multi_chat_model_configuration() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "VERTEX_CHAT_MODELS" in readme
    assert "VERTEX_CHAT_MODEL_ALIASES" in readme
    assert "genos-flash" in readme


def test_readme_points_first_time_users_to_quickstart() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "docs/quickstart.md" in readme
    assert "runbook" in readme.lower()
    assert "docs/configuration.md" in readme
    assert "docs/validation.md" in readme


def test_quickstart_covers_local_and_helm_paths() -> None:
    quickstart = (PROJECT_ROOT / "docs" / "quickstart.md").read_text()

    assert "cp .env.example .env" in quickstart
    assert "uvicorn app.main:app" in quickstart
    assert "helm upgrade --install" in quickstart
    assert "INTERNAL_BEARER_TOKEN" in quickstart


def test_configuration_doc_splits_core_and_advanced_settings() -> None:
    configuration = (PROJECT_ROOT / "docs" / "configuration.md").read_text()

    assert "Core Settings" in configuration
    assert "Advanced Runtime Settings" in configuration
    assert "INTERNAL_BEARER_TOKEN" in configuration
    assert "QUEUE_ENABLED" in configuration


def test_validation_doc_covers_vm_and_in_cluster_paths() -> None:
    validation = (PROJECT_ROOT / "docs" / "validation.md").read_text()

    assert "smoke_vm_direct.py" in validation
    assert "smoke_in_cluster.py" in validation
    assert "Workload Identity" in validation
    assert "tool calling" in validation.lower()


def test_compatibility_doc_mentions_alias_and_raw_chat_model_support() -> None:
    compatibility = (PROJECT_ROOT / "docs" / "compatibility.md").read_text()

    assert "alias" in compatibility.lower()
    assert "raw model" in compatibility.lower()
    assert "single-model" in compatibility.lower()
    assert "examples/curl/tool_calling.sh" in compatibility
    assert "examples/python/tool_calling.py" in compatibility


def test_docs_describe_embeddings_usage_as_approximate() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()
    compatibility = (PROJECT_ROOT / "docs" / "compatibility.md").read_text()

    assert "approximate" in readme.lower()
    assert "embeddings" in readme.lower()
    assert "approximate" in compatibility.lower()
    assert "usage" in compatibility.lower()


def test_production_values_example_shows_multi_chat_model_settings() -> None:
    values = (PROJECT_ROOT / "charts/vertex-openai-proxy/examples/values-production.yaml").read_text()

    assert "vertexChatModel:" in values
    assert "vertexChatModels:" in values
    assert "vertexChatModelAliases:" in values


def test_tool_calling_examples_exist_and_are_linked() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert (PROJECT_ROOT / "examples/curl/tool_calling.sh").exists()
    assert (PROJECT_ROOT / "examples/python/tool_calling.py").exists()
    assert "examples/curl/tool_calling.sh" in readme
    assert "examples/python/tool_calling.py" in readme
