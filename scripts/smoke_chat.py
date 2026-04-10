from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    models = client.get("/v1/models")

    payload = models.json()
    has_chat_model = any(
        any(capability.get("kind") == "chat" for capability in model.get("capabilities", []))
        for model in payload.get("data", [])
    )

    print(
        json.dumps(
            {
                "ok": health.status_code == 200 and models.status_code == 200 and has_chat_model,
                "health_status": health.status_code,
                "models_status": models.status_code,
                "has_chat_model": has_chat_model,
            }
        )
    )


if __name__ == "__main__":
    main()
