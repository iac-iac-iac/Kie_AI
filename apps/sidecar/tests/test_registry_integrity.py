from __future__ import annotations

import json
from pathlib import Path

import pytest

from kie_sidecar.models.registry import (
    CHAT_REGISTRY_DIR,
    IMAGE_REGISTRY_DIR,
    VIDEO_REGISTRY_DIR,
    ChatModelDefinition,
    ImageModelDefinition,
    VideoModelDefinition,
    get_chat_models,
    get_image_models,
    get_video_models,
    validate_model_input,
)


def _load_json_models(directory: Path, model_cls: type) -> list:
    models = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        models.append(model_cls.model_validate(data))
    return models


def test_registry_json_validates():
    chat = _load_json_models(CHAT_REGISTRY_DIR, ChatModelDefinition)
    image = _load_json_models(IMAGE_REGISTRY_DIR, ImageModelDefinition)
    video = _load_json_models(VIDEO_REGISTRY_DIR, VideoModelDefinition)
    assert len(chat) == 31
    assert len(image) == 59
    assert len(video) == 97


def test_registry_ids_unique():
    ids: list[str] = []
    for directory in (CHAT_REGISTRY_DIR, IMAGE_REGISTRY_DIR, VIDEO_REGISTRY_DIR):
        for path in directory.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            ids.append(data["id"])
    assert len(ids) == len(set(ids))


def test_image_video_models_have_required_primary_input():
    for model in get_image_models() + get_video_models():
        required = [p for p in model.parameters if p.required]
        assert required, f"{model.id} has no required parameters"
        names = {p.name for p in required}
        assert names & {"prompt", "image_url", "input_urls", "image_urls", "video_url", "audio_url"}, (
            f"{model.id} missing primary input: {names}"
        )


def _model_by_id(models, model_id: str):
    return next(m for m in models if m.id == model_id)


def test_validate_i2i_image_urls():
    model = _model_by_id(get_image_models(), "flux-2/flex-image-to-image")
    validated = validate_model_input(
        model,
        {
            "input_urls": ["https://example.com/a.png"],
            "prompt": "test",
            "aspect_ratio": "1:1",
            "resolution": "1K",
        },
    )
    assert validated["input_urls"] == ["https://example.com/a.png"]


def test_validate_seedance_duration_int():
    model = _model_by_id(get_video_models(), "bytedance/seedance-1.5-pro")
    validated = validate_model_input(
        model,
        {"prompt": "test", "duration": "5"},
    )
    assert validated["duration"] == 5
    assert isinstance(validated["duration"], int)


def test_validate_image_url_optional_skip():
    model = _model_by_id(get_video_models(), "bytedance/seedance-2-fast")
    validated = validate_model_input(model, {"prompt": "test"})
    assert "first_frame_url" not in validated


@pytest.mark.parametrize(
    "model_id,key_param",
    [
        ("flux-2/flex-image-to-image", "input_urls"),
        ("google/nano-banana-edit", "input_urls"),
        ("grok-imagine/text-to-video", "prompt"),
        ("kling/v2-5-turbo-text-to-video-pro", "prompt"),
        ("bytedance/seedance-2", "prompt"),
    ],
)
def test_schema_api_smoke(client, model_id: str, key_param: str):
    response = client.get(f"/api/v1/models/{model_id}/schema")
    assert response.status_code == 200
    schema = response.json()
    assert schema["id"] == model_id
    assert any(p["name"] == key_param for p in schema["parameters"])
