from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContentBlock(BaseModel):
    type: Literal["text", "image_url", "tool_use", "tool_result"] = "text"
    text: str | None = None
    url: str | None = None
    tool_use_id: str | None = None
    name: str | None = None
    input: dict[str, Any] | None = None
    content: str | None = None


class ChatFolder(BaseModel):
    id: str
    name: str
    sort_order: int = 0
    created_at: str


class ChatSummary(BaseModel):
    id: str
    folder_id: str | None = None
    title: str
    model_id: str
    created_at: str
    updated_at: str


class MessageRecord(BaseModel):
    id: str
    chat_id: str
    role: Literal["user", "assistant", "tool"]
    content: list[ContentBlock]
    tokens_in: int | None = None
    tokens_out: int | None = None
    credits: float | None = None
    created_at: str


class CreateChatRequest(BaseModel):
    model_id: str
    title: str | None = None
    folder_id: str | None = None


class UpdateChatRequest(BaseModel):
    title: str | None = None
    folder_id: str | None = None
    model_id: str | None = None


class CreateFolderRequest(BaseModel):
    name: str


class UpdateFolderRequest(BaseModel):
    name: str


class SendMessageRequest(BaseModel):
    content: list[ContentBlock] = Field(min_length=1)
    tools_enabled: bool = False


class SendMessageResponse(BaseModel):
    message_id: str


class ChatModelInfo(BaseModel):
    id: str
    display_name: str
    price_hint: str
    estimate_credits: float | None = None
    price_updated_at: str | None = None
    supports_vision: bool = False
    supports_tools: bool = False


class UploadResponse(BaseModel):
    file_url: str
