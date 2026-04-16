from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import settings
from app.vertex_auth import get_vertex_access_token


class VertexUpstreamError(Exception):
    def __init__(self, *, status_code: int, message: str, response_text: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.response_text = response_text


RETRYABLE_UPSTREAM_STATUSES = frozenset({429, 500, 502, 503, 504})
_shared_client: httpx.AsyncClient | None = None
_shared_client_lock = asyncio.Lock()


def is_retryable_upstream_error(exc: VertexUpstreamError) -> bool:
    return exc.status_code in RETRYABLE_UPSTREAM_STATUSES


def _build_async_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.request_timeout_seconds)


async def get_shared_http_client() -> httpx.AsyncClient:
    global _shared_client

    if _shared_client is not None:
        return _shared_client

    async with _shared_client_lock:
        if _shared_client is None:
            _shared_client = _build_async_client()
        return _shared_client


async def close_shared_http_client() -> None:
    global _shared_client

    async with _shared_client_lock:
        if _shared_client is not None:
            await _shared_client.aclose()
            _shared_client = None


def _extract_upstream_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message
    return response.text


async def vertex_json_request(
    method: str,
    url: str,
    json_body: dict[str, Any],
) -> dict[str, Any]:
    token = await get_vertex_access_token()
    client = await get_shared_http_client()
    response = await client.request(
        method=method,
        url=url,
        json=json_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    if response.status_code >= 400:
        raise VertexUpstreamError(
            status_code=response.status_code,
            message=_extract_upstream_message(response),
            response_text=response.text,
        )

    return response.json()


async def vertex_stream_request(
    method: str,
    url: str,
    json_body: dict[str, Any],
) -> AsyncIterator[str]:
    token = await get_vertex_access_token()
    client = await get_shared_http_client()
    async with client.stream(
        method=method,
        url=url,
        json=json_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    ) as response:
        if response.status_code >= 400:
            await response.aread()
            raise VertexUpstreamError(
                status_code=response.status_code,
                message=_extract_upstream_message(response),
                response_text=response.text,
            )

        async for line in response.aiter_lines():
            if line:
                yield line
