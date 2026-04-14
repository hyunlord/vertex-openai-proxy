from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_internal_bearer_token
from app.config import settings
from app.runtime.controller import runtime_controller
from app.schemas.openai_embeddings import EmbeddingRequest
from app.services.vertex_embeddings import create_embedding_response
from app.utils.logging import log_event

router = APIRouter()


def _shed_headers(status_code: int) -> dict[str, str] | None:
    if status_code != 429:
        return None
    return {"Retry-After": str(settings.queue_retry_after_seconds)}


@router.post("/v1/embeddings")
async def embeddings(
    payload: EmbeddingRequest,
    _: None = Depends(require_internal_bearer_token),
) -> dict:
    payload.ensure_supported_model()
    rejection = await runtime_controller.acquire_request_slot(
        endpoint="embeddings",
        input_count=len(payload.normalized_input),
    )
    if rejection is not None:
        log_event(
            "request_shed",
            operation="embeddings",
            endpoint="/v1/embeddings",
            model=payload.resolved_model(),
            input_count=len(payload.normalized_input),
            reason=rejection.reason,
            runtime_mode=runtime_controller.current_mode(),
        )
        raise HTTPException(
            status_code=rejection.status_code,
            detail=rejection.message,
            headers=_shed_headers(rejection.status_code),
        )
    return await create_embedding_response(payload)
