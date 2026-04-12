from fastapi.testclient import TestClient
from time import time

from app.config import settings
from app.main import app
from app.runtime.controller import runtime_controller


client = TestClient(app)


def test_metrics_endpoint_exposes_runtime_mode_and_basic_gauges() -> None:
    runtime_controller.reset()
    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert 'vertex_proxy_runtime_mode{mode="normal"} 1' in body
    assert "vertex_proxy_runtime_ready 1" in body
    assert 'vertex_proxy_in_flight_requests{endpoint="chat"} 0' in body
    assert 'vertex_proxy_in_flight_requests{endpoint="embeddings"} 0' in body
    assert "vertex_proxy_effective_embedding_concurrency" in body
    assert "vertex_proxy_process_cpu_percent" in body
    assert "vertex_proxy_process_rss_mb" in body
    assert "vertex_proxy_process_max_rss_mb" in body
    assert "vertex_proxy_request_shed_total" in body


def test_metrics_include_transition_and_status_breakdown(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "runtime_window_size", 50)
    monkeypatch.setattr(settings, "runtime_window_seconds", 60)
    monkeypatch.setattr(settings, "runtime_recovery_seconds", 0)
    monkeypatch.setattr(settings, "runtime_embeddings_soft_latency_ms", 10.0)
    monkeypatch.setattr(settings, "runtime_embeddings_hard_latency_ms", 1000.0)
    now = time()

    runtime_controller.request_started("embeddings")
    runtime_controller.request_finished(
        endpoint="embeddings",
        latency_ms=50.0,
        status_code=200,
        retry_attempts=2,
        retryable_failure=False,
        timed_out=False,
        auth_failure=False,
        now=now,
    )

    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert 'vertex_proxy_runtime_mode{mode="elevated"} 1' in body
    assert 'vertex_proxy_runtime_mode_transitions_total{from_mode="normal",to_mode="elevated"} 1' in body
    assert 'vertex_proxy_request_status_recent{scope="embeddings",status_class="2xx"} 1' in body
    assert 'vertex_proxy_retry_count_recent{scope="embeddings"} 2' in body
