from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer test-proxy-token"}


@patch("app.routes.chat.create_chat_completion", new_callable=AsyncMock)
def test_chat_completion(mock_create: AsyncMock) -> None:
    mock_create.return_value = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
    }
    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "ok"


@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
def test_chat_completion_alias_resolves_to_upstream_model(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "vertex_chat_model", "google/gemini-3.1-flash-lite-preview")
    monkeypatch.setattr(settings, "vertex_chat_models", "google/gemini-3.1-pro-preview")
    monkeypatch.setattr(settings, "vertex_chat_model_aliases", "genos-pro=google/gemini-3.1-pro-preview")
    mock_vertex_json_request.return_value = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
    }

    response = client.post(
        "/v1/chat/completions",
        headers=AUTH,
        json={
            "model": "genos-pro",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "google/gemini-3.1-pro-preview"
    upstream_body = mock_vertex_json_request.await_args.args[2]
    assert upstream_body["model"] == "google/gemini-3.1-pro-preview"
