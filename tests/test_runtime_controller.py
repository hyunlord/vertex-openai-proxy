from time import time

from app.config import settings
from app.runtime.controller import runtime_controller


def test_runtime_controller_enters_elevated_on_soft_latency(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "runtime_window_size", 50)
    monkeypatch.setattr(settings, "runtime_window_seconds", 60)
    monkeypatch.setattr(settings, "runtime_recovery_seconds", 0)
    monkeypatch.setattr(settings, "runtime_embeddings_soft_latency_ms", 10.0)
    monkeypatch.setattr(settings, "runtime_embeddings_hard_latency_ms", 1000.0)
    monkeypatch.setattr(settings, "runtime_soft_retryable_error_rate", 0.5)
    monkeypatch.setattr(settings, "runtime_hard_retryable_error_rate", 0.9)
    monkeypatch.setattr(settings, "runtime_soft_timeout_rate", 0.5)
    monkeypatch.setattr(settings, "runtime_hard_timeout_rate", 0.9)
    now = time()

    runtime_controller.request_started("embeddings")
    mode = runtime_controller.request_finished(
        endpoint="embeddings",
        latency_ms=50.0,
        status_code=200,
        retry_attempts=0,
        retryable_failure=False,
        timed_out=False,
        auth_failure=False,
        now=now,
    )

    assert mode == "elevated"
    assert runtime_controller.current_mode() == "elevated"
    snapshot = runtime_controller.snapshot()
    assert snapshot["mode_transitions"]["normal->elevated"] == 1
    assert "embeddings_p95_high" in snapshot["reasons"]


def test_runtime_controller_enters_degraded_on_hard_failure_rate(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "runtime_window_size", 50)
    monkeypatch.setattr(settings, "runtime_window_seconds", 60)
    monkeypatch.setattr(settings, "runtime_recovery_seconds", 0)
    monkeypatch.setattr(settings, "runtime_soft_retryable_error_rate", 0.2)
    monkeypatch.setattr(settings, "runtime_hard_retryable_error_rate", 0.1)
    monkeypatch.setattr(settings, "runtime_soft_timeout_rate", 0.5)
    monkeypatch.setattr(settings, "runtime_hard_timeout_rate", 0.9)
    monkeypatch.setattr(settings, "runtime_chat_soft_latency_ms", 1000.0)
    monkeypatch.setattr(settings, "runtime_chat_hard_latency_ms", 2000.0)
    now = time()

    for step in range(2):
        runtime_controller.request_started("chat")
        mode = runtime_controller.request_finished(
            endpoint="chat",
            latency_ms=100.0,
            status_code=503,
            retry_attempts=1,
            retryable_failure=True,
            timed_out=False,
            auth_failure=False,
            now=now + step,
        )

    assert mode == "degraded"
    assert runtime_controller.current_mode() == "degraded"
    snapshot = runtime_controller.snapshot()
    assert snapshot["mode_transitions"]["elevated->degraded"] == 0 or snapshot["mode_transitions"]["normal->degraded"] >= 1
    assert "retryable_error_rate_high" in snapshot["reasons"]
