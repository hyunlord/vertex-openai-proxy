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
    target_model: str | None = None


def _build_chat_entries() -> dict[str, ModelEntry]:
    entries: dict[str, ModelEntry] = {}

    for model_id in settings.allowed_chat_models():
        entries[model_id] = ModelEntry(
            id=model_id,
            object="model",
            owned_by="vertex-ai",
            capabilities=(ModelCapability(kind="chat", supports_streaming=True),),
        )

    for alias, target_model in settings.chat_model_alias_map().items():
        entries[alias] = ModelEntry(
            id=alias,
            object="model",
            owned_by="vertex-ai",
            capabilities=(ModelCapability(kind="chat", supports_streaming=True),),
            target_model=target_model,
        )

    return entries


def _build_embedding_entries() -> dict[str, ModelEntry]:
    model_id = settings.vertex_embedding_model
    return {
        model_id: ModelEntry(
            id=model_id,
            object="model",
            owned_by="vertex-ai",
            capabilities=(ModelCapability(kind="embedding"),),
        )
    }


def list_models() -> list[dict[str, object]]:
    entries = {**_build_chat_entries(), **_build_embedding_entries()}
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
            **({"target_model": model.target_model} if model.target_model else {}),
        }
        for model in entries.values()
    ]


def resolve_chat_model(requested_model: str | None) -> str:
    if requested_model is None:
        return settings.vertex_chat_model

    aliases = settings.chat_model_alias_map()
    if requested_model in aliases:
        return aliases[requested_model]

    if requested_model in settings.allowed_chat_models():
        return requested_model

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported chat model: {requested_model}",
    )


def ensure_supported_chat_model(requested_model: str | None) -> str:
    return resolve_chat_model(requested_model)


def get_default_chat_model() -> str:
    return settings.vertex_chat_model


def resolve_embedding_model(requested_model: str | None) -> str:
    model_id = requested_model or settings.vertex_embedding_model
    if model_id != settings.vertex_embedding_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported embedding model: {requested_model}",
        )
    return model_id


def ensure_supported_embedding_model(requested_model: str | None) -> str:
    return resolve_embedding_model(requested_model)


def get_default_embedding_model() -> str:
    return settings.vertex_embedding_model
