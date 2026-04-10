from fastapi.testclient import TestClient

from app.main import app


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
        headers={"Authorization": "Bearer change-me"},
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
        headers={"Authorization": "Bearer change-me"},
        json={
            "model": "unsupported-embedding-model",
            "input": "hello",
        },
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
    assert "Unsupported embedding model" in payload["error"]["message"]
