from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from app.config import settings
from app.schemas.openai_embeddings import EmbeddingRequest
from app.services.http_client import vertex_json_request
from app.utils.logging import log_event


def build_embedding_url(model: str) -> str:
    return (
        f"https://{settings.vertex_embedding_location}-aiplatform.googleapis.com/v1/projects/"
        f"{settings.vertex_project_id}/locations/{settings.vertex_embedding_location}"
        f"/publishers/google/models/{model}:embedContent"
    )


async def _embed_one(text: str, model: str) -> list[float]:
    response = await vertex_json_request(
        "POST",
        build_embedding_url(model),
        {"content": {"parts": [{"text": text}]}},
    )
    embedding = response.get("embedding") if isinstance(response, dict) else None
    values = embedding.get("values") if isinstance(embedding, dict) else None
    if not isinstance(values, list):
        raise HTTPException(
            status_code=502,
            detail="Vertex embedding response must include embedding.values",
        )
    return _normalize_embedding_values(values)


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
    started_at = perf_counter()
    upstream_status = 200
    try:
        vectors = await asyncio.gather(*[_embed_one(text, model) for text in texts])
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
            upstream_status=upstream_status,
            upstream_latency_ms=round((perf_counter() - started_at) * 1000, 3),
        )
