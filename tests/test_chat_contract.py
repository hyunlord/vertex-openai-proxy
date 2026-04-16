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
async def test_chat_completion_accepts_missing_model_and_uses_default(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "vertex_chat_model", "google/gemini-3.1-flash-lite-preview")
    mock_vertex_json_request.return_value = {
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
            messages=[{"role": "user", "content": "hello"}],
        )
    )

    assert response["model"] == "google/gemini-3.1-flash-lite-preview"


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


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_completion_normalizes_tool_call_response(
    mock_vertex_json_request: AsyncMock,
) -> None:
    mock_vertex_json_request.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_weather",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": "{\"city\":\"Seoul\"}",
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }

    response = await create_chat_completion(
        ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "What is the weather in Seoul?"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the current weather",
                    },
                }
            ],
            tool_choice="auto",
        )
    )

    assert response["choices"][0]["finish_reason"] == "tool_calls"
    assert response["choices"][0]["message"]["tool_calls"] == [
        {
            "id": "call_weather",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": "{\"city\":\"Seoul\"}",
            },
        }
    ]
    assert "content" not in response["choices"][0]["message"]


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_completion_forwards_tool_payload_to_vertex(
    mock_vertex_json_request: AsyncMock,
) -> None:
    mock_vertex_json_request.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ]
    }

    await create_chat_completion(
        ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[
                {"role": "user", "content": "What is the weather in Seoul?"},
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_weather",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": "{\"city\":\"Seoul\"}",
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_weather",
                    "content": "{\"temperature_c\":19}",
                },
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get the current weather",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "city": {"type": "string"},
                            },
                            "required": ["city"],
                        },
                    },
                }
            ],
            tool_choice={
                "type": "function",
                "function": {"name": "get_weather"},
            },
        )
    )

    upstream_body = mock_vertex_json_request.await_args.args[2]
    assert upstream_body["tools"][0]["function"]["name"] == "get_weather"
    assert upstream_body["tool_choice"] == {
        "type": "function",
        "function": {"name": "get_weather"},
    }
    assert upstream_body["messages"][1]["tool_calls"][0]["id"] == "call_weather"
    assert upstream_body["messages"][2]["tool_call_id"] == "call_weather"


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_completion_accepts_text_content_parts_and_flattens_for_vertex(
    mock_vertex_json_request: AsyncMock,
) -> None:
    mock_vertex_json_request.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ]
    }

    await create_chat_completion(
        ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello, "},
                        {"type": "text", "text": "world"},
                    ],
                }
            ],
        )
    )

    upstream_body = mock_vertex_json_request.await_args.args[2]
    assert upstream_body["messages"][0]["content"] == "Hello, world"


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


def test_chat_completion_rejects_non_text_content_parts() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": "https://example.com/cat.png"},
                        }
                    ],
                }
            ],
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"


def test_chat_completion_rejects_tool_messages_without_tool_call_id() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "tool", "content": "{\"temperature_c\":19}"}],
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"


def test_chat_completion_shed_response_includes_retry_after_header(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "chat_max_in_flight_requests", 0)
    monkeypatch.setattr(settings, "queue_enabled", False)
    monkeypatch.setattr(settings, "queue_retry_after_seconds", 7)

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "7"
    payload = response.json()
    assert payload["error"]["type"] == "rate_limit_error"


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
