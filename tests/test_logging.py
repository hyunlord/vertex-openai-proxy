from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.services.adaptive_concurrency import adaptive_embedding_concurrency
from app.services.http_client import VertexUpstreamError
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
    assert log_record.retry_attempts == 0
    assert isinstance(log_record.upstream_latency_ms, float)


@patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock)
def test_embeddings_request_logs_request_id_model_and_latency(
    mock_embed_one: AsyncMock,
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="vertex_openai_proxy")
    mock_embed_one.side_effect = [([0.1, 0.2], 0), ([0.3, 0.4], 0)]

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
    assert log_record.fanout_count == 2
    assert log_record.retry_attempts == 0
    assert isinstance(log_record.upstream_latency_ms, float)


@patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock)
def test_embeddings_logs_adaptive_concurrency_fields(
    mock_embed_one: AsyncMock,
    caplog,
    monkeypatch,
) -> None:
    adaptive_embedding_concurrency.reset()
    caplog.set_level(logging.INFO, logger="vertex_openai_proxy")
    monkeypatch.setattr(settings, "embedding_adaptive_concurrency", True)
    monkeypatch.setattr(settings, "embedding_adaptive_window_size", 20)
    monkeypatch.setattr(settings, "embedding_adaptive_window_seconds", 60)
    monkeypatch.setattr(settings, "embedding_adaptive_cooldown_seconds", 0)
    monkeypatch.setattr(settings, "embedding_adaptive_min_samples", 1)
    monkeypatch.setattr(settings, "embedding_adaptive_latency_up_threshold_ms", 4000.0)
    mock_embed_one.return_value = ([0.1, 0.2], 0)

    response = client.post(
        "/v1/embeddings",
        headers=AUTH,
        json={"model": "gemini-embedding-2-preview", "input": ["a"]},
    )

    assert response.status_code == 200
    request_record = next(
        record
        for record in caplog.records
        if getattr(record, "operation", None) == "embeddings"
        and getattr(record, "event", None) == "request_completed"
    )
    assert request_record.adaptive_concurrency_enabled is True
    assert request_record.configured_concurrency == settings.embedding_max_concurrency
    assert request_record.effective_concurrency >= settings.embedding_max_concurrency
    adjustment_record = next(record for record in caplog.records if getattr(record, "event", None) == "adaptive_concurrency_adjusted")
    assert adjustment_record.reason == "healthy_window"
    adaptive_embedding_concurrency.reset()


@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
def test_chat_logs_retry_attempts_when_retry_used(
    mock_vertex_json_request: AsyncMock,
    caplog,
    monkeypatch,
) -> None:
    caplog.set_level(logging.INFO, logger="vertex_openai_proxy")
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
    assert log_record.retry_attempts == 1
