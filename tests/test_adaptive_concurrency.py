from app.config import settings
from app.services.adaptive_concurrency import AdaptiveConcurrencyController


def test_adaptive_controller_scales_up_after_healthy_window(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_adaptive_window_size", 20)
    monkeypatch.setattr(settings, "embedding_adaptive_window_seconds", 60)
    monkeypatch.setattr(settings, "embedding_adaptive_cooldown_seconds", 30)
    monkeypatch.setattr(settings, "embedding_adaptive_min_samples", 5)
    monkeypatch.setattr(settings, "embedding_adaptive_latency_up_threshold_ms", 4000.0)
    monkeypatch.setattr(settings, "embedding_adaptive_failure_rate_up_threshold", 0.01)

    controller = AdaptiveConcurrencyController()
    base = 4
    adaptive_max = 16
    assert controller.get_effective_concurrency(
        base=base,
        adaptive_enabled=True,
        adaptive_max=adaptive_max,
    ) == 4

    base_now = 1000.0
    adjustment = None
    for index in range(5):
        adjustment = controller.record_outcome(
            latency_ms=1500.0,
            success=True,
            retryable_failure=False,
            timed_out=False,
            base=base,
            adaptive_enabled=True,
            adaptive_max=adaptive_max,
            now=base_now + (index * 10),
        )

    assert adjustment is not None
    assert adjustment["reason"] == "healthy_window"
    assert controller.get_effective_concurrency(
        base=base,
        adaptive_enabled=True,
        adaptive_max=adaptive_max,
    ) == 8


def test_adaptive_controller_scales_down_after_failure_window(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_adaptive_window_size", 20)
    monkeypatch.setattr(settings, "embedding_adaptive_window_seconds", 60)
    monkeypatch.setattr(settings, "embedding_adaptive_cooldown_seconds", 0)
    monkeypatch.setattr(settings, "embedding_adaptive_min_samples", 5)
    monkeypatch.setattr(settings, "embedding_adaptive_latency_up_threshold_ms", 4000.0)
    monkeypatch.setattr(settings, "embedding_adaptive_failure_rate_up_threshold", 0.01)
    monkeypatch.setattr(settings, "embedding_adaptive_failure_rate_down_threshold", 0.10)

    controller = AdaptiveConcurrencyController()
    base = 4
    adaptive_max = 16
    now = 1000.0
    for index in range(10):
        controller.record_outcome(
            latency_ms=1200.0,
            success=True,
            retryable_failure=False,
            timed_out=False,
            base=base,
            adaptive_enabled=True,
            adaptive_max=adaptive_max,
            now=now + (index * 5),
        )

    assert controller.get_effective_concurrency(
        base=base,
        adaptive_enabled=True,
        adaptive_max=adaptive_max,
    ) >= 8

    adjustment = None
    failure_now = 2000.0
    for index in range(5):
        adjustment = controller.record_outcome(
            latency_ms=9000.0,
            success=False,
            retryable_failure=True,
            timed_out=index == 0,
            base=base,
            adaptive_enabled=True,
            adaptive_max=adaptive_max,
            now=failure_now + index,
        )

    assert adjustment is not None
    assert adjustment["reason"] in {"retryable_failure_rate", "timeout_rate", "p95_latency"}
    assert controller.get_effective_concurrency(
        base=base,
        adaptive_enabled=True,
        adaptive_max=adaptive_max,
    ) >= 4


def test_adaptive_controller_respects_cooldown(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_adaptive_window_size", 20)
    monkeypatch.setattr(settings, "embedding_adaptive_window_seconds", 60)
    monkeypatch.setattr(settings, "embedding_adaptive_cooldown_seconds", 60)
    monkeypatch.setattr(settings, "embedding_adaptive_min_samples", 5)

    controller = AdaptiveConcurrencyController()
    base = 4
    adaptive_max = 16
    first_adjustment = None
    for index in range(5):
        first_adjustment = controller.record_outcome(
            latency_ms=1000.0,
            success=True,
            retryable_failure=False,
            timed_out=False,
            base=base,
            adaptive_enabled=True,
            adaptive_max=adaptive_max,
            now=1000.0 + (index * 10),
        )

    assert first_adjustment is not None
    no_adjustment = controller.record_outcome(
        latency_ms=1000.0,
        success=True,
        retryable_failure=False,
        timed_out=False,
        base=base,
        adaptive_enabled=True,
        adaptive_max=adaptive_max,
        now=1000.0 + 41,
    )
    assert no_adjustment is None


def test_adaptive_controller_disabled_returns_fixed_concurrency() -> None:
    controller = AdaptiveConcurrencyController()

    assert controller.get_effective_concurrency(
        base=6,
        adaptive_enabled=False,
        adaptive_max=16,
    ) == 6

    adjustment = controller.record_outcome(
        latency_ms=1000.0,
        success=True,
        retryable_failure=False,
        timed_out=False,
        base=6,
        adaptive_enabled=False,
        adaptive_max=16,
        now=1000.0,
    )
    assert adjustment is None
