from __future__ import annotations


def validate_chat_completion(payload: dict) -> bool:
    return (
        payload.get("object") == "chat.completion"
        and isinstance(payload.get("id"), str)
        and isinstance(payload.get("created"), int)
        and isinstance(payload.get("model"), str)
        and isinstance(payload.get("choices"), list)
    )


def validate_chat_chunk(payload: dict) -> bool:
    return (
        payload.get("object") == "chat.completion.chunk"
        and isinstance(payload.get("id"), str)
        and isinstance(payload.get("created"), int)
        and isinstance(payload.get("model"), str)
        and isinstance(payload.get("choices"), list)
    )


def validate_embeddings_response(payload: dict, *, expected_count: int | None = None) -> bool:
    data = payload.get("data")
    if payload.get("object") != "list" or not isinstance(data, list):
        return False
    if expected_count is not None and len(data) != expected_count:
        return False
    return all(
        item.get("object") == "embedding"
        and item.get("index") == index
        and isinstance(item.get("embedding"), list)
        for index, item in enumerate(data)
    )


def validate_openai_error(payload: dict) -> bool:
    error = payload.get("error")
    return (
        isinstance(error, dict)
        and isinstance(error.get("message"), str)
        and isinstance(error.get("type"), str)
        and "code" in error
    )
