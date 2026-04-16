from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.http_client import VertexUpstreamError
from app.services.vertex_chat import create_chat_completion_stream


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-proxy-token"}


async def _fake_vertex_stream():
    yield 'data: {"id":"chunk-1","created":1710000000,"choices":[{"index":0,"delta":{"role":"assistant","content":"Hel"}}]}'
    yield 'data: {"choices":[{"index":0,"delta":{"content":"lo"},"finish_reason":"stop"}]}'
    yield "data: [DONE]"


async def _fake_vertex_tool_stream():
    yield (
        'data: {"id":"chunk-tool-1","created":1710000001,"choices":[{"index":0,"delta":'
        '{"role":"assistant","tool_calls":[{"index":0,"id":"call_weather","type":"function",'
        '"function":{"name":"get_weather","arguments":"{\\"city\\":\\""}}]}}]}'
    )
    yield (
        'data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":'
        '{"arguments":"Seoul\\"}"}}]},"finish_reason":"tool_calls"}]}'
    )
    yield "data: [DONE]"


async def _fake_vertex_stream_then_error():
    yield 'data: {"id":"chunk-err-1","created":1710000002,"choices":[{"index":0,"delta":{"role":"assistant","content":"Hel"}}]}'
    raise VertexUpstreamError(status_code=503, message="temporary unavailable")


@pytest.mark.asyncio
async def test_chat_streaming_translates_openai_chunks() -> None:
    with patch("app.services.vertex_chat.vertex_stream_request", return_value=_fake_vertex_stream()):
        payload = ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hello"}],
            stream=True,
        )

        events = [event async for event in create_chat_completion_stream(payload)]

    assert events[-1] == "data: [DONE]\n\n"

    first_chunk = json.loads(events[0].removeprefix("data: ").strip())
    assert first_chunk["id"] == "chunk-1"
    assert first_chunk["object"] == "chat.completion.chunk"
    assert first_chunk["created"] == 1710000000
    assert first_chunk["model"] == "google/gemini-2.5-flash"
    assert first_chunk["choices"] == [
        {
            "index": 0,
            "delta": {"role": "assistant", "content": "Hel"},
        }
    ]

    second_chunk = json.loads(events[1].removeprefix("data: ").strip())
    assert second_chunk["object"] == "chat.completion.chunk"
    assert second_chunk["choices"] == [
        {
            "index": 0,
            "delta": {"content": "lo"},
            "finish_reason": "stop",
        }
    ]


@pytest.mark.asyncio
async def test_chat_streaming_translates_tool_call_chunks() -> None:
    with patch("app.services.vertex_chat.vertex_stream_request", return_value=_fake_vertex_tool_stream()):
        payload = ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hello"}],
            stream=True,
            tools=[
                {
                    "type": "function",
                    "function": {"name": "get_weather"},
                }
            ],
            tool_choice="auto",
        )

        events = [event async for event in create_chat_completion_stream(payload)]

    first_chunk = json.loads(events[0].removeprefix("data: ").strip())
    assert first_chunk["choices"] == [
        {
            "index": 0,
            "delta": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_weather",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": "{\"city\":\"",
                        },
                    }
                ],
            },
        }
    ]

    second_chunk = json.loads(events[1].removeprefix("data: ").strip())
    assert second_chunk["choices"] == [
        {
            "index": 0,
            "delta": {
                "tool_calls": [
                    {
                        "index": 0,
                        "function": {
                            "arguments": "Seoul\"}",
                        },
                    }
                ],
            },
            "finish_reason": "tool_calls",
        }
    ]


@pytest.mark.asyncio
async def test_chat_streaming_emits_error_event_when_upstream_fails_mid_stream() -> None:
    with patch(
        "app.services.vertex_chat.vertex_stream_request",
        return_value=_fake_vertex_stream_then_error(),
    ):
        payload = ChatCompletionRequest(
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "hello"}],
            stream=True,
        )

        events = [event async for event in create_chat_completion_stream(payload)]

    assert events[-1] == "data: [DONE]\n\n"
    assert events[1].startswith("event: error\n")

    error_payload = json.loads(events[1].split("data: ", 1)[1].strip())
    assert error_payload["error"]["message"] == "temporary unavailable"
    assert error_payload["error"]["type"] == "server_error"


async def _fake_route_stream(_payload: ChatCompletionRequest):
    yield 'data: {"id":"chunk-1","object":"chat.completion.chunk","created":1710000000,"model":"google/gemini-2.5-flash","choices":[{"index":0,"delta":{"role":"assistant","content":"ok"}}]}\n\n'
    yield "data: [DONE]\n\n"


async def _fake_route_stream_error_before_first_chunk(_payload: ChatCompletionRequest):
    if False:  # pragma: no cover
        yield ""
    raise VertexUpstreamError(status_code=503, message="temporary unavailable")


def test_chat_streaming_response_uses_sse_media_type() -> None:
    with patch("app.routes.chat.create_chat_completion_stream", side_effect=_fake_route_stream):
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=AUTH,
            json={
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        ) as response:
            body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"id":"chunk-1"' in body
    assert "data: [DONE]" in body


def test_chat_streaming_route_emits_error_event_when_stream_fails_before_first_chunk() -> None:
    with patch(
        "app.routes.chat.create_chat_completion_stream",
        side_effect=_fake_route_stream_error_before_first_chunk,
    ):
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=AUTH,
            json={
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        ) as response:
            body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: error" in body
    assert '"temporary unavailable"' in body
    assert "data: [DONE]" in body


def test_chat_streaming_route_accepts_tool_calling() -> None:
    async def fake_tool_route_stream(_payload: ChatCompletionRequest):
        yield (
            'data: {"id":"chunk-tool-1","object":"chat.completion.chunk","created":1710000001,'
            '"model":"google/gemini-2.5-flash","choices":[{"index":0,"delta":{"role":"assistant",'
            '"tool_calls":[{"index":0,"id":"call_weather","type":"function","function":{"name":"get_weather"}}]}}]}\n\n'
        )
        yield "data: [DONE]\n\n"

    with patch("app.routes.chat.create_chat_completion_stream", side_effect=fake_tool_route_stream):
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers=AUTH,
            json={
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
                "tools": [
                    {
                        "type": "function",
                        "function": {"name": "get_weather"},
                    }
                ],
            },
        ) as response:
            body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"tool_calls"' in body
    assert "data: [DONE]" in body


@pytest.mark.asyncio
async def test_chat_streaming_alias_resolves_model_name() -> None:
    with patch("app.services.vertex_chat.vertex_stream_request", return_value=_fake_vertex_stream()):
        original_default = settings.vertex_chat_model
        original_models = settings.vertex_chat_models
        original_aliases = settings.vertex_chat_model_aliases
        settings.vertex_chat_model = "google/gemini-3.1-flash-lite-preview"
        settings.vertex_chat_models = "google/gemini-3.1-pro-preview"
        settings.vertex_chat_model_aliases = "genos-pro=google/gemini-3.1-pro-preview"
        try:
            payload = ChatCompletionRequest(
                model="genos-pro",
                messages=[{"role": "user", "content": "hello"}],
                stream=True,
            )

            events = [event async for event in create_chat_completion_stream(payload)]
        finally:
            settings.vertex_chat_model = original_default
            settings.vertex_chat_models = original_models
            settings.vertex_chat_model_aliases = original_aliases

    first_chunk = json.loads(events[0].removeprefix("data: ").strip())
    assert first_chunk["model"] == "google/gemini-3.1-pro-preview"
