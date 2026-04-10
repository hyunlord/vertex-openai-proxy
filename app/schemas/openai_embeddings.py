from __future__ import annotations

from pydantic import BaseModel, Field, computed_field, field_validator

from app.model_registry import ensure_supported_model, get_default_embedding_model


class EmbeddingRequest(BaseModel):
    model: str | None = None
    input: str | list[str] = Field(min_length=1)
    user: str | None = None
    dimensions: int | None = None

    @field_validator("input", mode="before")
    @classmethod
    def validate_input_type(cls, value: object) -> object:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            if not value:
                raise ValueError("Embedding input list must not be empty")
            if any(not isinstance(item, str) for item in value):
                raise ValueError("Embedding input items must all be strings")
            return value
        raise ValueError("Embedding input must be a string or list of strings")

    @computed_field
    @property
    def normalized_input(self) -> list[str]:
        if isinstance(self.input, str):
            return [self.input]
        return self.input

    def resolved_model(self) -> str:
        return self.model or get_default_embedding_model()

    def ensure_supported_model(self) -> None:
        ensure_supported_model(self.resolved_model(), feature="embedding")
