from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from kie_sidecar.models.registry import ModelParameter


class ModelInfo(BaseModel):
    id: str
    display_name: str
    price_hint: str
    category: Literal["image", "video", "chat", "audio"]
    estimate_credits: float | None = None
    price_updated_at: str | None = None


class ModelSchemaResponse(BaseModel):
    id: str
    display_name: str
    price_hint: str
    estimate_credits: float | None = None
    price_updated_at: str | None = None
    parameters: list[ModelParameter]


class GenerationRecord(BaseModel):
    id: str
    type: Literal["image", "video", "audio"]
    model_id: str
    task_id: str | None
    status: Literal["pending", "running", "success", "failed"]
    prompt: str | None
    params: dict[str, Any] | None = None
    credits_used: float | None = None
    remote_url: str | None = None
    local_path: str | None = None
    error_msg: str | None = None
    created_at: str
    completed_at: str | None = None
    has_file: bool = False


class CreateGenerationRequest(BaseModel):
    model_id: str
    input: dict[str, Any] = Field(default_factory=dict)
