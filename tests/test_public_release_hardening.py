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


def test_security_policy_exists_and_is_linked_from_readme() -> None:
    security = (PROJECT_ROOT / "SECURITY.md").read_text()
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "Security" in security
    assert "private vulnerability" in security.lower()
    assert "SECURITY.md" in readme


def test_code_of_conduct_exists_and_is_linked_from_readme() -> None:
    code_of_conduct = (PROJECT_ROOT / "CODE_OF_CONDUCT.md").read_text()
    readme = (PROJECT_ROOT / "README.md").read_text()

    assert "Code of Conduct" in code_of_conduct
    assert "respectful" in code_of_conduct.lower()
    assert "CODE_OF_CONDUCT.md" in readme


def test_issue_and_pr_templates_exist() -> None:
    bug_report = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md"
    feature_request = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md"
    issue_config = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml"
    pr_template = PROJECT_ROOT / ".github" / "pull_request_template.md"

    assert bug_report.exists()
    assert feature_request.exists()
    assert issue_config.exists()
    assert pr_template.exists()


def test_issue_template_config_disables_blank_issues_and_links_docs() -> None:
    issue_config = (PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text()

    assert "blank_issues_enabled: false" in issue_config
    assert "SECURITY.md" in issue_config
    assert "CONTRIBUTING.md" in issue_config


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


def test_raw_k8s_manifest_uses_runtime_probe_endpoints() -> None:
    deployment = (PROJECT_ROOT / "k8s/deployment.yaml").read_text()

    assert "path: /livez" in deployment
    assert "path: /readyz" in deployment
