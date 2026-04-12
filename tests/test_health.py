from fastapi.testclient import TestClient

from app.main import app
from app.runtime.controller import runtime_controller


client = TestClient(app)


def test_health() -> None:
    runtime_controller.reset()
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["runtime_mode"] == "normal"
    assert payload["degraded"] is False
    assert payload["adaptive_mode_enabled"] in {True, False}
    assert payload["in_flight"] == {"chat": 0, "embeddings": 0}
