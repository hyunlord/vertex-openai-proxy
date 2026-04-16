from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth import require_internal_bearer_token
from app.config import settings
from app.errors import build_openai_error, extract_detail_message
from app.runtime.controller import runtime_controller
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.http_client import VertexUpstreamError
from app.services.vertex_chat import create_chat_completion, create_chat_completion_stream
from app.utils.logging import log_event

router = APIRouter()


def _shed_headers(status_code: int) -> dict[str, str] | None:
    if status_code != 429:
        return None
    return {"Retry-After": str(settings.queue_retry_after_seconds)}


def _stream_error_event(
    *,
    status_code: int,
    message: str,
    error_type: str | None = None,
    code: int | str | None = None,
) -> str:
    payload = build_openai_error(
        message=message,
        status_code=status_code,
        error_type=error_type,
        code=code,
    ).model_dump()
    return f"event: error\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def _safe_chat_stream(payload: ChatCompletionRequest) -> AsyncIterator[str]:
    try:
        async for chunk in create_chat_completion_stream(payload):
            yield chunk
    except VertexUpstreamError as exc:
        yield _stream_error_event(status_code=exc.status_code, message=exc.message)
        yield "data: [DONE]\n\n"
    except HTTPException as exc:
        yield _stream_error_event(
            status_code=exc.status_code,
            message=extract_detail_message(exc.detail),
        )
        yield "data: [DONE]\n\n"
    except TimeoutError:
        yield _stream_error_event(status_code=504, message="Upstream request timed out")
        yield "data: [DONE]\n\n"
    except Exception:
        yield _stream_error_event(status_code=500, message="Internal server error")
        yield "data: [DONE]\n\n"


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    payload: ChatCompletionRequest,
    _: None = Depends(require_internal_bearer_token),
) -> StreamingResponse | dict:
    payload.ensure_supported_model()
    requested_model = payload.requested_model()
    resolved_model = payload.resolved_model()
    rejection = await runtime_controller.acquire_request_slot(endpoint="chat")
    if rejection is not None:
        log_event(
            "request_shed",
            operation="chat",
            endpoint="/v1/chat/completions",
            model=resolved_model,
            requested_model=requested_model,
            reason=rejection.reason,
            runtime_mode=runtime_controller.current_mode(),
            stream=payload.stream,
        )
        raise HTTPException(
            status_code=rejection.status_code,
            detail=rejection.message,
            headers=_shed_headers(rejection.status_code),
        )
    if payload.stream:
        return StreamingResponse(
            _safe_chat_stream(payload),
            media_type="text/event-stream",
        )
    return await create_chat_completion(payload)
