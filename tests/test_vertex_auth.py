from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

import app.vertex_auth as vertex_auth
from app.main import app
from app.routes import chat as chat_route
from app.services import http_client
from app.services.http_client import VertexUpstreamError, close_shared_http_client, vertex_json_request


client = TestClient(app)


class FakeMetadataResponse:
    def __init__(self, payload: dict[str, object], *, status_code: int = 200, text: str | None = None):
        self._payload = payload
        self.status_code = status_code
        self.text = text or httpx.Response(status_code, json=payload).text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", vertex_auth.METADATA_TOKEN_URL)
            response = httpx.Response(self.status_code, request=request, text=self.text)
            raise httpx.HTTPStatusError("metadata failed", request=request, response=response)
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class FakeMetadataClient:
    calls = 0
    response = FakeMetadataResponse({"access_token": "metadata-token", "expires_in": 120})

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, headers=None):
        type(self).calls += 1
        assert headers == {"Metadata-Flavor": "Google"}
        return type(self).response


class FakeGoogleCredentials:
    def __init__(self, token: str = "adc-token"):
        self.token = None
        self._token = token

    def refresh(self, request) -> None:
        self.token = self._token


class FakeUpstreamResponse:
    def __init__(self, status_code: int, payload: dict[str, object]):
        self.status_code = status_code
        self._payload = payload
        self.text = httpx.Response(status_code, json=payload).text

    def json(self) -> dict[str, object]:
        return self._payload


class FakeUpstreamClient:
    init_calls = 0
    close_calls = 0
    last_request = None

    def __init__(self, *args, **kwargs):
        type(self).init_calls += 1
        self.kwargs = kwargs

    async def aclose(self):
        type(self).close_calls += 1

    async def request(self, method=None, url=None, json=None, headers=None):
        type(self).last_request = SimpleNamespace(
            method=method,
            url=url,
            json=json,
            headers=headers,
        )
        return FakeUpstreamResponse(
            404,
            {"error": {"message": "Publisher Model not found", "status": "NOT_FOUND"}},
        )


@pytest_asyncio.fixture(autouse=True)
async def reset_shared_http_client_state() -> None:
    await close_shared_http_client()
    yield
    await close_shared_http_client()


@pytest.mark.asyncio
async def test_metadata_token_fetch_and_cache_reuse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vertex_auth, "_load_adc_token", lambda: None)
    monkeypatch.setattr(vertex_auth, "httpx", SimpleNamespace(AsyncClient=FakeMetadataClient))
    monkeypatch.setattr(vertex_auth.settings, "vertex_access_token", None, raising=False)
    vertex_auth.reset_vertex_access_token_cache()
    FakeMetadataClient.calls = 0
    FakeMetadataClient.response = FakeMetadataResponse(
        {"access_token": "metadata-token", "expires_in": 120}
    )

    first = await vertex_auth.get_vertex_access_token()
    second = await vertex_auth.get_vertex_access_token()

    assert first == "metadata-token"
    assert second == "metadata-token"
    assert FakeMetadataClient.calls == 1


@pytest.mark.asyncio
async def test_metadata_token_fetch_is_shared_across_concurrent_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vertex_auth, "_load_adc_token", lambda: None)
    monkeypatch.setattr(vertex_auth, "httpx", SimpleNamespace(AsyncClient=FakeMetadataClient))
    monkeypatch.setattr(vertex_auth.settings, "vertex_access_token", None, raising=False)
    vertex_auth.reset_vertex_access_token_cache()
    FakeMetadataClient.calls = 0
    FakeMetadataClient.response = FakeMetadataResponse(
        {"access_token": "metadata-token", "expires_in": 120}
    )

    first, second = await asyncio.gather(
        vertex_auth.get_vertex_access_token(),
        vertex_auth.get_vertex_access_token(),
    )

    assert first == "metadata-token"
    assert second == "metadata-token"
    assert FakeMetadataClient.calls == 1


@pytest.mark.asyncio
async def test_static_token_override_skips_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vertex_auth, "_load_adc_token", lambda: None)
    monkeypatch.setattr(vertex_auth, "httpx", SimpleNamespace(AsyncClient=FakeMetadataClient))
    monkeypatch.setattr(vertex_auth.settings, "vertex_access_token", "static-token", raising=False)
    vertex_auth.reset_vertex_access_token_cache()
    FakeMetadataClient.calls = 0
    FakeMetadataClient.response = FakeMetadataResponse(
        {"access_token": "metadata-token", "expires_in": 120}
    )

    token = await vertex_auth.get_vertex_access_token()

    assert token == "static-token"
    assert FakeMetadataClient.calls == 0


@pytest.mark.asyncio
async def test_adc_token_is_preferred_over_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vertex_auth, "_load_adc_token", lambda: "adc-token")
    monkeypatch.setattr(vertex_auth, "httpx", SimpleNamespace(AsyncClient=FakeMetadataClient))
    monkeypatch.setattr(vertex_auth.settings, "vertex_access_token", None, raising=False)
    vertex_auth.reset_vertex_access_token_cache()
    FakeMetadataClient.calls = 0
    FakeMetadataClient.response = FakeMetadataResponse(
        {"access_token": "metadata-token", "expires_in": 120}
    )

    token = await vertex_auth.get_vertex_access_token()

    assert token == "adc-token"
    assert FakeMetadataClient.calls == 0


@pytest.mark.asyncio
async def test_policy_blocked_metadata_becomes_vertex_auth_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vertex_auth, "_load_adc_token", lambda: None)
    monkeypatch.setattr(vertex_auth.httpx, "AsyncClient", FakeMetadataClient)
    monkeypatch.setattr(vertex_auth.settings, "vertex_access_token", None, raising=False)
    vertex_auth.reset_vertex_access_token_cache()
    FakeMetadataClient.calls = 0
    FakeMetadataClient.response = FakeMetadataResponse(
        {},
        status_code=403,
        text=(
            "Unable to fetch federated token; The Global STS returned 403 Forbidden: "
            "{\"error\":\"access_denied\",\"error_description\":\"Request is prohibited by "
            "organization's policy. "
            "vpcServiceControlsUniqueIdentifier: abc123xyz\"}"
        ),
    )

    with pytest.raises(vertex_auth.VertexAuthError) as exc_info:
        await vertex_auth.get_vertex_access_token()

    assert exc_info.value.status_code == 503
    assert exc_info.value.error_type == "service_unavailable_error"
    assert exc_info.value.auth_path == "adc->metadata"
    assert exc_info.value.vpc_service_controls_id == "abc123xyz"
    assert "organization's policy" in exc_info.value.message
    assert "vpcServiceControlsUniqueIdentifier=abc123xyz" in exc_info.value.message


@pytest.mark.asyncio
async def test_upstream_http_failure_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.http_client.httpx", SimpleNamespace(AsyncClient=FakeUpstreamClient))

    async def fake_token() -> str:
        return "metadata-token"

    monkeypatch.setattr("app.services.http_client.get_vertex_access_token", fake_token)

    with pytest.raises(VertexUpstreamError) as exc_info:
        await vertex_json_request(
            "POST",
            "https://example.com",
            {"model": "google/gemini-2.5-flash", "messages": []},
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.message == "Publisher Model not found"


@pytest.mark.asyncio
async def test_upstream_http_client_is_reused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.http_client.httpx", SimpleNamespace(AsyncClient=FakeUpstreamClient))

    async def fake_token() -> str:
        return "metadata-token"

    FakeUpstreamClient.init_calls = 0
    FakeUpstreamClient.close_calls = 0
    monkeypatch.setattr("app.services.http_client.get_vertex_access_token", fake_token)

    for _ in range(2):
        with pytest.raises(VertexUpstreamError):
            await vertex_json_request(
                "POST",
                "https://example.com",
                {"model": "google/gemini-2.5-flash", "messages": []},
            )

    assert FakeUpstreamClient.init_calls == 1
    await http_client.close_shared_http_client()
    assert FakeUpstreamClient.close_calls == 1


def test_upstream_error_is_normalized_by_app(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_upstream_error(*args, **kwargs):
        raise VertexUpstreamError(status_code=404, message="Publisher Model not found")

    monkeypatch.setattr(chat_route, "create_chat_completion", raise_upstream_error)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer test-proxy-token"},
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["message"] == "Publisher Model not found"
    assert payload["error"]["type"] == "not_found_error"


def test_vertex_auth_error_is_normalized_by_app(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_vertex_auth_error(*args, **kwargs):
        raise vertex_auth.VertexAuthError(
            message=(
                "Vertex authentication failed while minting an access token. "
                "auth_path=adc->metadata. "
                "The token exchange was denied by organization's policy, which strongly "
                "suggests VPC Service Controls or a related org policy is blocking STS. "
                "vpcServiceControlsUniqueIdentifier=abc123xyz."
            ),
            auth_path="adc->metadata",
            vpc_service_controls_id="abc123xyz",
        )

    monkeypatch.setattr(chat_route, "create_chat_completion", raise_vertex_auth_error)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer test-proxy-token"},
        json={
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": "hello"}],
        },
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["type"] == "service_unavailable_error"
    assert payload["error"]["code"] == "vertex_auth_failed"
    assert "organization's policy" in payload["error"]["message"]
