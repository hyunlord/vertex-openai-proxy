from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.auth import require_internal_bearer_token
from app.config import settings
from app.runtime.controller import runtime_controller
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.vertex_chat import create_chat_completion, create_chat_completion_stream
from app.utils.logging import log_event

router = APIRouter()


def _shed_headers(status_code: int) -> dict[str, str] | None:
    if status_code != 429:
        return None
    return {"Retry-After": str(settings.queue_retry_after_seconds)}


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
            create_chat_completion_stream(payload),
            media_type="text/event-stream",
        )
    return await create_chat_completion(payload)
