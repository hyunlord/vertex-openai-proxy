from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer change-me"}


@patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock)
def test_embeddings_batch(mock_embed: AsyncMock) -> None:
    mock_embed.side_effect = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    response = client.post(
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": ["a", "b", "c"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 3
    assert payload["data"][1]["index"] == 1


@patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock)
def test_embeddings_single_string(mock_embed: AsyncMock) -> None:
    mock_embed.return_value = [0.1, 0.2]
    response = client.post(
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": "a"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["data"]) == 1
    assert payload["data"][0]["index"] == 0
    assert payload["usage"] == {"prompt_tokens": 1, "total_tokens": 1}


def test_embeddings_reject_non_string_inputs() -> None:
    response = client.post(
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": ["ok", 123]},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
