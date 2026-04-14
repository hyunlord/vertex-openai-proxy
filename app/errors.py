from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class OpenAIError(BaseModel):
    message: str
    type: str
    param: str | None = None
    code: int | str | None = None


class OpenAIErrorResponse(BaseModel):
    error: OpenAIError


def _error_type_for_status(status_code: int) -> str:
    if status_code == 401:
        return "authentication_error"
    if status_code == 403:
        return "permission_error"
    if status_code == 404:
        return "not_found_error"
    if status_code == 429:
        return "rate_limit_error"
    if status_code >= 500:
        return "server_error"
    return "invalid_request_error"


def build_openai_error(
    *,
    message: str,
    status_code: int,
    error_type: str | None = None,
    param: str | None = None,
    code: int | str | None = None,
) -> OpenAIErrorResponse:
    return OpenAIErrorResponse(
        error=OpenAIError(
            message=message,
            type=error_type or _error_type_for_status(status_code),
            param=param,
            code=code if code is not None else status_code,
        )
    )


def openai_error_response(
    *,
    status_code: int,
    message: str,
    request_id: str | None = None,
    headers: dict[str, str] | None = None,
    error_type: str | None = None,
    param: str | None = None,
    code: int | str | None = None,
) -> JSONResponse:
    response_headers = dict(headers or {})
    if request_id:
        response_headers["x-request-id"] = request_id
    payload = build_openai_error(
        message=message,
        status_code=status_code,
        error_type=error_type,
        param=param,
        code=code,
    ).model_dump()
    return JSONResponse(status_code=status_code, content=payload, headers=response_headers)


def extract_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def extract_detail_message(detail: Any) -> str:
    if isinstance(detail, str):
        return detail
    return str(detail)
