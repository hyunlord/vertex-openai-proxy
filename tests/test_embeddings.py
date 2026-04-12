import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.runtime.controller import runtime_controller
from app.schemas.openai_embeddings import EmbeddingRequest
from app.services.http_client import VertexUpstreamError
from app.services.vertex_embeddings import create_embedding_response


client = TestClient(app)
AUTH = {"Authorization": "Bearer change-me"}


@patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock)
def test_embeddings_batch(mock_embed: AsyncMock) -> None:
    mock_embed.side_effect = [([0.1, 0.2], 0), ([0.3, 0.4], 0), ([0.5, 0.6], 0)]
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
    mock_embed.return_value = ([0.1, 0.2], 0)
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


def test_embeddings_reject_too_many_inputs(monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_max_inputs_per_request", 2)

    response = client.post(
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": ["a", "b", "c"]},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["type"] == "invalid_request_error"
    assert "maximum" in payload["error"]["message"].lower()


def test_embeddings_shed_oversized_requests_in_degraded_mode(monkeypatch) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "runtime_adaptive_mode", True)
    monkeypatch.setattr(settings, "runtime_soft_retryable_error_rate", 0.5)
    monkeypatch.setattr(settings, "runtime_hard_retryable_error_rate", 0.1)
    monkeypatch.setattr(settings, "runtime_degraded_max_embedding_inputs", 2)

    for _ in range(2):
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
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": ["a", "b", "c"]},
    )

    assert response.status_code == 429
    payload = response.json()
    assert payload["error"]["type"] == "rate_limit_error"
    assert "degraded-mode embeddings input count exceeded" in payload["error"]["message"]


@patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock)
def test_embeddings_bound_fanout_concurrency(mock_embed: AsyncMock, monkeypatch) -> None:
    monkeypatch.setattr(settings, "embedding_max_concurrency", 2)

    state = {"in_flight": 0, "max_seen": 0}

    async def fake_embed(text: str, model: str) -> tuple[list[float], int]:
        state["in_flight"] += 1
        state["max_seen"] = max(state["max_seen"], state["in_flight"])
        await asyncio.sleep(0.01)
        state["in_flight"] -= 1
        return [float(ord(text))], 0

    mock_embed.side_effect = fake_embed

    response = client.post(
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": ["a", "b", "c", "d"]},
    )

    assert response.status_code == 200
    assert state["max_seen"] <= 2


@pytest.mark.asyncio
@patch("app.services.vertex_embeddings.vertex_json_request", new_callable=AsyncMock)
async def test_embeddings_retry_transient_429_once(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "embedding_retry_attempts", 1)
    monkeypatch.setattr(settings, "embedding_retry_backoff_ms", 0)

    mock_vertex_json_request.side_effect = [
        VertexUpstreamError(status_code=429, message="rate limited"),
        {"embedding": {"values": [0.1, 0.2]}},
    ]

    response = await create_embedding_response(
        EmbeddingRequest(model="gemini-embedding-2-preview", input="alpha")
    )

    assert len(response["data"]) == 1
    assert mock_vertex_json_request.await_count == 2


@pytest.mark.asyncio
@patch("app.services.vertex_embeddings.vertex_json_request", new_callable=AsyncMock)
async def test_embeddings_fail_after_retry_budget_exhausted(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "embedding_retry_attempts", 1)
    monkeypatch.setattr(settings, "embedding_retry_backoff_ms", 0)

    mock_vertex_json_request.side_effect = [
        VertexUpstreamError(status_code=503, message="temporary unavailable"),
        VertexUpstreamError(status_code=503, message="temporary unavailable"),
    ]

    with pytest.raises(VertexUpstreamError) as exc_info:
        await create_embedding_response(
            EmbeddingRequest(model="gemini-embedding-2-preview", input="alpha")
        )

    assert exc_info.value.status_code == 503
    assert mock_vertex_json_request.await_count == 2
