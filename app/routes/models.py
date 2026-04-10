from fastapi import APIRouter

from app.model_registry import list_models as list_supported_models

router = APIRouter()


@router.get("/v1/models")
async def list_models() -> dict:
    return {
        "object": "list",
        "data": list_supported_models(),
    }
