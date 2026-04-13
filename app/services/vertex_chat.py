from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.config import settings
from app.schemas.openai_chat import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionUsage,
)
from app.schemas.openai_stream import (
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
)
from app.runtime.controller import runtime_controller
from app.services.http_client import (
    VertexUpstreamError,
    is_retryable_upstream_error,
    vertex_json_request,
    vertex_stream_request,
)
from app.utils.logging import log_event


def build_chat_url() -> str:
    return (
        "https://aiplatform.googleapis.com/v1/projects/"
        f"{settings.vertex_project_id}/locations/{settings.vertex_chat_location}"
        "/endpoints/openapi/chat/completions"
    )


def _normalize_choice(choice: Any, index: int) -> ChatCompletionChoice:
    if not isinstance(choice, dict):
        raise HTTPException(status_code=502, detail="Vertex chat response choices must be objects")

    message = choice.get("message")
    if isinstance(message, dict):
        message_payload = {
            "role": message.get("role") or "assistant",
            "content": message.get("content"),
        }
    else:
        message_payload = {
            "role": "assistant",
            "content": choice.get("content"),
        }

    normalized_choice = {
        "index": choice.get("index", index),
        "message": message_payload,
        "finish_reason": choice.get("finish_reason"),
        "logprobs": choice.get("logprobs"),
    }
    return ChatCompletionChoice.model_validate(normalized_choice)


def _normalize_stream_choice(choice: Any, index: int) -> ChatCompletionChunkChoice:
    if not isinstance(choice, dict):
        raise HTTPException(status_code=502, detail="Vertex chat stream choices must be objects")

    delta = choice.get("delta")
    if isinstance(delta, dict):
        delta_payload = {
            "role": delta.get("role"),
            "content": delta.get("content"),
        }
    else:
        message = choice.get("message")
        if isinstance(message, dict):
            delta_payload = {
                "role": message.get("role") or "assistant",
                "content": message.get("content"),
            }
        else:
            delta_payload = {
                "role": "assistant" if index == 0 else None,
                "content": choice.get("content"),
            }

    normalized_choice = {
        "index": choice.get("index", index),
        "delta": delta_payload,
        "finish_reason": choice.get("finish_reason"),
        "logprobs": choice.get("logprobs"),
    }
    return ChatCompletionChunkChoice.model_validate(normalized_choice)


def normalize_chat_completion_response(
    response: dict[str, Any],
    *,
    model: str,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "id": response.get("id") or f"chatcmpl-{uuid4().hex}",
        "object": "chat.completion",
        "created": int(response.get("created") or time.time()),
        "model": response.get("model") or model,
        "choices": [
            _normalize_choice(choice, index=index).model_dump(exclude_none=True)
            for index, choice in enumerate(response.get("choices", []))
        ],
    }

    usage = response.get("usage")
    if isinstance(usage, dict):
        normalized["usage"] = ChatCompletionUsage.model_validate(usage).model_dump(
            exclude_none=True
        )

    return ChatCompletionResponse.model_validate(normalized).model_dump(exclude_none=True)


def normalize_chat_stream_chunk(
    response: dict[str, Any],
    *,
    model: str,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "id": response.get("id") or f"chatcmpl-{uuid4().hex}",
        "object": "chat.completion.chunk",
        "created": int(response.get("created") or time.time()),
        "model": response.get("model") or model,
        "choices": [
            _normalize_stream_choice(choice, index=index).model_dump(exclude_none=True)
            for index, choice in enumerate(response.get("choices", []))
        ],
    }

    usage = response.get("usage")
    if isinstance(usage, dict):
        normalized["usage"] = ChatCompletionUsage.model_validate(usage).model_dump(
            exclude_none=True
        )

    return ChatCompletionChunk.model_validate(normalized).model_dump(exclude_none=True)


def _parse_stream_payload(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(":") or stripped.startswith("event:"):
        return None
    if stripped.startswith("data:"):
        return stripped[len("data:") :].strip()
    return stripped


async def create_chat_completion_stream(payload: ChatCompletionRequest) -> AsyncIterator[str]:
    requested_model = payload.requested_model()
    resolved_model = payload.resolved_model()
    body = payload.model_dump(exclude_none=True)
    body["model"] = resolved_model
    saw_done = False
    started_at = perf_counter()
    upstream_status = 200
    retryable_failure = False
    timed_out = False
    auth_failure = False
    try:
        async for line in vertex_stream_request("POST", build_chat_url(), body):
            data = _parse_stream_payload(line)
            if data is None:
                continue
            if data == "[DONE]":
                saw_done = True
                break

            try:
                upstream_chunk = json.loads(data)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=502, detail="Vertex chat stream emitted invalid JSON"
                ) from exc

            if not isinstance(upstream_chunk, dict):
                raise HTTPException(
                    status_code=502, detail="Vertex chat stream chunks must be JSON objects"
                )

            normalized_chunk = normalize_chat_stream_chunk(upstream_chunk, model=resolved_model)
            yield f"data: {json.dumps(normalized_chunk, separators=(',', ':'))}\n\n"
    except VertexUpstreamError as exc:
        upstream_status = exc.status_code
        retryable_failure = is_retryable_upstream_error(exc)
        auth_failure = exc.status_code in {401, 403}
        raise
    except HTTPException as exc:
        upstream_status = exc.status_code
        timed_out = exc.status_code == 504
        raise
    except Exception:
        upstream_status = 500
        raise
    finally:
        request_latency_ms = round((perf_counter() - started_at) * 1000, 3)
        runtime_mode = runtime_controller.request_finished(
            endpoint="chat",
            latency_ms=request_latency_ms,
            status_code=upstream_status,
            retry_attempts=0,
            retryable_failure=retryable_failure,
            timed_out=timed_out,
            auth_failure=auth_failure,
        )
        log_event(
            "request_completed",
            operation="chat",
            endpoint="/v1/chat/completions",
            model=resolved_model,
            requested_model=requested_model,
            mode="stream",
            runtime_mode=runtime_mode,
            upstream_status=upstream_status,
            upstream_latency_ms=request_latency_ms,
        )

    yield "data: [DONE]\n\n"


async def create_chat_completion(payload: ChatCompletionRequest) -> dict:
    requested_model = payload.requested_model()
    resolved_model = payload.resolved_model()
    body = payload.model_dump(exclude_none=True)
    body["model"] = resolved_model
    started_at = perf_counter()
    upstream_status = 200
    retry_attempts = 0
    retryable_failure = False
    timed_out = False
    auth_failure = False
    try:
        response = await _chat_request_with_retry(body)
        retry_attempts = response[1]
        response = response[0]
        if not isinstance(response, dict):
            raise HTTPException(status_code=502, detail="Vertex chat response must be a JSON object")
        return normalize_chat_completion_response(response, model=resolved_model)
    except VertexUpstreamError as exc:
        upstream_status = exc.status_code
        retryable_failure = is_retryable_upstream_error(exc)
        auth_failure = exc.status_code in {401, 403}
        raise
    except HTTPException as exc:
        upstream_status = exc.status_code
        timed_out = exc.status_code == 504
        raise
    except Exception:
        upstream_status = 500
        raise
    finally:
        request_latency_ms = round((perf_counter() - started_at) * 1000, 3)
        runtime_mode = runtime_controller.request_finished(
            endpoint="chat",
            latency_ms=request_latency_ms,
            status_code=upstream_status,
            retry_attempts=retry_attempts,
            retryable_failure=retryable_failure,
            timed_out=timed_out,
            auth_failure=auth_failure,
        )
        log_event(
            "request_completed",
            operation="chat",
            endpoint="/v1/chat/completions",
            model=resolved_model,
            requested_model=requested_model,
            mode="non_stream",
            runtime_mode=runtime_mode,
            retry_attempts=retry_attempts,
            upstream_status=upstream_status,
            upstream_latency_ms=request_latency_ms,
        )


async def _chat_request_with_retry(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    attempts = 0
    runtime_mode = runtime_controller.current_mode()
    if settings.runtime_adaptive_mode and runtime_mode == "degraded":
        max_attempts = 1
    elif settings.runtime_adaptive_mode and runtime_mode == "elevated":
        max_attempts = max(1, settings.chat_retry_attempts)
    else:
        max_attempts = settings.chat_retry_attempts + 1
    while True:
        try:
            response = await vertex_json_request("POST", build_chat_url(), body)
            return response, attempts
        except VertexUpstreamError as exc:
            if attempts + 1 >= max_attempts or not is_retryable_upstream_error(exc):
                raise
            attempts += 1
            await asyncio.sleep(settings.chat_retry_backoff_ms / 1000)
