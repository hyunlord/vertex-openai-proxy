from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)
AUTH = {"Authorization": "Bearer change-me"}


@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
def test_chat_request_logs_request_id_model_and_latency(
    mock_vertex_json_request: AsyncMock,
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="vertex_openai_proxy")
    mock_vertex_json_request.return_value = {
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ]
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
    log_record = next(record for record in caplog.records if getattr(record, "operation", None) == "chat")
    assert log_record.request_id == response.headers["x-request-id"]
    assert log_record.model == "google/gemini-2.5-flash"
    assert log_record.mode == "non_stream"
    assert isinstance(log_record.upstream_latency_ms, float)


@patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock)
def test_embeddings_request_logs_request_id_model_and_latency(
    mock_embed_one: AsyncMock,
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="vertex_openai_proxy")
    mock_embed_one.side_effect = [[0.1, 0.2], [0.3, 0.4]]

    response = client.post(
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": ["a", "b"]},
    )

    assert response.status_code == 200
    log_record = next(
        record for record in caplog.records if getattr(record, "operation", None) == "embeddings"
    )
    assert log_record.request_id == response.headers["x-request-id"]
    assert log_record.model == "gemini-embedding-2-preview"
    assert log_record.mode == "batch"
    assert log_record.input_count == 2
    assert isinstance(log_record.upstream_latency_ms, float)
