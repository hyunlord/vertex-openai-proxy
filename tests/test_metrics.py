from fastapi.testclient import TestClient

from app.main import app
from app.runtime.controller import runtime_controller


client = TestClient(app)


def test_metrics_endpoint_exposes_runtime_mode_and_basic_gauges() -> None:
    runtime_controller.reset()
    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert 'vertex_proxy_runtime_mode{mode="normal"} 1' in body
    assert 'vertex_proxy_in_flight_requests{endpoint="chat"} 0' in body
    assert 'vertex_proxy_in_flight_requests{endpoint="embeddings"} 0' in body
    assert "vertex_proxy_process_max_rss_mb" in body
