from fastapi import APIRouter, Depends

from app.auth import require_internal_bearer_token
from app.schemas.openai_embeddings import EmbeddingRequest
from app.services.vertex_embeddings import create_embedding_response

router = APIRouter()


@router.post("/v1/embeddings")
async def embeddings(
    payload: EmbeddingRequest,
    _: None = Depends(require_internal_bearer_token),
) -> dict:
    payload.ensure_supported_model()
    return await create_embedding_response(payload)
