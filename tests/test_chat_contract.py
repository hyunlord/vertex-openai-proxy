from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.http_client import VertexUpstreamError
from app.services.vertex_chat import create_chat_completion
from app.config import settings


client = TestClient(app)
AUTH = {"Authorization": "Bearer change-me"}


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_completion_normalizes_openai_shape(
    mock_vertex_json_request: AsyncMock,
) -> None:
    mock_vertex_json_request.return_value = {
        "id": "chatcmpl-upstream",
        "object": "chat.completion",
        "created": 1710000000,
        "model": "publisher/model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
    }

    response = await create_chat_completion(
        ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    assert response["id"] == "chatcmpl-upstream"
    assert response["object"] == "chat.completion"
    assert isinstance(response["created"], int)
    assert response["model"] == "publisher/model"
    assert response["choices"][0]["index"] == 0
    assert response["choices"][0]["message"]["role"] == "assistant"
    assert response["choices"][0]["message"]["content"] == "ok"
    assert response["choices"][0]["finish_reason"] == "stop"
    assert "usage" not in response


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_completion_preserves_usage_when_present(
    mock_vertex_json_request: AsyncMock,
) -> None:
    mock_vertex_json_request.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    }

    response = await create_chat_completion(
        ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    assert response["object"] == "chat.completion"
    assert response["model"] == "google/gemini-2.5-flash"
    assert response["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 5,
        "total_tokens": 8,
    }


def test_chat_completion_rejects_malformed_messages() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user"}],
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_completion_retries_non_stream_transient_429(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "chat_retry_attempts", 1)
    monkeypatch.setattr(settings, "chat_retry_backoff_ms", 0)

    mock_vertex_json_request.side_effect = [
        VertexUpstreamError(status_code=429, message="rate limited"),
        {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ]
        },
    ]

    response = await create_chat_completion(
        ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    assert response["choices"][0]["message"]["content"] == "ok"
    assert mock_vertex_json_request.await_count == 2


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_completion_fails_after_retry_budget_exhausted(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "chat_retry_attempts", 1)
    monkeypatch.setattr(settings, "chat_retry_backoff_ms", 0)

    mock_vertex_json_request.side_effect = [
        VertexUpstreamError(status_code=503, message="temporary unavailable"),
        VertexUpstreamError(status_code=503, message="temporary unavailable"),
    ]

    with pytest.raises(VertexUpstreamError) as exc_info:
        await create_chat_completion(
            ChatCompletionRequest(
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": "hello"}],
            )
        )

    assert exc_info.value.status_code == 503
    assert mock_vertex_json_request.await_count == 2
