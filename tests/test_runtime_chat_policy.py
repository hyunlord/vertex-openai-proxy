from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.runtime.controller import runtime_controller
from app.schemas.openai_chat import ChatCompletionRequest
from app.services.http_client import VertexUpstreamError
from app.services.vertex_chat import _chat_request_with_retry


@pytest.mark.asyncio
@patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock)
async def test_chat_retry_budget_is_disabled_in_degraded_mode(
    mock_vertex_json_request: AsyncMock,
    monkeypatch,
) -> None:
    runtime_controller.reset()
    monkeypatch.setattr(settings, "runtime_adaptive_mode", True)
    monkeypatch.setattr(settings, "chat_retry_attempts", 2)

    runtime_controller.request_started("chat")
    runtime_controller.request_finished(
        endpoint="chat",
        latency_ms=100.0,
        retryable_failure=True,
        timed_out=False,
        auth_failure=False,
        now=1000.0,
    )

    mock_vertex_json_request.side_effect = VertexUpstreamError(
        status_code=503,
        message="temporary unavailable",
    )

    with pytest.raises(VertexUpstreamError):
        await _chat_request_with_retry(
            ChatCompletionRequest(
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": "hello"}],
            ).model_dump(exclude_none=True)
        )

    assert mock_vertex_json_request.await_count == 1
