from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.runtime.controller import runtime_controller
from app.services.adaptive_concurrency import adaptive_embedding_concurrency
from app.services.vertex_embeddings import effective_embedding_adaptive_max

router = APIRouter()


def _runtime_payload() -> dict:
    snapshot = runtime_controller.snapshot()
    embedding_metrics = adaptive_embedding_concurrency.get_metrics()
    effective_embedding_concurrency = adaptive_embedding_concurrency.get_effective_concurrency(
        base=settings.embedding_max_concurrency,
        adaptive_enabled=settings.embedding_adaptive_concurrency,
        adaptive_max=effective_embedding_adaptive_max(),
    )
    return {
        "status": "ok",
        "ready": snapshot["ready"],
        "mode": snapshot["mode"],
        "runtime_mode": snapshot["mode"],
        "degraded": snapshot["mode"] == "degraded",
        "reasons": snapshot["reasons"],
        "adaptive_mode_enabled": snapshot["adaptive_mode_enabled"],
        "in_flight": snapshot["in_flight"],
        "effective_limits": {
            "embedding_concurrency": effective_embedding_concurrency,
        },
        "recent_pressure": {
            "chat_p95_latency_ms": snapshot["metrics"]["chat"]["p95_latency_ms"],
            "embeddings_p95_latency_ms": snapshot["metrics"]["embeddings"]["p95_latency_ms"],
            "retryable_error_rate": snapshot["metrics"]["global"]["retryable_error_rate"],
            "timeout_rate": snapshot["metrics"]["global"]["timeout_rate"],
        },
        "adaptive_metrics": embedding_metrics,
        "process": snapshot["process"],
        "mode_transitions": snapshot["mode_transitions"],
    }


@router.get("/livez")
async def livez() -> dict:
    return {"status": "ok", "service": settings.app_name}


@router.get("/readyz")
async def readyz() -> JSONResponse:
    payload = _runtime_payload()
    status_code = 200 if payload["ready"] else 503
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/runtimez")
async def runtimez() -> dict:
    return _runtime_payload()


@router.get("/health")
async def health() -> dict:
    return _runtime_payload()
