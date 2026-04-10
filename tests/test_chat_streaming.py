from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.vertex_chat import create_chat_completion_stream


client = TestClient(app)
AUTH = {"Authorization": "Bearer change-me"}


async def _fake_vertex_stream():
    yield 'data: {"id":"chunk-1","created":1710000000,"choices":[{"index":0,"delta":{"role":"assistant","content":"Hel"}}]}'
    yield 'data: {"choices":[{"index":0,"delta":{"content":"lo"},"finish_reason":"stop"}]}'
    yield "data: [DONE]"


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


async def _fake_route_stream(_payload: ChatCompletionRequest):
    yield 'data: {"id":"chunk-1","object":"chat.completion.chunk","created":1710000000,"model":"google/gemini-2.5-flash","choices":[{"index":0,"delta":{"role":"assistant","content":"ok"}}]}\n\n'
    yield "data: [DONE]\n\n"


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
