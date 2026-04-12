from time import time

import pytest

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


def test_runtime_controller_tracks_request_shed_reasons(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "runtime_adaptive_mode", True)
    monkeypatch.setattr(settings, "runtime_degraded_max_embedding_inputs", 2)
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

    rejection = runtime_controller.admission_check(endpoint="embeddings", input_count=3)
    assert rejection is not None
    assert rejection.reason == "degraded_input_count"
    snapshot = runtime_controller.snapshot()
    assert snapshot["request_shed"]["embeddings:degraded_input_count"] == 1


def test_admission_check_handles_inconsistent_internal_state_without_assert(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(
        runtime_controller,
        "_capacity_decision_locked",
        lambda *, endpoint, input_count: ("wait", None),
    )

    rejection = runtime_controller.admission_check(endpoint="chat")

    assert rejection is not None
    assert rejection.status_code == 503
    assert rejection.reason == "admission_state_inconsistent"


@pytest.mark.asyncio
async def test_acquire_request_slot_handles_inconsistent_internal_state_without_assert(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "queue_enabled", False)
    monkeypatch.setattr(
        runtime_controller,
        "_capacity_decision_locked",
        lambda *, endpoint, input_count: ("wait", None),
    )

    rejection = await runtime_controller.acquire_request_slot(endpoint="embeddings")

    assert rejection is not None
    assert rejection.status_code == 503
    assert rejection.reason == "admission_state_inconsistent"
