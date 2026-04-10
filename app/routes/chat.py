from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import require_internal_bearer_token
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.vertex_chat import create_chat_completion, create_chat_completion_stream

router = APIRouter()


@router.post("/v1/chat/completions", response_model=None)
async def chat_completions(
    payload: ChatCompletionRequest,
    _: None = Depends(require_internal_bearer_token),
) -> StreamingResponse | dict:
    payload.ensure_supported_model()
    if payload.stream:
        return StreamingResponse(
            create_chat_completion_stream(payload),
            media_type="text/event-stream",
        )
    return await create_chat_completion(payload)
