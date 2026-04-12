from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import validate_runtime_settings
from app.errors import (
    extract_detail_message,
    extract_request_id,
    openai_error_response,
)
from app.services.http_client import VertexUpstreamError
from app.vertex_auth import VertexAuthError
from app.routes.chat import router as chat_router
from app.routes.embeddings import router as embeddings_router
from app.routes.health import router as health_router
from app.routes.metrics import router as metrics_router
from app.routes.models import router as models_router
from app.utils.logging import log_exception, reset_request_id, set_request_id
from app.utils.request_id import generate_request_id


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_runtime_settings()
    yield


app = FastAPI(title="vertex-openai-proxy", lifespan=lifespan)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = generate_request_id()
    request.state.request_id = request_id
    context_token = set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
    finally:
        reset_request_id(context_token)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return openai_error_response(
        status_code=exc.status_code,
        message=extract_detail_message(exc.detail),
        request_id=extract_request_id(request),
    )


@app.exception_handler(VertexUpstreamError)
async def vertex_upstream_exception_handler(
    request: Request,
    exc: VertexUpstreamError,
) -> JSONResponse:
    return openai_error_response(
        status_code=exc.status_code,
        message=exc.message,
        request_id=extract_request_id(request),
    )


@app.exception_handler(VertexAuthError)
async def vertex_auth_exception_handler(
    request: Request,
    exc: VertexAuthError,
) -> JSONResponse:
    return openai_error_response(
        status_code=exc.status_code,
        message=exc.message,
        request_id=extract_request_id(request),
        error_type=exc.error_type,
        code=exc.code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return openai_error_response(
        status_code=422,
        message=str(exc),
        request_id=extract_request_id(request),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_exception(
        "unhandled_exception",
        exc=exc,
        endpoint=str(request.url.path),
        method=request.method,
    )
    return openai_error_response(
        status_code=500,
        message="Internal server error",
        request_id=extract_request_id(request),
    )


app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(models_router)
app.include_router(chat_router)
app.include_router(embeddings_router)
