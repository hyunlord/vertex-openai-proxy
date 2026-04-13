from fastapi.testclient import TestClient

from app.main import app
from app import model_registry
from app.config import settings


client = TestClient(app)


def test_models() -> None:
    response = client.get("/v1/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert len(payload["data"]) == 2
    assert payload["data"][0]["owned_by"] == "vertex-ai"
    assert payload["data"][1]["capabilities"][0]["kind"] == "embedding"


def test_invalid_chat_model_is_rejected() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer test-proxy-token"},
        json={
            "model": "unsupported-chat-model",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
    assert "Unsupported chat model" in payload["error"]["message"]


def test_invalid_embedding_model_is_rejected() -> None:
    response = client.post(
        "/v1/embeddings",
        headers={"Authorization": "Bearer test-proxy-token"},
        json={
            "model": "unsupported-embedding-model",
            "input": "hello",
        },
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
    assert "Unsupported embedding model" in payload["error"]["message"]


def test_resolve_chat_model_uses_default_when_model_is_omitted(monkeypatch) -> None:
    monkeypatch.setattr(settings, "vertex_chat_model", "google/gemini-3.1-flash-lite-preview")
    monkeypatch.setattr(settings, "vertex_chat_models", "google/gemini-3.1-pro-preview")
    monkeypatch.setattr(
        settings,
        "vertex_chat_model_aliases",
        "genos-flash=google/gemini-3.1-flash-lite-preview,genos-pro=google/gemini-3.1-pro-preview",
    )

    assert model_registry.resolve_chat_model(None) == "google/gemini-3.1-flash-lite-preview"


def test_resolve_chat_model_accepts_alias_and_raw_model(monkeypatch) -> None:
    monkeypatch.setattr(settings, "vertex_chat_model", "google/gemini-3.1-flash-lite-preview")
    monkeypatch.setattr(settings, "vertex_chat_models", "google/gemini-3.1-pro-preview")
    monkeypatch.setattr(
        settings,
        "vertex_chat_model_aliases",
        "genos-pro=google/gemini-3.1-pro-preview",
    )

    assert model_registry.resolve_chat_model("genos-pro") == "google/gemini-3.1-pro-preview"
    assert (
        model_registry.resolve_chat_model("google/gemini-3.1-pro-preview")
        == "google/gemini-3.1-pro-preview"
    )


def test_models_endpoint_lists_aliases_and_raw_chat_models(monkeypatch) -> None:
    monkeypatch.setattr(settings, "vertex_chat_model", "google/gemini-3.1-flash-lite-preview")
    monkeypatch.setattr(settings, "vertex_chat_models", "google/gemini-3.1-pro-preview")
    monkeypatch.setattr(
        settings,
        "vertex_chat_model_aliases",
        "genos-flash=google/gemini-3.1-flash-lite-preview,genos-pro=google/gemini-3.1-pro-preview",
    )

    payload = client.get("/v1/models").json()
    ids = {entry["id"] for entry in payload["data"]}

    assert "genos-flash" in ids
    assert "genos-pro" in ids
    assert "google/gemini-3.1-flash-lite-preview" in ids
    assert "google/gemini-3.1-pro-preview" in ids
