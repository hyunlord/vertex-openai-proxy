from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.config import settings


@dataclass(frozen=True, slots=True)
class ModelCapability:
    kind: str
    supports_streaming: bool = False


@dataclass(frozen=True, slots=True)
class ModelEntry:
    id: str
    object: str
    owned_by: str
    capabilities: tuple[ModelCapability, ...]


_MODELS: dict[str, ModelEntry] = {
    settings.vertex_chat_model: ModelEntry(
        id=settings.vertex_chat_model,
        object="model",
        owned_by="vertex-ai",
        capabilities=(ModelCapability(kind="chat", supports_streaming=True),),
    ),
    settings.vertex_embedding_model: ModelEntry(
        id=settings.vertex_embedding_model,
        object="model",
        owned_by="vertex-ai",
        capabilities=(ModelCapability(kind="embedding"),),
    ),
}


def list_models() -> list[dict[str, object]]:
    return [
        {
            "id": model.id,
            "object": model.object,
            "owned_by": model.owned_by,
            "capabilities": [
                {
                    "kind": capability.kind,
                    "supports_streaming": capability.supports_streaming,
                }
                for capability in model.capabilities
            ],
        }
        for model in _MODELS.values()
    ]


def is_supported_model(model_id: str) -> bool:
    return model_id in _MODELS


def ensure_supported_model(model_id: str, *, feature: str) -> None:
    if not is_supported_model(model_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported {feature} model: {model_id}",
        )


def get_default_chat_model() -> str:
    return settings.vertex_chat_model


def get_default_embedding_model() -> str:
    return settings.vertex_embedding_model
