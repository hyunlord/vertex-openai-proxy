from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.model_registry import ensure_supported_chat_model, get_default_chat_model, resolve_chat_model


class ChatToolFunction(BaseModel):
    name: str = Field(min_length=1)
    arguments: str


class ChatToolCall(BaseModel):
    id: str = Field(min_length=1)
    type: Literal["function"]
    function: ChatToolFunction


class ChatCompletionToolFunction(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    parameters: dict[str, Any] | None = None


class ChatCompletionTool(BaseModel):
    type: Literal["function"]
    function: ChatCompletionToolFunction


class ChatCompletionNamedToolChoiceFunction(BaseModel):
    name: str = Field(min_length=1)


class ChatCompletionNamedToolChoice(BaseModel):
    type: Literal["function"]
    function: ChatCompletionNamedToolChoiceFunction


class ChatMessageTextContentPart(BaseModel):
    type: Literal["text"]
    text: str


ChatMessageContent = str | list[ChatMessageTextContentPart]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: ChatMessageContent | None = None
    tool_call_id: str | None = None
    tool_calls: list[ChatToolCall] | None = None

    @model_validator(mode="after")
    def validate_message_shape(self) -> "ChatMessage":
        if self.role in {"system", "user", "tool"} and self.content is None:
            raise ValueError(f"{self.role} messages require content")
        if self.role == "assistant" and self.content is None and not self.tool_calls:
            raise ValueError("assistant messages require content or tool_calls")
        if self.role == "tool" and not self.tool_call_id:
            raise ValueError("tool messages require tool_call_id")
        if self.role != "tool" and self.tool_call_id is not None:
            raise ValueError("tool_call_id is only valid on tool messages")
        if self.role != "assistant" and self.tool_calls is not None:
            raise ValueError("tool_calls are only valid on assistant messages")
        return self

    def normalized_content(self) -> str | None:
        if self.content is None:
            return None
        if isinstance(self.content, str):
            return self.content
        return "".join(part.text for part in self.content)

    def to_upstream_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role}
        normalized_content = self.normalized_content()
        if normalized_content is not None:
            payload["content"] = normalized_content
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            payload["tool_calls"] = [tool_call.model_dump(exclude_none=True) for tool_call in self.tool_calls]
        return payload


ChatCompletionToolChoice = Literal["none", "auto", "required"] | ChatCompletionNamedToolChoice


class ChatCompletionRequest(BaseModel):
    model: str | None = Field(default=None, min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    stream: bool = False
    tools: list[ChatCompletionTool] | None = None
    tool_choice: ChatCompletionToolChoice | None = None

    def ensure_supported_model(self) -> None:
        ensure_supported_chat_model(self.model)

    def resolved_model(self) -> str:
        return resolve_chat_model(self.model)

    def requested_model(self) -> str:
        return self.model or get_default_chat_model()

    def uses_tool_calling(self) -> bool:
        return (
            bool(self.tools)
            or self.tool_choice is not None
            or any(message.role == "tool" or bool(message.tool_calls) for message in self.messages)
        )

    def to_upstream_payload(self, *, model: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [message.to_upstream_payload() for message in self.messages],
            "stream": self.stream,
        }
        if self.tools is not None:
            payload["tools"] = [tool.model_dump(exclude_none=True) for tool in self.tools]
        if self.tool_choice is not None:
            if isinstance(self.tool_choice, str):
                payload["tool_choice"] = self.tool_choice
            else:
                payload["tool_choice"] = self.tool_choice.model_dump(exclude_none=True)
        return payload


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: dict[str, Any] | None = None
    completion_tokens_details: dict[str, Any] | None = None


class ChatCompletionResponseMessage(BaseModel):
    role: Literal["assistant"]
    content: str | None = None
    tool_calls: list[ChatToolCall] | None = None


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
