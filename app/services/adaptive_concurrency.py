from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import quantiles
from time import time

from app.config import settings


STEP_LADDER = (4, 8, 12, 16)


@dataclass(slots=True)
class RequestOutcome:
    timestamp: float
    latency_ms: float
    success: bool
    retryable_failure: bool
    timed_out: bool


class AdaptiveConcurrencyController:
    def __init__(self) -> None:
        self._recent: deque[RequestOutcome] = deque()
        self._current_concurrency: int | None = None
        self._last_adjustment_at: float | None = None

    def get_effective_concurrency(self, *, base: int, adaptive_enabled: bool, adaptive_max: int) -> int:
        if not adaptive_enabled:
            return base

        ladder = self._build_ladder(base, adaptive_max)
        if self._current_concurrency not in ladder:
            self._current_concurrency = ladder[0]
        return self._current_concurrency

    def record_outcome(
        self,
        *,
        latency_ms: float,
        success: bool,
        retryable_failure: bool,
        timed_out: bool,
        base: int,
        adaptive_enabled: bool,
        adaptive_max: int,
        now: float | None = None,
    ) -> dict | None:
        timestamp = now if now is not None else time()
        self._recent.append(
            RequestOutcome(
                timestamp=timestamp,
                latency_ms=latency_ms,
                success=success,
                retryable_failure=retryable_failure,
                timed_out=timed_out,
            )
        )
        self._prune(timestamp)

        if not adaptive_enabled:
            return None

        ladder = self._build_ladder(base, adaptive_max)
        if self._current_concurrency not in ladder:
            self._current_concurrency = ladder[0]

        metrics = self.get_metrics(now=timestamp)
        if metrics["request_count"] < settings.embedding_adaptive_min_samples:
            return None

        if not self._cooldown_elapsed(timestamp):
            return None

        next_concurrency, reason = self._decide_next_concurrency(ladder, metrics)
        if next_concurrency == self._current_concurrency:
            return None

        previous = self._current_concurrency
        self._current_concurrency = next_concurrency
        self._last_adjustment_at = timestamp
        return {
            "previous_concurrency": previous,
            "new_concurrency": next_concurrency,
            "reason": reason,
            **metrics,
        }

    def get_metrics(self, *, now: float | None = None) -> dict[str, float | int]:
        timestamp = now if now is not None else time()
        self._prune(timestamp)
        request_count = len(self._recent)
        if request_count == 0:
            return {
                "request_count": 0,
                "failure_rate": 0.0,
                "timeout_rate": 0.0,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
            }

        failures = sum(1 for item in self._recent if item.retryable_failure)
        timeouts = sum(1 for item in self._recent if item.timed_out)
        latencies = [item.latency_ms for item in self._recent]
        avg_latency_ms = sum(latencies) / request_count
        p95_latency_ms = self._p95(latencies)
        return {
            "request_count": request_count,
            "failure_rate": failures / request_count,
            "timeout_rate": timeouts / request_count,
            "avg_latency_ms": round(avg_latency_ms, 3),
            "p95_latency_ms": round(p95_latency_ms, 3),
        }

    def reset(self) -> None:
        self._recent.clear()
        self._current_concurrency = None
        self._last_adjustment_at = None

    def _build_ladder(self, base: int, adaptive_max: int) -> list[int]:
        ceiling = max(base, adaptive_max)
        values = sorted(set([base, ceiling, *STEP_LADDER]))
        return [value for value in values if base <= value <= ceiling]

    def _prune(self, now: float) -> None:
        while len(self._recent) > settings.embedding_adaptive_window_size:
            self._recent.popleft()

        max_age = settings.embedding_adaptive_window_seconds
        while self._recent and now - self._recent[0].timestamp > max_age:
            self._recent.popleft()

    def _cooldown_elapsed(self, now: float) -> bool:
        if self._last_adjustment_at is None:
            return True
        return (now - self._last_adjustment_at) >= settings.embedding_adaptive_cooldown_seconds

    def _decide_next_concurrency(self, ladder: list[int], metrics: dict[str, float | int]) -> tuple[int, str | None]:
        current = self._current_concurrency if self._current_concurrency is not None else ladder[0]
        current_index = ladder.index(current)
        failure_rate = float(metrics["failure_rate"])
        timeout_rate = float(metrics["timeout_rate"])
        p95_latency_ms = float(metrics["p95_latency_ms"])

        should_downscale = (
            failure_rate > settings.embedding_adaptive_failure_rate_down_threshold
            or timeout_rate > 0.05
            or p95_latency_ms > settings.embedding_adaptive_latency_down_threshold_ms
        )
        if should_downscale and current_index > 0:
            if failure_rate > settings.embedding_adaptive_failure_rate_down_threshold:
                return ladder[current_index - 1], "retryable_failure_rate"
            if timeout_rate > 0.05:
                return ladder[current_index - 1], "timeout_rate"
            return ladder[current_index - 1], "p95_latency"

        should_upscale = (
            failure_rate <= settings.embedding_adaptive_failure_rate_up_threshold
            and timeout_rate == 0
            and p95_latency_ms < settings.embedding_adaptive_latency_up_threshold_ms
        )
        if should_upscale and current_index < len(ladder) - 1:
            return ladder[current_index + 1], "healthy_window"

        return current, None

    def _p95(self, latencies: list[float]) -> float:
        if len(latencies) == 1:
            return latencies[0]
        return quantiles(latencies, n=100, method="inclusive")[94]


adaptive_embedding_concurrency = AdaptiveConcurrencyController()
