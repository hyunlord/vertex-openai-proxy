from __future__ import annotations

import re
import time
from typing import Any

import httpx

from app.config import settings

METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/"
    "instance/service-accounts/default/token"
)

_cached_token: str | None = None
_cached_token_expiry: float = 0.0


class VertexAuthError(Exception):
    def __init__(
        self,
        *,
        message: str,
        auth_path: str,
        code: str = "vertex_auth_failed",
        vpc_service_controls_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.auth_path = auth_path
        self.code = code
        self.vpc_service_controls_id = vpc_service_controls_id
        self.status_code = 503
        self.error_type = "service_unavailable_error"


def reset_vertex_access_token_cache() -> None:
    global _cached_token, _cached_token_expiry
    _cached_token = None
    _cached_token_expiry = 0.0


def _load_adc_token() -> str | None:
    try:
        import google.auth
        from google.auth.transport import requests as google_auth_requests
    except ImportError:
        return None

    creds, _project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google_auth_requests.Request())
    return getattr(creds, "token", None)


def _extract_vpc_service_controls_id(message: str) -> str | None:
    match = re.search(r"vpcServiceControlsUniqueIdentifier:\s*([A-Za-z0-9._-]+)", message)
    if match:
        return match.group(1)
    return None


def _build_auth_failure_message(*, auth_path: str, details: str) -> str:
    vpc_sc_id = _extract_vpc_service_controls_id(details)
    base = (
        "Vertex authentication failed while minting an access token. "
        f"auth_path={auth_path}. "
    )
    if "organization's policy" in details or "vpcServiceControlsUniqueIdentifier" in details:
        base += (
            "The token exchange was denied by organization's policy, which strongly suggests "
            "VPC Service Controls or a related org policy is blocking STS."
        )
    else:
        base += "The token exchange failed before reaching Vertex."
    if vpc_sc_id:
        base += f" vpcServiceControlsUniqueIdentifier={vpc_sc_id}."
    base += f" details={details}"
    return base


async def get_vertex_access_token() -> str:
    global _cached_token, _cached_token_expiry

    if settings.vertex_access_token:
        return settings.vertex_access_token

    now = time.time()
    if _cached_token and now < (_cached_token_expiry - 60):
        return _cached_token

    adc_error: Exception | None = None
    try:
        adc_token = _load_adc_token()
    except Exception as exc:
        adc_error = exc
        adc_token = None
    if adc_token:
        _cached_token = adc_token
        _cached_token_expiry = now + 300
        return _cached_token

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                METADATA_TOKEN_URL,
                headers={"Metadata-Flavor": "Google"},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
    except httpx.HTTPError as exc:
        details = ""
        if hasattr(exc, "response") and getattr(exc, "response") is not None:
            details = getattr(exc.response, "text", "") or str(exc)
        elif adc_error is not None:
            details = str(adc_error)
        else:
            details = str(exc)
        message = _build_auth_failure_message(
            auth_path="adc->metadata",
            details=details,
        )
        raise VertexAuthError(
            message=message,
            auth_path="adc->metadata",
            vpc_service_controls_id=_extract_vpc_service_controls_id(details),
        ) from exc

    _cached_token = payload["access_token"]
    _cached_token_expiry = now + int(payload.get("expires_in", 300))
    return _cached_token
