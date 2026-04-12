from fastapi.testclient import TestClient
from time import time

from app.config import settings
from app.main import app
from app.runtime.controller import runtime_controller


client = TestClient(app)


def test_livez() -> None:
    response = client.get("/livez")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "vertex-openai-proxy"}


def test_health() -> None:
    runtime_controller.reset()
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ready"] is True
    assert payload["mode"] == "normal"
    assert payload["runtime_mode"] == "normal"
    assert payload["degraded"] is False
    assert payload["reasons"] == []
    assert payload["adaptive_mode_enabled"] in {True, False}
    assert payload["in_flight"] == {"chat": 0, "embeddings": 0}
    assert "process" in payload
    assert "recent_pressure" in payload
    assert "mode_transitions" in payload
    assert "request_shed" in payload


def test_readyz_returns_not_ready_when_degraded_and_policy_enabled(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "readiness_fail_on_degraded", True)
    monkeypatch.setattr(settings, "runtime_window_size", 50)
    monkeypatch.setattr(settings, "runtime_window_seconds", 60)
    monkeypatch.setattr(settings, "runtime_recovery_seconds", 0)
    monkeypatch.setattr(settings, "runtime_soft_retryable_error_rate", 0.5)
    monkeypatch.setattr(settings, "runtime_hard_retryable_error_rate", 0.1)
    now = time()

    for step in range(2):
        runtime_controller.request_started("chat")
        runtime_controller.request_finished(
            endpoint="chat",
            latency_ms=100.0,
            status_code=503,
            retry_attempts=1,
            retryable_failure=True,
            timed_out=False,
            auth_failure=False,
            now=now + step,
        )

    response = client.get("/readyz")
    assert response.status_code == 503
    payload = response.json()
    assert payload["ready"] is False
    assert payload["mode"] == "degraded"
    assert "retryable_error_rate_high" in payload["reasons"]


def test_runtimez_returns_detailed_runtime_snapshot() -> None:
    runtime_controller.reset()
    response = client.get("/runtimez")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "normal"
    assert "effective_limits" in payload
    assert "adaptive_metrics" in payload
    assert "process" in payload
    assert "queue" in payload
