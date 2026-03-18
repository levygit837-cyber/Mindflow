"""Typed request schemas for chat/session endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from mindflow_backend.infra.sanitizer import sanitize_message


class ChatSessionCreateRequest(BaseModel):
    title: str = Field(default="New Chat", min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, value: str) -> str:
        return sanitize_message(value)


class ChatSessionUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)

    @field_validator("title")
    @classmethod
    def sanitize_title(cls, value: str) -> str:
        return sanitize_message(value)


class ChatSessionMessageCreateRequest(BaseModel):
    role: str = Field(default="user", min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=100000)
    model: str | None = Field(default=None, max_length=100)
    provider: str | None = Field(default=None, max_length=100)

    @field_validator("role")
    @classmethod
    def sanitize_role(cls, value: str) -> str:
        return sanitize_message(value)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, value: str) -> str:
        return sanitize_message(value)

    @field_validator("model", "provider")
    @classmethod
    def sanitize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return sanitize_message(value)


class ChatSessionTitleGenerateRequest(BaseModel):
    message: str = Field(default="", max_length=300)

    @field_validator("message")
    @classmethod
    def sanitize_message_text(cls, value: str) -> str:
        return sanitize_message(value)
