from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.runtime.controller import runtime_controller
from app.schemas.openai_embeddings import EmbeddingRequest
from app.services.adaptive_concurrency import adaptive_embedding_concurrency
from app.services.http_client import (
    VertexUpstreamError,
    is_retryable_upstream_error,
    vertex_json_request,
)
from app.utils.logging import log_event


def build_embedding_url(model: str) -> str:
    return (
        f"https://{settings.vertex_embedding_location}-aiplatform.googleapis.com/v1/projects/"
        f"{settings.vertex_project_id}/locations/{settings.vertex_embedding_location}"
        f"/publishers/google/models/{model}:embedContent"
    )


async def _request_embedding_with_retry(text: str, model: str) -> tuple[dict[str, Any], int]:
    attempts = 0
    max_attempts = settings.embedding_retry_attempts + 1
    while True:
        try:
            response = await vertex_json_request(
                "POST",
                build_embedding_url(model),
                {"content": {"parts": [{"text": text}]}},
            )
            return response, attempts
        except VertexUpstreamError as exc:
            if attempts + 1 >= max_attempts or not is_retryable_upstream_error(exc):
                raise
            attempts += 1
            await asyncio.sleep(settings.embedding_retry_backoff_ms / 1000)


async def _embed_one(text: str, model: str) -> tuple[list[float], int]:
    response, retry_attempts = await _request_embedding_with_retry(text, model)
    embedding = response.get("embedding") if isinstance(response, dict) else None
    values = embedding.get("values") if isinstance(embedding, dict) else None
    if not isinstance(values, list):
        raise HTTPException(
            status_code=502,
            detail="Vertex embedding response must include embedding.values",
        )
    return _normalize_embedding_values(values), retry_attempts


def _normalize_embedding_values(values: list[Any]) -> list[float]:
    normalized: list[float] = []
    for value in values:
        if not isinstance(value, int | float):
            raise HTTPException(
                status_code=502,
                detail="Vertex embedding values must be numeric",
            )
        normalized.append(float(value))
    return normalized


def _estimate_prompt_tokens(texts: list[str]) -> int:
    # Vertex embedding responses do not currently provide prompt usage, so we expose
    # a stable split-based estimate rather than claiming an exact tokenizer count.
    return sum(len(text.split()) for text in texts)


async def _embed_many_fail_fast(
    texts: list[str],
    model: str,
    *,
    concurrency: int,
) -> tuple[list[list[float]], int]:
    semaphore = asyncio.Semaphore(concurrency)
    vectors: list[list[float] | None] = [None] * len(texts)
    retry_attempts: list[int] = [0] * len(texts)

    async def bounded_embed(index: int, text: str) -> None:
        async with semaphore:
            vector, item_retry_attempts = await _embed_one(text, model)
        vectors[index] = vector
        retry_attempts[index] = item_retry_attempts

    tasks = [asyncio.create_task(bounded_embed(index, text)) for index, text in enumerate(texts)]
    pending = set(tasks)

    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_EXCEPTION)

            first_error: BaseException | None = None
            for task in done:
                exc = task.exception()
                if exc is not None:
                    first_error = exc
                    break

            if first_error is not None:
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                raise first_error
    finally:
        remaining = [task for task in tasks if not task.done()]
        if remaining:
            for task in remaining:
                task.cancel()
            await asyncio.gather(*remaining, return_exceptions=True)

    if any(vector is None for vector in vectors):
        raise HTTPException(
            status_code=502,
            detail="Vertex embedding fan-out completed without all vectors",
        )

    return [vector for vector in vectors if vector is not None], sum(retry_attempts)


async def create_embedding_response(payload: EmbeddingRequest) -> dict:
    model = payload.resolved_model()
    texts = payload.normalized_input
    if len(texts) > settings.embedding_max_inputs_per_request:
        raise HTTPException(
            status_code=400,
            detail=(
                "Embedding input exceeds the maximum number of items per request: "
                f"{settings.embedding_max_inputs_per_request}"
            ),
        )

    started_at = perf_counter()
    upstream_status = 200
    retry_attempts = 0
    effective_concurrency = adaptive_embedding_concurrency.get_effective_concurrency(
        base=settings.embedding_max_concurrency,
        adaptive_enabled=settings.embedding_adaptive_concurrency,
        adaptive_max=effective_embedding_adaptive_max(),
    )
    success = False
    retryable_failure = False
    timed_out = False
    auth_failure = False
    try:
        vectors, retry_attempts = await _embed_many_fail_fast(
            texts,
            model,
            concurrency=effective_concurrency,
        )
        success = True
        return {
            "object": "list",
            "model": model,
            "data": [
                {
                    "object": "embedding",
                    "index": index,
                    "embedding": vector,
                }
                for index, vector in enumerate(vectors)
            ],
            "usage": {
                "prompt_tokens": _estimate_prompt_tokens(texts),
                "total_tokens": _estimate_prompt_tokens(texts),
            },
        }
    except VertexUpstreamError as exc:
        upstream_status = exc.status_code
        retryable_failure = is_retryable_upstream_error(exc)
        auth_failure = exc.status_code in {401, 403}
        raise
    except HTTPException as exc:
        upstream_status = exc.status_code
        timed_out = exc.status_code == 504
        raise
    except TimeoutError:
        upstream_status = 504
        retryable_failure = True
        timed_out = True
        raise
    except Exception:
        upstream_status = 500
        raise
    finally:
        request_latency_ms = round((perf_counter() - started_at) * 1000, 3)
        runtime_mode = runtime_controller.request_finished(
            endpoint="embeddings",
            latency_ms=request_latency_ms,
            status_code=upstream_status,
            retry_attempts=retry_attempts,
            retryable_failure=retryable_failure,
            timed_out=timed_out,
            auth_failure=auth_failure,
        )
        adjustment = adaptive_embedding_concurrency.record_outcome(
            latency_ms=request_latency_ms,
            success=success,
            retryable_failure=retryable_failure,
            timed_out=timed_out,
            base=settings.embedding_max_concurrency,
            adaptive_enabled=settings.embedding_adaptive_concurrency,
            adaptive_max=effective_embedding_adaptive_max(),
        )
        if adjustment is not None:
            log_event(
                "adaptive_concurrency_adjusted",
                operation="embeddings",
                configured_concurrency=settings.embedding_max_concurrency,
                effective_concurrency=adjustment["new_concurrency"],
                previous_concurrency=adjustment["previous_concurrency"],
                reason=adjustment["reason"],
                request_count=adjustment["request_count"],
                failure_rate=adjustment["failure_rate"],
                timeout_rate=adjustment["timeout_rate"],
                avg_latency_ms=adjustment["avg_latency_ms"],
                p95_latency_ms=adjustment["p95_latency_ms"],
            )
        log_event(
            "request_completed",
            operation="embeddings",
            endpoint="/v1/embeddings",
            model=model,
            mode="batch" if len(texts) > 1 else "single",
            runtime_mode=runtime_mode,
            input_count=len(texts),
            fanout_count=len(texts),
            adaptive_concurrency_enabled=settings.embedding_adaptive_concurrency,
            configured_concurrency=settings.embedding_max_concurrency,
            effective_concurrency=effective_concurrency,
            retry_attempts=retry_attempts,
            upstream_status=upstream_status,
            upstream_latency_ms=request_latency_ms,
        )


def effective_embedding_adaptive_max() -> int:
    runtime_mode = runtime_controller.current_mode()
    if not settings.runtime_adaptive_mode:
        return settings.embedding_adaptive_max_concurrency
    if runtime_mode == "degraded":
        return settings.embedding_max_concurrency
    if runtime_mode == "elevated":
        return min(settings.embedding_adaptive_max_concurrency, max(settings.embedding_max_concurrency, 8))
    return settings.embedding_adaptive_max_concurrency
