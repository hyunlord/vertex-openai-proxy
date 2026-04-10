from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import Any


request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("vertex_openai_proxy")


def set_request_id(request_id: str) -> Token[str | None]:
    return request_id_context.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    request_id_context.reset(token)


def get_request_id() -> str | None:
    return request_id_context.get()


def log_event(event: str, **fields: Any) -> None:
    logger.info(
        event,
        extra={
            "event": event,
            "request_id": get_request_id(),
            **fields,
        },
    )


def log_exception(event: str, *, exc: Exception, **fields: Any) -> None:
    logger.exception(
        event,
        extra={
            "event": event,
            "request_id": get_request_id(),
            **fields,
        },
        exc_info=exc,
    )
