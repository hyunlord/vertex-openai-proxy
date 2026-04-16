from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.openai_chat import ChatCompletionUsage


class ChatCompletionChunkToolCallFunction(BaseModel):
    name: str | None = None
    arguments: str | None = None


class ChatCompletionChunkToolCall(BaseModel):
    index: int
    id: str | None = None
    type: Literal["function"] | None = None
    function: ChatCompletionChunkToolCallFunction | None = None


class ChatCompletionChunkDelta(BaseModel):
    role: Literal["assistant"] | None = None
    content: str | None = None
    tool_calls: list[ChatCompletionChunkToolCall] | None = None


class ChatCompletionChunkChoice(BaseModel):
    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: str | None = None
    logprobs: dict[str, Any] | None = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: Literal["chat.completion.chunk"]
    created: int
    model: str
    choices: list[ChatCompletionChunkChoice]
    usage: ChatCompletionUsage | None = None
