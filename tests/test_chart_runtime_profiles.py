from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_chart_values_define_runtime_profiles_and_autoscaling() -> None:
    values_text = (PROJECT_ROOT / "charts/vertex-openai-proxy/values.yaml").read_text()

    assert "profile: balanced" in values_text
    assert "profiles:" in values_text
    assert "small:" in values_text
    assert "balanced:" in values_text
    assert "heavy:" in values_text
    assert "autoscaling:" in values_text
    assert "targetCPUUtilizationPercentage" in values_text
    assert "targetMemoryUtilizationPercentage" in values_text


def test_chart_templates_reference_profiles_and_optional_hpa() -> None:
    helpers = (PROJECT_ROOT / "charts/vertex-openai-proxy/templates/_helpers.tpl").read_text()
    deployment = (PROJECT_ROOT / "charts/vertex-openai-proxy/templates/deployment.yaml").read_text()
    configmap = (PROJECT_ROOT / "charts/vertex-openai-proxy/templates/configmap.yaml").read_text()
    hpa = (PROJECT_ROOT / "charts/vertex-openai-proxy/templates/hpa.yaml").read_text()

    assert 'define "vertex-openai-proxy.selectedProfile"' in helpers
    assert 'define "vertex-openai-proxy.resources"' in helpers
    assert 'define "vertex-openai-proxy.embeddingMaxConcurrency"' in helpers
    assert "{{- if not .Values.autoscaling.enabled }}" in deployment
    assert 'include "vertex-openai-proxy.resources" . | nindent 12' in deployment
    assert 'include "vertex-openai-proxy.embeddingMaxConcurrency" .' in configmap
    assert "kind: HorizontalPodAutoscaler" in hpa
    assert ".Values.autoscaling.enabled" in hpa
