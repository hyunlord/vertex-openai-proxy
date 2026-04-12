from __future__ import annotations

import resource
import sys
from collections import deque
from dataclasses import dataclass
from statistics import quantiles
from threading import Lock
from time import time
from typing import Literal

from app.config import settings


EndpointName = Literal["chat", "embeddings"]
RuntimeMode = Literal["normal", "elevated", "degraded"]


@dataclass(slots=True)
class RequestOutcome:
    endpoint: EndpointName
    timestamp: float
    latency_ms: float
    retryable_failure: bool
    timed_out: bool
    auth_failure: bool


def _normalize_max_rss_mb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(usage / (1024 * 1024), 3)
    return round(usage / 1024, 3)


class RuntimeController:
    def __init__(self) -> None:
        self._recent: deque[RequestOutcome] = deque()
        self._lock = Lock()
        self._mode: RuntimeMode = "normal"
        self._last_mode_change_at: float | None = None
        self._in_flight_chat = 0
        self._in_flight_embeddings = 0

    def request_started(self, endpoint: EndpointName) -> None:
        with self._lock:
            if endpoint == "chat":
                self._in_flight_chat += 1
            else:
                self._in_flight_embeddings += 1

    def request_finished(
        self,
        *,
        endpoint: EndpointName,
        latency_ms: float,
        retryable_failure: bool,
        timed_out: bool,
        auth_failure: bool,
        now: float | None = None,
    ) -> RuntimeMode:
        timestamp = now if now is not None else time()
        with self._lock:
            if endpoint == "chat":
                self._in_flight_chat = max(0, self._in_flight_chat - 1)
            else:
                self._in_flight_embeddings = max(0, self._in_flight_embeddings - 1)

            self._recent.append(
                RequestOutcome(
                    endpoint=endpoint,
                    timestamp=timestamp,
                    latency_ms=latency_ms,
                    retryable_failure=retryable_failure,
                    timed_out=timed_out,
                    auth_failure=auth_failure,
                )
            )
            self._prune(timestamp)
            self._recompute_mode(timestamp)
            return self._mode

    def current_mode(self) -> RuntimeMode:
        with self._lock:
            return self._mode

    def snapshot(self) -> dict:
        now = time()
        with self._lock:
            self._prune(now)
            metrics = self._compute_metrics()
            return {
                "mode": self._mode,
                "adaptive_mode_enabled": settings.runtime_adaptive_mode,
                "in_flight": {
                    "chat": self._in_flight_chat,
                    "embeddings": self._in_flight_embeddings,
                },
                "metrics": metrics,
                "process": {
                    "max_rss_mb": _normalize_max_rss_mb(),
                },
            }

    def reset(self) -> None:
        with self._lock:
            self._recent.clear()
            self._mode = "normal"
            self._last_mode_change_at = None
            self._in_flight_chat = 0
            self._in_flight_embeddings = 0

    def _prune(self, now: float) -> None:
        while len(self._recent) > settings.runtime_window_size:
            self._recent.popleft()
        while self._recent and now - self._recent[0].timestamp > settings.runtime_window_seconds:
            self._recent.popleft()

    def _recompute_mode(self, now: float) -> None:
        metrics = self._compute_metrics()
        hard = self._is_hard_pressure(metrics)
        soft = self._is_soft_pressure(metrics)

        if hard:
            self._set_mode("degraded", now)
            return

        if soft:
            target: RuntimeMode = "elevated"
            if self._mode == "degraded" and not self._recovery_elapsed(now):
                return
            self._set_mode(target, now)
            return

        if self._mode == "degraded":
            if self._recovery_elapsed(now):
                self._set_mode("elevated", now)
            return

        if self._mode == "elevated":
            if self._recovery_elapsed(now):
                self._set_mode("normal", now)
            return

    def _recovery_elapsed(self, now: float) -> bool:
        if self._last_mode_change_at is None:
            return True
        return (now - self._last_mode_change_at) >= settings.runtime_recovery_seconds

    def _set_mode(self, mode: RuntimeMode, now: float) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self._last_mode_change_at = now

    def _compute_metrics(self) -> dict:
        return {
            "chat": self._endpoint_metrics("chat"),
            "embeddings": self._endpoint_metrics("embeddings"),
            "global": self._global_metrics(),
        }

    def _endpoint_metrics(self, endpoint: EndpointName) -> dict[str, float | int]:
        items = [item for item in self._recent if item.endpoint == endpoint]
        return self._metrics_for_items(items)

    def _global_metrics(self) -> dict[str, float | int]:
        return self._metrics_for_items(list(self._recent))

    def _metrics_for_items(self, items: list[RequestOutcome]) -> dict[str, float | int]:
        count = len(items)
        if count == 0:
            return {
                "request_count": 0,
                "retryable_error_rate": 0.0,
                "timeout_rate": 0.0,
                "auth_failure_rate": 0.0,
                "p95_latency_ms": 0.0,
            }
        retryable_errors = sum(1 for item in items if item.retryable_failure)
        timeouts = sum(1 for item in items if item.timed_out)
        auth_failures = sum(1 for item in items if item.auth_failure)
        latencies = [item.latency_ms for item in items]
        p95_latency_ms = latencies[0] if len(latencies) == 1 else quantiles(
            latencies, n=100, method="inclusive"
        )[94]
        return {
            "request_count": count,
            "retryable_error_rate": round(retryable_errors / count, 6),
            "timeout_rate": round(timeouts / count, 6),
            "auth_failure_rate": round(auth_failures / count, 6),
            "p95_latency_ms": round(p95_latency_ms, 3),
        }

    def _is_soft_pressure(self, metrics: dict) -> bool:
        chat = metrics["chat"]
        embeddings = metrics["embeddings"]
        global_metrics = metrics["global"]
        return (
            float(chat["p95_latency_ms"]) > settings.runtime_chat_soft_latency_ms
            or float(embeddings["p95_latency_ms"]) > settings.runtime_embeddings_soft_latency_ms
            or float(global_metrics["retryable_error_rate"]) > settings.runtime_soft_retryable_error_rate
            or float(global_metrics["timeout_rate"]) > settings.runtime_soft_timeout_rate
        )

    def _is_hard_pressure(self, metrics: dict) -> bool:
        chat = metrics["chat"]
        embeddings = metrics["embeddings"]
        global_metrics = metrics["global"]
        return (
            float(chat["p95_latency_ms"]) > settings.runtime_chat_hard_latency_ms
            or float(embeddings["p95_latency_ms"]) > settings.runtime_embeddings_hard_latency_ms
            or float(global_metrics["retryable_error_rate"]) > settings.runtime_hard_retryable_error_rate
            or float(global_metrics["timeout_rate"]) > settings.runtime_hard_timeout_rate
        )


runtime_controller = RuntimeController()
