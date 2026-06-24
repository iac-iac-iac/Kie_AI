from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from kie_sidecar.models.param_conditions import is_param_required, is_param_visible

CHAT_REGISTRY_DIR = Path(__file__).resolve().parent / "registry" / "chat"
IMAGE_REGISTRY_DIR = Path(__file__).resolve().parent / "registry" / "image"
VIDEO_REGISTRY_DIR = Path(__file__).resolve().parent / "registry" / "video"
AUDIO_REGISTRY_DIR = Path(__file__).resolve().parent / "registry" / "audio"


class ChatModelDefinition(BaseModel):
    id: str
    display_name: str
    api_path: str
    api_style: Literal["claude", "openai"]
    model_field: str
    price_hint: str
    estimate_credits: float | None = None
    supports_vision: bool = False
    supports_tools: bool = False
    default_params: dict[str, Any] = {}
    docs_url: str | None = None


class ModelParameter(BaseModel):
    name: str
    type: Literal["textarea", "select", "switch", "text", "number", "image_urls", "image_url"]
    required: bool = False
    max_length: int | None = None
    max_items: int | None = None
    options: list[str] | None = None
    default: str | bool | int | float | list[str] | None = None
    visible_when: dict[str, Any] | None = None
    required_when: dict[str, Any] | None = None


class ImageModelDefinition(BaseModel):
    id: str
    category: Literal["image"]
    display_name: str
    api_type: Literal["jobs"]
    create_path: str
    model_field: str
    price_hint: str
    estimate_credits: float | None = None
    parameters: list[ModelParameter] = Field(default_factory=list)
    docs_url: str | None = None


class VideoModelDefinition(BaseModel):
    id: str
    category: Literal["video"]
    display_name: str
    api_type: Literal["jobs"]
    create_path: str
    model_field: str
    price_hint: str
    estimate_credits: float | None = None
    parameters: list[ModelParameter] = Field(default_factory=list)
    docs_url: str | None = None


class AudioModelDefinition(BaseModel):
    id: str
    category: Literal["audio"]
    display_name: str
    api_type: Literal["suno", "jobs"]
    operation: str = "generate"
    model_field: str
    price_hint: str
    estimate_credits: float | None = None
    output_kind: Literal["audio", "text", "metadata"] = "audio"
    sync_result: bool = False
    parameters: list[ModelParameter] = Field(default_factory=list)
    docs_url: str | None = None


def _load_registry_dir(directory: Path, model_cls: type[BaseModel]) -> list[Any]:
    models: list[Any] = []
    if not directory.exists():
        return models
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        models.append(model_cls.model_validate(data))
    return models


@lru_cache
def get_chat_models() -> list[ChatModelDefinition]:
    return _load_registry_dir(CHAT_REGISTRY_DIR, ChatModelDefinition)


@lru_cache
def get_image_models() -> list[ImageModelDefinition]:
    return _load_registry_dir(IMAGE_REGISTRY_DIR, ImageModelDefinition)


@lru_cache
def get_video_models() -> list[VideoModelDefinition]:
    return _load_registry_dir(VIDEO_REGISTRY_DIR, VideoModelDefinition)


@lru_cache
def get_audio_models() -> list[AudioModelDefinition]:
    return _load_registry_dir(AUDIO_REGISTRY_DIR, AudioModelDefinition)


def clear_registry_cache() -> None:
    get_chat_models.cache_clear()
    get_image_models.cache_clear()
    get_video_models.cache_clear()
    get_audio_models.cache_clear()


def get_chat_model(model_id: str) -> ChatModelDefinition | None:
    for model in get_chat_models():
        if model.id == model_id:
            return model
    return None


def get_image_model(model_id: str) -> ImageModelDefinition | None:
    for model in get_image_models():
        if model.id == model_id:
            return model
    return None


def get_video_model(model_id: str) -> VideoModelDefinition | None:
    for model in get_video_models():
        if model.id == model_id:
            return model
    return None


def get_audio_model(model_id: str) -> AudioModelDefinition | None:
    for model in get_audio_models():
        if model.id == model_id:
            return model
    return None


def get_model_by_id(
    model_id: str,
) -> ChatModelDefinition | ImageModelDefinition | VideoModelDefinition | AudioModelDefinition | None:
    return (
        get_chat_model(model_id)
        or get_image_model(model_id)
        or get_video_model(model_id)
        or get_audio_model(model_id)
    )


def get_models(model_type: Literal["image", "video", "chat", "audio"]) -> list[Any]:
    if model_type == "image":
        return get_image_models()
    if model_type == "video":
        return get_video_models()
    if model_type == "audio":
        return get_audio_models()
    return get_chat_models()


def validate_model_input(
    model: ImageModelDefinition | VideoModelDefinition | AudioModelDefinition,
    input_data: dict[str, Any],
) -> dict[str, Any]:
    working_values: dict[str, Any] = dict(input_data)
    for param in model.parameters:
        if param.default is not None and param.name not in working_values:
            working_values[param.name] = param.default
        if param.type == "switch" and param.name not in working_values:
            working_values[param.name] = False

    validated: dict[str, Any] = {}
    for param in model.parameters:
        if not is_param_visible(working_values, param.visible_when):
            continue

        value = input_data.get(param.name)
        required = is_param_required(param.required, working_values, param.required_when)

        if param.type == "image_url":
            if value is None or value == "":
                if required:
                    raise ValueError(f"Missing required parameter: {param.name}")
                continue
            validated[param.name] = str(value).strip()
            continue
        if param.type == "image_urls":
            if value is None or value == "" or value == []:
                if required:
                    raise ValueError(f"Missing required parameter: {param.name}")
                validated[param.name] = []
                continue
            if not isinstance(value, list):
                raise ValueError(f"Parameter {param.name} must be a list of URLs")
            urls = [str(u).strip() for u in value if u]
            max_items = param.max_items or 2
            if len(urls) > max_items:
                raise ValueError(f"Parameter {param.name} allows at most {max_items} URLs")
            validated[param.name] = urls
            continue
        if value is None or value == "":
            if required:
                raise ValueError(f"Missing required parameter: {param.name}")
            if param.default is not None:
                validated[param.name] = param.default
            continue
        if param.type == "textarea" or param.type == "text":
            text = str(value)
            if param.max_length and len(text) > param.max_length:
                raise ValueError(f"Parameter {param.name} exceeds max length {param.max_length}")
            validated[param.name] = text
        elif param.type == "select":
            str_value = str(value)
            if param.options and str_value not in param.options:
                raise ValueError(f"Invalid value for {param.name}: {str_value}")
            if param.name == "duration" and (
                model.id.startswith("bytedance/")
                or getattr(model, "model_field", "").startswith("bytedance/")
            ):
                validated[param.name] = int(str_value)
            else:
                validated[param.name] = str_value
        elif param.type == "switch":
            validated[param.name] = bool(value)
        elif param.type == "number":
            validated[param.name] = float(value)
        else:
            validated[param.name] = value
    return validated
