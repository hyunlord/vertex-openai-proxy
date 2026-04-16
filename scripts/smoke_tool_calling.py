from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.main import app


async def _fake_tool_stream():
    yield (
        'data: {"id":"chatcmpl-tool-stream","created":1710000001,"choices":[{"index":0,"delta":'
        '{"role":"assistant","tool_calls":[{"index":0,"id":"call_weather","type":"function",'
        '"function":{"name":"get_weather","arguments":"{\\"city\\":\\"Seoul\\"}"}}]},"finish_reason":"tool_calls"}]}'
    )
    yield "data: [DONE]"


def main() -> None:
    client = TestClient(app)
    authorization = f"Bearer {settings.internal_bearer_token}"
    tool_payload = {
        "model": settings.vertex_chat_model,
        "messages": [{"role": "user", "content": "What is the weather in Seoul?"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather",
                },
            }
        ],
        "tool_choice": "auto",
    }

    with patch("app.services.vertex_chat.vertex_json_request", new_callable=AsyncMock) as mock_vertex:
        mock_vertex.return_value = {
            "id": "chatcmpl-tool-smoke",
            "created": 1710000000,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_weather",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": "{\"city\":\"Seoul\"}",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        }
        tool_response = client.post(
            "/v1/chat/completions",
            headers={"Authorization": authorization},
            json=tool_payload,
        )

    tool_body = tool_response.json() if tool_response.status_code == 200 else {}
    with patch("app.services.vertex_chat.vertex_stream_request", return_value=_fake_tool_stream()):
        with client.stream(
            "POST",
            "/v1/chat/completions",
            headers={"Authorization": authorization},
            json={**tool_payload, "stream": True},
        ) as stream_response:
            stream_body = "".join(stream_response.iter_text())

    result = {
        "ok": (
            tool_response.status_code == 200
            and tool_body.get("choices", [{}])[0].get("message", {}).get("tool_calls", [{}])[0].get("id")
            == "call_weather"
            and stream_response.status_code == 200
            and '"tool_calls"' in stream_body
            and "data: [DONE]" in stream_body
        ),
        "tool_chat_status": tool_response.status_code,
        "tool_stream_status": stream_response.status_code,
    }
    print(json.dumps(result))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
