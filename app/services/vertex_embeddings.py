from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.schemas.openai_embeddings import EmbeddingRequest
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
    try:
        semaphore = asyncio.Semaphore(settings.embedding_max_concurrency)

        async def bounded_embed(text: str) -> tuple[list[float], int]:
            async with semaphore:
                return await _embed_one(text, model)

        results = await asyncio.gather(*[bounded_embed(text) for text in texts])
        vectors = [vector for vector, _ in results]
        retry_attempts = sum(item_retry_attempts for _, item_retry_attempts in results)
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
                "prompt_tokens": sum(len(text.split()) for text in texts),
                "total_tokens": sum(len(text.split()) for text in texts),
            },
        }
    except HTTPException as exc:
        upstream_status = exc.status_code
        raise
    except Exception:
        upstream_status = 500
        raise
    finally:
        log_event(
            "request_completed",
            operation="embeddings",
            endpoint="/v1/embeddings",
            model=model,
            mode="batch" if len(texts) > 1 else "single",
            input_count=len(texts),
            fanout_count=len(texts),
            retry_attempts=retry_attempts,
            upstream_status=upstream_status,
            upstream_latency_ms=round((perf_counter() - started_at) * 1000, 3),
        )
