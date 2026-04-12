from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.runtime.controller import runtime_controller

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
    lines = [
        "# HELP vertex_proxy_runtime_mode Current runtime mode",
        "# TYPE vertex_proxy_runtime_mode gauge",
        *_mode_lines(snapshot["mode"]),
        "# HELP vertex_proxy_in_flight_requests Current in-flight requests by endpoint",
        "# TYPE vertex_proxy_in_flight_requests gauge",
        f'vertex_proxy_in_flight_requests{{endpoint="chat"}} {snapshot["in_flight"]["chat"]}',
        f'vertex_proxy_in_flight_requests{{endpoint="embeddings"}} {snapshot["in_flight"]["embeddings"]}',
        "# HELP vertex_proxy_process_max_rss_mb Max RSS observed for this process in MB",
        "# TYPE vertex_proxy_process_max_rss_mb gauge",
        f'vertex_proxy_process_max_rss_mb {snapshot["process"]["max_rss_mb"]}',
    ]
    for endpoint in ("chat", "embeddings", "global"):
        metrics = snapshot["metrics"][endpoint]
        lines.extend(
            [
                f'vertex_proxy_request_count_recent{{scope="{endpoint}"}} {metrics["request_count"]}',
                f'vertex_proxy_retryable_error_rate{{scope="{endpoint}"}} {metrics["retryable_error_rate"]}',
                f'vertex_proxy_timeout_rate{{scope="{endpoint}"}} {metrics["timeout_rate"]}',
                f'vertex_proxy_auth_failure_rate{{scope="{endpoint}"}} {metrics["auth_failure_rate"]}',
                f'vertex_proxy_request_p95_latency_ms{{scope="{endpoint}"}} {metrics["p95_latency_ms"]}',
            ]
        )
    return PlainTextResponse("\n".join(lines) + "\n")
