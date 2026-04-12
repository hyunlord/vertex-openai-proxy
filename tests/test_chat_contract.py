from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.http_client import VertexUpstreamError
from app.services.vertex_chat import create_chat_completion
from app.config import settings
from app.runtime.controller import runtime_controller


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-proxy-token"}


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


@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
def test_chat_completion_sheds_requests_when_degraded_chat_cap_is_hit(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "runtime_adaptive_mode", True)
    monkeypatch.setattr(settings, "runtime_soft_retryable_error_rate", 0.5)
    monkeypatch.setattr(settings, "runtime_hard_retryable_error_rate", 0.1)
    monkeypatch.setattr(settings, "runtime_degraded_chat_max_in_flight", 0)

    runtime_controller.request_started("chat")
    runtime_controller.request_finished(
        endpoint="chat",
        latency_ms=100.0,
        status_code=503,
        retry_attempts=1,
        retryable_failure=True,
        timed_out=False,
        auth_failure=False,
    )

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 429
    payload = response.json()
    assert payload["error"]["type"] == "rate_limit_error"
    assert "degraded-mode chat in-flight requests exceeded" in payload["error"]["message"]
    assert mock_vertex_json_request.await_count == 0


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
