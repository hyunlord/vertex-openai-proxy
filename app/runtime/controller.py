from __future__ import annotations

import asyncio
import resource
import sys
from collections import deque
from dataclasses import dataclass
from statistics import quantiles
from threading import Lock
from time import process_time, time
from typing import Literal

from app.config import settings


EndpointName = Literal["chat", "embeddings"]
RuntimeMode = Literal["normal", "elevated", "degraded"]


@dataclass(slots=True)
class RequestOutcome:
    endpoint: EndpointName
    timestamp: float
    latency_ms: float
    status_code: int
    retry_attempts: int
    retryable_failure: bool
    timed_out: bool
    auth_failure: bool


@dataclass(slots=True)
class AdmissionRejection:
    endpoint: EndpointName
    reason: str
    status_code: int
    message: str


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
        self._mode_reasons: list[str] = []
        self._last_mode_change_at: float | None = None
        self._in_flight_chat = 0
        self._in_flight_embeddings = 0
        self._mode_transitions = {
            "normal->elevated": 0,
            "normal->degraded": 0,
            "elevated->normal": 0,
            "elevated->degraded": 0,
            "degraded->elevated": 0,
            "degraded->normal": 0,
        }
        self._request_shed = {
            "chat:absolute_in_flight_cap": 0,
            "chat:degraded_in_flight_cap": 0,
            "chat:queue_full": 0,
            "chat:queue_timeout": 0,
            "chat:queue_disabled_on_degraded": 0,
            "embeddings:absolute_in_flight_cap": 0,
            "embeddings:degraded_in_flight_cap": 0,
            "embeddings:degraded_input_count": 0,
            "embeddings:queue_full": 0,
            "embeddings:queue_timeout": 0,
            "embeddings:queue_disabled_on_degraded": 0,
        }
        self._queued_chat = 0
        self._queued_embeddings = 0
        self._queue_admitted_total = {"chat": 0, "embeddings": 0}
        self._queue_timeouts_total = {"chat": 0, "embeddings": 0}
        self._last_process_wall: float | None = None
        self._last_process_cpu: float | None = None
        self._cpu_percent: float = 0.0

    def admission_check(
        self,
        *,
        endpoint: EndpointName,
        input_count: int = 1,
    ) -> AdmissionRejection | None:
        with self._lock:
            decision, rejection = self._capacity_decision_locked(
                endpoint=endpoint,
                input_count=input_count,
            )
            if decision == "start":
                return None
            if rejection is not None and decision == "reject":
                return rejection
            if rejection is not None and decision == "wait":
                return self._record_rejection(
                    endpoint=endpoint,
                    reason=rejection.reason,
                    message=rejection.message,
                    status_code=rejection.status_code,
                )
            return self._unexpected_admission_state_rejection(
                endpoint=endpoint,
            )

    async def acquire_request_slot(
        self,
        *,
        endpoint: EndpointName,
        input_count: int = 1,
    ) -> AdmissionRejection | None:
        with self._lock:
            decision, rejection = self._capacity_decision_locked(
                endpoint=endpoint,
                input_count=input_count,
            )
            if decision == "start":
                self._request_started_locked(endpoint)
                return None
            if decision == "reject":
                return rejection
            if not settings.queue_enabled:
                if rejection is not None:
                    return self._record_rejection(
                        endpoint=endpoint,
                        reason=rejection.reason,
                        message=rejection.message,
                        status_code=rejection.status_code,
                    )
                return self._unexpected_admission_state_rejection(
                    endpoint=endpoint,
                )
            if settings.queue_disable_on_degraded and self._mode == "degraded":
                return self._record_rejection(
                    endpoint=endpoint,
                    reason="queue_disabled_on_degraded",
                    message="Request shed because bounded queueing is disabled while the service is degraded",
                )
            if self._queue_depth_locked(endpoint) >= self._queue_max_depth(endpoint):
                return self._record_rejection(
                    endpoint=endpoint,
                    reason="queue_full",
                    message="Request shed because the bounded queue is full",
                )
            self._set_queue_depth_locked(endpoint, self._queue_depth_locked(endpoint) + 1)

        deadline = time() + (self._queue_max_wait_ms(endpoint) / 1000)
        poll_interval = max(0.001, settings.queue_poll_interval_ms / 1000)
        while True:
            await asyncio.sleep(poll_interval)
            now = time()
            with self._lock:
                decision, rejection = self._capacity_decision_locked(
                    endpoint=endpoint,
                    input_count=input_count,
                )
                if decision == "start":
                    self._set_queue_depth_locked(endpoint, max(0, self._queue_depth_locked(endpoint) - 1))
                    self._queue_admitted_total[endpoint] += 1
                    self._request_started_locked(endpoint)
                    return None
                if decision == "reject":
                    self._set_queue_depth_locked(endpoint, max(0, self._queue_depth_locked(endpoint) - 1))
                    return rejection
                if settings.queue_disable_on_degraded and self._mode == "degraded":
                    self._set_queue_depth_locked(endpoint, max(0, self._queue_depth_locked(endpoint) - 1))
                    return self._record_rejection(
                        endpoint=endpoint,
                        reason="queue_disabled_on_degraded",
                        message="Request shed because bounded queueing is disabled while the service is degraded",
                    )
                if now >= deadline:
                    self._set_queue_depth_locked(endpoint, max(0, self._queue_depth_locked(endpoint) - 1))
                    self._queue_timeouts_total[endpoint] += 1
                    return self._record_rejection(
                        endpoint=endpoint,
                        reason="queue_timeout",
                        message="Request shed because the bounded queue wait budget expired before capacity became available",
                    )

    def request_started(self, endpoint: EndpointName) -> None:
        with self._lock:
            self._request_started_locked(endpoint)

    def request_finished(
        self,
        *,
        endpoint: EndpointName,
        latency_ms: float,
        status_code: int,
        retry_attempts: int,
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
                    status_code=status_code,
                    retry_attempts=retry_attempts,
                    retryable_failure=retryable_failure,
                    timed_out=timed_out,
                    auth_failure=auth_failure,
                )
            )
            self._prune(timestamp)
            process = self._sample_process_pressure(timestamp)
            self._recompute_mode(timestamp)
            self._refresh_mode_reasons(self._compute_metrics(), process)
            return self._mode

    def current_mode(self) -> RuntimeMode:
        with self._lock:
            return self._mode

    def snapshot(self) -> dict:
        now = time()
        with self._lock:
            self._prune(now)
            metrics = self._compute_metrics()
            process = self._sample_process_pressure(now)
            self._refresh_mode_reasons(metrics, process)
            ready = not (
                settings.readiness_fail_on_degraded and self._mode == "degraded"
            )
            return {
                "mode": self._mode,
                "reasons": list(self._mode_reasons),
                "adaptive_mode_enabled": settings.runtime_adaptive_mode,
                "queue_enabled": settings.queue_enabled,
                "ready": ready,
                "in_flight": {
                    "chat": self._in_flight_chat,
                    "embeddings": self._in_flight_embeddings,
                },
                "queue": {
                    "chat": {
                        "depth": self._queued_chat,
                        "max_depth": settings.chat_queue_max_depth,
                        "max_wait_ms": settings.chat_queue_max_wait_ms,
                        "admitted_total": self._queue_admitted_total["chat"],
                        "timeouts_total": self._queue_timeouts_total["chat"],
                    },
                    "embeddings": {
                        "depth": self._queued_embeddings,
                        "max_depth": settings.embeddings_queue_max_depth,
                        "max_wait_ms": settings.embeddings_queue_max_wait_ms,
                        "admitted_total": self._queue_admitted_total["embeddings"],
                        "timeouts_total": self._queue_timeouts_total["embeddings"],
                    },
                },
                "metrics": metrics,
                "process": {
                    "cpu_percent": process["cpu_percent"],
                    "rss_mb": process["rss_mb"],
                    "max_rss_mb": _normalize_max_rss_mb(),
                },
                "mode_transitions": dict(self._mode_transitions),
                "request_shed": dict(self._request_shed),
            }

    def reset(self) -> None:
        with self._lock:
            self._recent.clear()
            self._mode = "normal"
            self._mode_reasons = []
            self._last_mode_change_at = None
            self._in_flight_chat = 0
            self._in_flight_embeddings = 0
            self._mode_transitions = {key: 0 for key in self._mode_transitions}
            self._request_shed = {key: 0 for key in self._request_shed}
            self._queued_chat = 0
            self._queued_embeddings = 0
            self._queue_admitted_total = {"chat": 0, "embeddings": 0}
            self._queue_timeouts_total = {"chat": 0, "embeddings": 0}
            self._last_process_wall = None
            self._last_process_cpu = None
            self._cpu_percent = 0.0

    def _request_started_locked(self, endpoint: EndpointName) -> None:
        if endpoint == "chat":
            self._in_flight_chat += 1
        else:
            self._in_flight_embeddings += 1

    def _queue_depth_locked(self, endpoint: EndpointName) -> int:
        return self._queued_chat if endpoint == "chat" else self._queued_embeddings

    def _set_queue_depth_locked(self, endpoint: EndpointName, value: int) -> None:
        if endpoint == "chat":
            self._queued_chat = value
        else:
            self._queued_embeddings = value

    def _queue_max_depth(self, endpoint: EndpointName) -> int:
        return settings.chat_queue_max_depth if endpoint == "chat" else settings.embeddings_queue_max_depth

    def _queue_max_wait_ms(self, endpoint: EndpointName) -> int:
        return settings.chat_queue_max_wait_ms if endpoint == "chat" else settings.embeddings_queue_max_wait_ms

    def _prune(self, now: float) -> None:
        while len(self._recent) > settings.runtime_window_size:
            self._recent.popleft()
        while self._recent and now - self._recent[0].timestamp > settings.runtime_window_seconds:
            self._recent.popleft()

    def _recompute_mode(self, now: float) -> None:
        metrics = self._compute_metrics()
        process = self._sample_process_pressure(now)
        hard = self._is_hard_pressure(metrics, process)
        soft = self._is_soft_pressure(metrics, process)

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
        transition = f"{self._mode}->{mode}"
        if transition in self._mode_transitions:
            self._mode_transitions[transition] += 1
        self._mode = mode
        self._last_mode_change_at = now

    def _capacity_decision_locked(
        self,
        *,
        endpoint: EndpointName,
        input_count: int,
    ) -> tuple[Literal["start", "wait", "reject"], AdmissionRejection | None]:
        mode = self._mode
        if endpoint == "chat":
            if self._in_flight_chat >= settings.chat_max_in_flight_requests:
                return (
                    "wait",
                    AdmissionRejection(
                        endpoint="chat",
                        reason="absolute_in_flight_cap",
                        status_code=429,
                        message="Request shed because chat in-flight requests exceeded the configured cap",
                    ),
                )
            if (
                settings.runtime_adaptive_mode
                and mode == "degraded"
                and self._in_flight_chat >= settings.runtime_degraded_chat_max_in_flight
            ):
                return (
                    "wait",
                    AdmissionRejection(
                        endpoint="chat",
                        reason="degraded_in_flight_cap",
                        status_code=429,
                        message="Request shed because degraded-mode chat in-flight requests exceeded the configured cap",
                    ),
                )
            return "start", None

        if settings.runtime_adaptive_mode and mode == "degraded":
            if input_count > settings.runtime_degraded_max_embedding_inputs:
                return (
                    "reject",
                    self._record_rejection(
                        endpoint="embeddings",
                        reason="degraded_input_count",
                        message=(
                            "Request shed because degraded-mode embeddings input count exceeded the configured cap"
                        ),
                    ),
                )
            if self._in_flight_embeddings >= settings.runtime_degraded_embeddings_max_in_flight:
                return (
                    "wait",
                    AdmissionRejection(
                        endpoint="embeddings",
                        reason="degraded_in_flight_cap",
                        status_code=429,
                        message=(
                            "Request shed because degraded-mode embeddings in-flight requests exceeded the configured cap"
                        ),
                    ),
                )
        if self._in_flight_embeddings >= settings.embeddings_max_in_flight_requests:
            return (
                "wait",
                AdmissionRejection(
                    endpoint="embeddings",
                    reason="absolute_in_flight_cap",
                    status_code=429,
                    message="Request shed because embeddings in-flight requests exceeded the configured cap",
                ),
            )
        return "start", None

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
                "retry_count": 0,
                "status_2xx_count": 0,
                "status_4xx_count": 0,
                "status_5xx_count": 0,
                "retryable_error_rate": 0.0,
                "timeout_rate": 0.0,
                "auth_failure_rate": 0.0,
                "p95_latency_ms": 0.0,
            }
        retryable_errors = sum(1 for item in items if item.retryable_failure)
        timeouts = sum(1 for item in items if item.timed_out)
        auth_failures = sum(1 for item in items if item.auth_failure)
        retry_count = sum(item.retry_attempts for item in items)
        status_2xx_count = sum(1 for item in items if 200 <= item.status_code < 300)
        status_4xx_count = sum(1 for item in items if 400 <= item.status_code < 500)
        status_5xx_count = sum(1 for item in items if 500 <= item.status_code < 600)
        latencies = [item.latency_ms for item in items]
        p95_latency_ms = latencies[0] if len(latencies) == 1 else quantiles(
            latencies, n=100, method="inclusive"
        )[94]
        return {
            "request_count": count,
            "retry_count": retry_count,
            "status_2xx_count": status_2xx_count,
            "status_4xx_count": status_4xx_count,
            "status_5xx_count": status_5xx_count,
            "retryable_error_rate": round(retryable_errors / count, 6),
            "timeout_rate": round(timeouts / count, 6),
            "auth_failure_rate": round(auth_failures / count, 6),
            "p95_latency_ms": round(p95_latency_ms, 3),
        }

    def _is_soft_pressure(self, metrics: dict, process: dict[str, float]) -> bool:
        chat = metrics["chat"]
        embeddings = metrics["embeddings"]
        global_metrics = metrics["global"]
        return (
            self._in_flight_chat > settings.runtime_soft_in_flight_chat
            or self._in_flight_embeddings > settings.runtime_soft_in_flight_embeddings
            or float(chat["p95_latency_ms"]) > settings.runtime_chat_soft_latency_ms
            or float(embeddings["p95_latency_ms"]) > settings.runtime_embeddings_soft_latency_ms
            or float(global_metrics["retryable_error_rate"]) > settings.runtime_soft_retryable_error_rate
            or float(global_metrics["timeout_rate"]) > settings.runtime_soft_timeout_rate
            or float(process["cpu_percent"]) > (settings.runtime_hard_cpu_percent * 0.75)
            or float(process["rss_mb"]) > (settings.runtime_hard_rss_mb * 0.75)
        )

    def _is_hard_pressure(self, metrics: dict, process: dict[str, float]) -> bool:
        chat = metrics["chat"]
        embeddings = metrics["embeddings"]
        global_metrics = metrics["global"]
        return (
            self._in_flight_chat > settings.runtime_hard_in_flight_chat
            or self._in_flight_embeddings > settings.runtime_hard_in_flight_embeddings
            or float(chat["p95_latency_ms"]) > settings.runtime_chat_hard_latency_ms
            or float(embeddings["p95_latency_ms"]) > settings.runtime_embeddings_hard_latency_ms
            or float(global_metrics["retryable_error_rate"]) > settings.runtime_hard_retryable_error_rate
            or float(global_metrics["timeout_rate"]) > settings.runtime_hard_timeout_rate
            or float(process["cpu_percent"]) > settings.runtime_hard_cpu_percent
            or float(process["rss_mb"]) > settings.runtime_hard_rss_mb
        )

    def _sample_process_pressure(self, now: float) -> dict[str, float]:
        cpu_now = process_time()
        if self._last_process_wall is None or self._last_process_cpu is None:
            self._last_process_wall = now
            self._last_process_cpu = cpu_now
            self._cpu_percent = 0.0
        else:
            wall_delta = now - self._last_process_wall
            cpu_delta = cpu_now - self._last_process_cpu
            if wall_delta > 0:
                self._cpu_percent = round(max(0.0, (cpu_delta / wall_delta) * 100), 3)
            self._last_process_wall = now
            self._last_process_cpu = cpu_now
        rss_mb = _normalize_max_rss_mb()
        return {
            "cpu_percent": self._cpu_percent,
            "rss_mb": rss_mb,
        }

    def _record_rejection(
        self,
        *,
        endpoint: EndpointName,
        reason: str,
        message: str,
        status_code: int = 429,
    ) -> AdmissionRejection:
        key = f"{endpoint}:{reason}"
        self._request_shed[key] = self._request_shed.get(key, 0) + 1
        return AdmissionRejection(
            endpoint=endpoint,
            reason=reason,
            status_code=status_code,
            message=message,
        )

    def _unexpected_admission_state_rejection(
        self,
        *,
        endpoint: EndpointName,
    ) -> AdmissionRejection:
        return self._record_rejection(
            endpoint=endpoint,
            reason="admission_state_inconsistent",
            message="Request shed because admission control encountered an inconsistent internal state",
            status_code=503,
        )

    def _refresh_mode_reasons(self, metrics: dict, process: dict[str, float]) -> None:
        reasons: list[str] = []
        chat = metrics["chat"]
        embeddings = metrics["embeddings"]
        global_metrics = metrics["global"]
        if self._in_flight_chat > settings.runtime_soft_in_flight_chat:
            reasons.append("chat_in_flight_high")
        if self._in_flight_embeddings > settings.runtime_soft_in_flight_embeddings:
            reasons.append("embeddings_in_flight_high")
        if float(chat["p95_latency_ms"]) > settings.runtime_chat_soft_latency_ms:
            reasons.append("chat_p95_high")
        if float(embeddings["p95_latency_ms"]) > settings.runtime_embeddings_soft_latency_ms:
            reasons.append("embeddings_p95_high")
        if float(global_metrics["retryable_error_rate"]) > settings.runtime_soft_retryable_error_rate:
            reasons.append("retryable_error_rate_high")
        if float(global_metrics["timeout_rate"]) > settings.runtime_soft_timeout_rate:
            reasons.append("timeout_rate_high")
        if float(process["cpu_percent"]) > (settings.runtime_hard_cpu_percent * 0.75):
            reasons.append("cpu_pressure_high")
        if float(process["rss_mb"]) > (settings.runtime_hard_rss_mb * 0.75):
            reasons.append("rss_pressure_high")
        self._mode_reasons = reasons


runtime_controller = RuntimeController()
