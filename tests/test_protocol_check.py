from harness.checks.protocol import (
    validate_chat_chunk,
    validate_chat_completion,
    validate_embeddings_response,
    validate_openai_error,
)


def test_validate_chat_completion_shape() -> None:
    assert validate_chat_completion(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1710000000,
            "model": "google/gemini-2.5-flash",
            "choices": [],
        }
    )


def test_validate_chat_chunk_shape() -> None:
    assert validate_chat_chunk(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion.chunk",
            "created": 1710000000,
            "model": "google/gemini-2.5-flash",
            "choices": [],
        }
    )


def test_validate_embeddings_count_and_order() -> None:
    assert validate_embeddings_response(
        {
            "object": "list",
            "data": [
                {"object": "embedding", "index": 0, "embedding": [0.1]},
                {"object": "embedding", "index": 1, "embedding": [0.2]},
            ],
        },
        expected_count=2,
    )
    assert not validate_embeddings_response(
        {
            "object": "list",
            "data": [
                {"object": "embedding", "index": 1, "embedding": [0.1]},
            ],
        },
        expected_count=1,
    )


def test_validate_openai_error_envelope() -> None:
    assert validate_openai_error(
        {
            "error": {
                "message": "bad request",
                "type": "invalid_request_error",
                "code": 400,
            }
        }
    )
