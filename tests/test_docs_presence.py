from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_harness_docs_exist() -> None:
    for relative_path in [
        "docs/harness.md",
        "docs/release.md",
        "docs/infrastructure-blocker.md",
        "docs/operations-transition.md",
    ]:
        assert (PROJECT_ROOT / relative_path).exists()


def test_helm_example_values_exist() -> None:
    for relative_path in [
        "charts/vertex-openai-proxy/examples/values-small.yaml",
        "charts/vertex-openai-proxy/examples/values-balanced-hpa.yaml",
        "charts/vertex-openai-proxy/examples/values-heavy-ingestion.yaml",
    ]:
        assert (PROJECT_ROOT / relative_path).exists()
