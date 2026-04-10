from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas.openai_embeddings import EmbeddingRequest
from app.services.http_client import VertexUpstreamError
from app.services.vertex_embeddings import _embed_one, create_embedding_response


@pytest.mark.asyncio
@patch("app.services.vertex_embeddings._embed_one")
async def test_embedding_response_preserves_input_order(mock_embed_one) -> None:
    async def fake_embed(text: str, model: str) -> tuple[list[float], int]:
        if text == "first":
            await asyncio.sleep(0.02)
            return [1.0], 0
        if text == "second":
            await asyncio.sleep(0.0)
            return [2.0], 0
        return [3.0], 0

    mock_embed_one.side_effect = fake_embed

    response = await create_embedding_response(
        EmbeddingRequest(
            model="gemini-embedding-2-preview",
            input=["first", "second", "third"],
        )
    )

    assert [item["index"] for item in response["data"]] == [0, 1, 2]
    assert [item["embedding"] for item in response["data"]] == [[1.0], [2.0], [3.0]]
    assert response["usage"] == {"prompt_tokens": 3, "total_tokens": 3}


@pytest.mark.asyncio
@patch("app.services.vertex_embeddings._embed_one")
async def test_embedding_batch_failure_aborts_entire_response(mock_embed_one) -> None:
    async def fake_embed(text: str, model: str) -> tuple[list[float], int]:
        if text == "broken":
            raise VertexUpstreamError(status_code=502, message="upstream failed")
        return [1.0], 0

    mock_embed_one.side_effect = fake_embed

    with pytest.raises(VertexUpstreamError):
        await create_embedding_response(
            EmbeddingRequest(
                model="gemini-embedding-2-preview",
                input=["ok", "broken", "later"],
            )
        )


@pytest.mark.asyncio
@patch("app.services.vertex_embeddings.vertex_json_request")
async def test_embedding_malformed_upstream_payload_becomes_502(
    mock_vertex_json_request,
) -> None:
    mock_vertex_json_request.return_value = {"unexpected": "payload"}

    with pytest.raises(HTTPException) as exc_info:
        await _embed_one("hello", "gemini-embedding-2-preview")

    assert exc_info.value.status_code == 502
