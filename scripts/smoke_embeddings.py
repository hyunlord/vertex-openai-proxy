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


def _select_embedding_model(payload: dict, explicit_model: str | None = None) -> str | None:
    if explicit_model:
        return explicit_model
    for model in payload.get("data", []):
        capabilities = model.get("capabilities", [])
        if any(capability.get("kind") == "embedding" for capability in capabilities):
            return model.get("id")
    return None


def main() -> None:
    client = TestClient(app)
    health = client.get("/health")
    models = client.get("/v1/models")
    authorization = f"Bearer {settings.internal_bearer_token}"

    payload = models.json()
    embedding_model = _select_embedding_model(payload)
    with patch("app.services.vertex_embeddings._embed_one", new_callable=AsyncMock) as mock_embed:
        mock_embed.side_effect = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        embeddings = client.post(
            "/v1/embeddings",
            headers={"Authorization": authorization},
            json={
                "model": embedding_model,
                "input": ["alpha", "beta", "gamma"],
            },
        )
    embeddings_payload = embeddings.json() if embeddings.status_code == 200 else {}

    print(
        json.dumps(
            {
                "ok": (
                    health.status_code == 200
                    and models.status_code == 200
                    and isinstance(embedding_model, str)
                    and embeddings.status_code == 200
                    and len(embeddings_payload.get("data", [])) == 3
                ),
                "health_status": health.status_code,
                "models_status": models.status_code,
                "embeddings_status": embeddings.status_code,
                "embedding_model": embedding_model,
            }
        )
    )


if __name__ == "__main__":
    main()
