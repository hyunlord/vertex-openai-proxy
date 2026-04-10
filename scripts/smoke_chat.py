from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.config import settings


def _select_chat_model(payload: dict, explicit_model: str | None = None) -> str | None:
    if explicit_model:
        return explicit_model
    for model in payload.get("data", []):
        capabilities = model.get("capabilities", [])
        if any(capability.get("kind") == "chat" for capability in capabilities):
            return model.get("id")
    return None


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    models = client.get("/v1/models")
    authorization = f"Bearer {settings.internal_bearer_token}"

    payload = models.json()
    chat_model = _select_chat_model(payload)
    with patch("app.routes.chat.create_chat_completion", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = {
            "id": "chatcmpl-smoke",
            "object": "chat.completion",
            "created": 1710000000,
            "model": chat_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "READY"},
                    "finish_reason": "stop",
                }
            ],
        }
        chat = client.post(
            "/v1/chat/completions",
            headers={"Authorization": authorization},
            json={
                "model": chat_model,
                "messages": [{"role": "user", "content": "reply with READY only"}],
            },
        )
    chat_payload = chat.json() if chat.status_code == 200 else {}

    result = {
        "ok": (
            health.status_code == 200
            and models.status_code == 200
            and isinstance(chat_model, str)
            and chat.status_code == 200
            and chat_payload.get("choices", [{}])[0].get("message", {}).get("content")
            == "READY"
        ),
        "health_status": health.status_code,
        "models_status": models.status_code,
        "chat_status": chat.status_code,
        "chat_model": chat_model,
    }
    print(json.dumps(result))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
