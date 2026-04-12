import asyncio
from time import perf_counter, time

import pytest

from app.config import settings
from app.runtime.controller import runtime_controller


@pytest.mark.asyncio
async def test_chat_bounded_queue_waits_and_then_reserves_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "queue_enabled", True)
    monkeypatch.setattr(settings, "queue_disable_on_degraded", True)
    monkeypatch.setattr(settings, "chat_max_in_flight_requests", 1)
    monkeypatch.setattr(settings, "chat_queue_max_depth", 1)
    monkeypatch.setattr(settings, "chat_queue_max_wait_ms", 200)
    monkeypatch.setattr(settings, "queue_poll_interval_ms", 5)

    runtime_controller.request_started("chat")

    async def release_running_request() -> None:
        await asyncio.sleep(0.03)
        runtime_controller.request_finished(
            endpoint="chat",
            latency_ms=30.0,
            status_code=200,
            retry_attempts=0,
            retryable_failure=False,
            timed_out=False,
            auth_failure=False,
            now=time(),
        )

    releaser = asyncio.create_task(release_running_request())
    started = perf_counter()
    rejection = await runtime_controller.acquire_request_slot(endpoint="chat")
    waited_ms = (perf_counter() - started) * 1000

    assert rejection is None
    assert waited_ms >= 20
    snapshot = runtime_controller.snapshot()
    assert snapshot["in_flight"]["chat"] == 1
    assert snapshot["queue"]["chat"]["depth"] == 0
    assert snapshot["queue"]["chat"]["admitted_total"] == 1

    runtime_controller.request_finished(
        endpoint="chat",
        latency_ms=1.0,
        status_code=200,
        retry_attempts=0,
        retryable_failure=False,
        timed_out=False,
        auth_failure=False,
        now=time(),
    )
    await releaser


@pytest.mark.asyncio
async def test_embeddings_bounded_queue_times_out_when_capacity_never_frees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "queue_enabled", True)
    monkeypatch.setattr(settings, "embeddings_max_in_flight_requests", 1)
    monkeypatch.setattr(settings, "embeddings_queue_max_depth", 1)
    monkeypatch.setattr(settings, "embeddings_queue_max_wait_ms", 20)
    monkeypatch.setattr(settings, "queue_poll_interval_ms", 5)

    runtime_controller.request_started("embeddings")
    rejection = await runtime_controller.acquire_request_slot(endpoint="embeddings", input_count=2)

    assert rejection is not None
    assert rejection.status_code == 429
    assert rejection.reason == "queue_timeout"
    snapshot = runtime_controller.snapshot()
    assert snapshot["queue"]["embeddings"]["timeouts_total"] == 1
    assert snapshot["request_shed"]["embeddings:queue_timeout"] == 1

    runtime_controller.request_finished(
        endpoint="embeddings",
        latency_ms=1.0,
        status_code=200,
        retry_attempts=0,
        retryable_failure=False,
        timed_out=False,
        auth_failure=False,
        now=time(),
    )
