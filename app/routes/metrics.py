from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.runtime.controller import runtime_controller
from app.services.adaptive_concurrency import adaptive_embedding_concurrency
from app.services.vertex_embeddings import effective_embedding_adaptive_max
from app.config import settings

router = APIRouter()


def _mode_lines(mode: str) -> list[str]:
    return [
        f'vertex_proxy_runtime_mode{{mode="normal"}} {1 if mode == "normal" else 0}',
        f'vertex_proxy_runtime_mode{{mode="elevated"}} {1 if mode == "elevated" else 0}',
        f'vertex_proxy_runtime_mode{{mode="degraded"}} {1 if mode == "degraded" else 0}',
    ]


@router.get("/metrics")
async def metrics() -> PlainTextResponse:
    snapshot = runtime_controller.snapshot()
    adaptive_metrics = adaptive_embedding_concurrency.get_metrics()
    effective_embedding_concurrency = adaptive_embedding_concurrency.get_effective_concurrency(
        base=settings.embedding_max_concurrency,
        adaptive_enabled=settings.embedding_adaptive_concurrency,
        adaptive_max=effective_embedding_adaptive_max(),
    )
    lines = [
        "# HELP vertex_proxy_runtime_mode Current runtime mode",
        "# TYPE vertex_proxy_runtime_mode gauge",
        *_mode_lines(snapshot["mode"]),
        "# HELP vertex_proxy_runtime_ready Current readiness state",
        "# TYPE vertex_proxy_runtime_ready gauge",
        f'vertex_proxy_runtime_ready {1 if snapshot["ready"] else 0}',
        "# HELP vertex_proxy_in_flight_requests Current in-flight requests by endpoint",
        "# TYPE vertex_proxy_in_flight_requests gauge",
        f'vertex_proxy_in_flight_requests{{endpoint="chat"}} {snapshot["in_flight"]["chat"]}',
        f'vertex_proxy_in_flight_requests{{endpoint="embeddings"}} {snapshot["in_flight"]["embeddings"]}',
        "# HELP vertex_proxy_effective_embedding_concurrency Current effective embedding concurrency",
        "# TYPE vertex_proxy_effective_embedding_concurrency gauge",
        f'vertex_proxy_effective_embedding_concurrency {effective_embedding_concurrency}',
        "# HELP vertex_proxy_process_cpu_percent Estimated process CPU percent",
        "# TYPE vertex_proxy_process_cpu_percent gauge",
        f'vertex_proxy_process_cpu_percent {snapshot["process"]["cpu_percent"]}',
        "# HELP vertex_proxy_process_rss_mb Process RSS estimate in MB",
        "# TYPE vertex_proxy_process_rss_mb gauge",
        f'vertex_proxy_process_rss_mb {snapshot["process"]["rss_mb"]}',
        "# HELP vertex_proxy_process_max_rss_mb Max RSS observed for this process in MB",
        "# TYPE vertex_proxy_process_max_rss_mb gauge",
        f'vertex_proxy_process_max_rss_mb {snapshot["process"]["max_rss_mb"]}',
        "# HELP vertex_proxy_runtime_mode_transitions_total Runtime mode transitions",
        "# TYPE vertex_proxy_runtime_mode_transitions_total counter",
    ]
    for transition, count in snapshot["mode_transitions"].items():
        from_mode, to_mode = transition.split("->", maxsplit=1)
        lines.extend(
            [
                f'vertex_proxy_runtime_mode_transitions_total{{from_mode="{from_mode}",to_mode="{to_mode}"}} {count}',
            ]
        )
    for endpoint in ("chat", "embeddings", "global"):
        metrics = snapshot["metrics"][endpoint]
        lines.extend(
            [
                f'vertex_proxy_request_count_recent{{scope="{endpoint}"}} {metrics["request_count"]}',
                f'vertex_proxy_retry_count_recent{{scope="{endpoint}"}} {metrics["retry_count"]}',
                f'vertex_proxy_request_status_recent{{scope="{endpoint}",status_class="2xx"}} {metrics["status_2xx_count"]}',
                f'vertex_proxy_request_status_recent{{scope="{endpoint}",status_class="4xx"}} {metrics["status_4xx_count"]}',
                f'vertex_proxy_request_status_recent{{scope="{endpoint}",status_class="5xx"}} {metrics["status_5xx_count"]}',
                f'vertex_proxy_retryable_error_rate{{scope="{endpoint}"}} {metrics["retryable_error_rate"]}',
                f'vertex_proxy_timeout_rate{{scope="{endpoint}"}} {metrics["timeout_rate"]}',
                f'vertex_proxy_auth_failure_rate{{scope="{endpoint}"}} {metrics["auth_failure_rate"]}',
                f'vertex_proxy_request_p95_latency_ms{{scope="{endpoint}"}} {metrics["p95_latency_ms"]}',
            ]
        )
    lines.extend(
        [
            "# HELP vertex_proxy_adaptive_request_count_recent Recent adaptive embedding request count",
            "# TYPE vertex_proxy_adaptive_request_count_recent gauge",
            f'vertex_proxy_adaptive_request_count_recent {adaptive_metrics["request_count"]}',
            "# HELP vertex_proxy_adaptive_failure_rate Recent adaptive embedding retryable failure rate",
            "# TYPE vertex_proxy_adaptive_failure_rate gauge",
            f'vertex_proxy_adaptive_failure_rate {adaptive_metrics["failure_rate"]}',
            "# HELP vertex_proxy_adaptive_timeout_rate Recent adaptive embedding timeout rate",
            "# TYPE vertex_proxy_adaptive_timeout_rate gauge",
            f'vertex_proxy_adaptive_timeout_rate {adaptive_metrics["timeout_rate"]}',
            "# HELP vertex_proxy_adaptive_p95_latency_ms Recent adaptive embedding p95 latency",
            "# TYPE vertex_proxy_adaptive_p95_latency_ms gauge",
            f'vertex_proxy_adaptive_p95_latency_ms {adaptive_metrics["p95_latency_ms"]}',
        ]
    )
    return PlainTextResponse("\n".join(lines) + "\n")
