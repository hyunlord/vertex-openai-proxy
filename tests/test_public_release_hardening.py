from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_chart_defaults_fail_closed_for_internal_bearer_token() -> None:
    values_text = (PROJECT_ROOT / "charts/vertex-openai-proxy/values.yaml").read_text()
    secret_template = (PROJECT_ROOT / "charts/vertex-openai-proxy/templates/secret.yaml").read_text()
    config_text = (PROJECT_ROOT / "app/config.py").read_text()

    assert "internalBearerToken: \"\"" in values_text
    assert 'internal_bearer_token: str = ""' in config_text
    assert 'fail "Set auth.internalBearerToken or auth.existingSecret before installing the chart."' in secret_template


def test_readme_avoids_maintainer_only_scaffolding_references() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert ".vertex-proxy" not in readme
    assert "docs/plans" not in readme


def test_gitignore_covers_sensitive_and_maintainer_only_assets() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text()

    assert "sa-key.json" in gitignore
    assert ".env" in gitignore
    assert ".vertex-proxy/" in gitignore
    assert "docs/plans/" in gitignore
