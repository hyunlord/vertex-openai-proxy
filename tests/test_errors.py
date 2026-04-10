from fastapi.testclient import TestClient

from app.main import app
from app.routes import chat as chat_route


client = TestClient(app)


def test_unauthorized_chat_returns_openai_error_and_request_id() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 401
    assert "x-request-id" in response.headers

    payload = response.json()
    assert "error" in payload
    assert payload["error"]["message"] == "Unauthorized"
    assert payload["error"]["type"] == "authentication_error"
    assert payload["error"]["code"] == 401


def test_validation_error_returns_openai_error_and_request_id() -> None:
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer change-me"},
        json={"model": "google/gemini-2.5-flash"},
    )

    assert response.status_code == 422
    assert "x-request-id" in response.headers

    payload = response.json()
    assert "error" in payload
    assert payload["error"]["type"] == "invalid_request_error"
    assert payload["error"]["code"] == 422
    assert payload["error"]["message"]


def test_success_response_has_request_id_header() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert "x-request-id" in response.headers


def test_generic_errors_return_safe_message(monkeypatch) -> None:
    error_client = TestClient(app, raise_server_exceptions=False)

    async def raise_runtime_error(*args, **kwargs):
        raise RuntimeError("sensitive internal details")

    monkeypatch.setattr(chat_route, "create_chat_completion", raise_runtime_error)

    response = error_client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer change-me"},
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["message"] == "Internal server error"
    assert payload["error"]["type"] == "server_error"
