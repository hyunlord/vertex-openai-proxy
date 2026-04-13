from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.model_registry import ensure_supported_chat_model, get_default_chat_model, resolve_chat_model


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = Field(default=None, min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False

    def ensure_supported_model(self) -> None:
        ensure_supported_chat_model(self.model)

    def resolved_model(self) -> str:
        return resolve_chat_model(self.model)

    def requested_model(self) -> str:
        return self.model or get_default_chat_model()


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: dict[str, Any] | None = None
    completion_tokens_details: dict[str, Any] | None = None


class ChatCompletionResponseMessage(BaseModel):
    role: Literal["assistant"]
    content: str | None = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatCompletionResponseMessage
    finish_reason: str | None = None
    logprobs: dict[str, Any] | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: Literal["chat.completion"]
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage | None = None
