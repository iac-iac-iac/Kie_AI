from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from kie_sidecar.models.generation import ModelInfo, ModelSchemaResponse
from kie_sidecar.models.registry import (
    get_audio_model,
    get_audio_models,
    get_image_model,
    get_image_models,
    get_models,
    get_video_model,
    get_video_models,
)
from kie_sidecar.services.pricing import get_merged_pricing

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelInfo])
async def list_models(
    request: Request,
    type: Literal["image", "video", "chat", "audio"] = Query(default="image"),
) -> list[ModelInfo]:
    state = request.app.state.app_state
    if type == "image":
        result: list[ModelInfo] = []
        for m in get_image_models():
            pricing = await get_merged_pricing(state.models_cache_repo, m, "image")
            result.append(
                ModelInfo(
                    id=m.id,
                    display_name=m.display_name,
                    price_hint=pricing.price_hint,
                    category="image",
                    estimate_credits=pricing.estimate_credits,
                    price_updated_at=pricing.price_updated_at,
                )
            )
        return result
    if type == "video":
        result = []
        for m in get_video_models():
            pricing = await get_merged_pricing(state.models_cache_repo, m, "video")
            result.append(
                ModelInfo(
                    id=m.id,
                    display_name=m.display_name,
                    price_hint=pricing.price_hint,
                    category="video",
                    estimate_credits=pricing.estimate_credits,
                    price_updated_at=pricing.price_updated_at,
                )
            )
        return result
    if type == "audio":
        result = []
        for m in get_audio_models():
            pricing = await get_merged_pricing(state.models_cache_repo, m, "audio")
            result.append(
                ModelInfo(
                    id=m.id,
                    display_name=m.display_name,
                    price_hint=pricing.price_hint,
                    category="audio",
                    estimate_credits=pricing.estimate_credits,
                    price_updated_at=pricing.price_updated_at,
                )
            )
        return result
    models_list = get_models("chat")
    result = []
    for m in models_list:
        pricing = await get_merged_pricing(state.models_cache_repo, m, "chat")
        result.append(
            ModelInfo(
                id=m.id,
                display_name=m.display_name,
                price_hint=pricing.price_hint,
                category="chat",
                estimate_credits=pricing.estimate_credits,
                price_updated_at=pricing.price_updated_at,
            )
        )
    return result


@router.get("/{model_id:path}/schema", response_model=ModelSchemaResponse)
async def get_model_schema(request: Request, model_id: str) -> ModelSchemaResponse:
    state = request.app.state.app_state
    model = get_image_model(model_id) or get_video_model(model_id) or get_audio_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    if get_audio_model(model_id):
        category = "audio"
    elif get_video_model(model_id):
        category = "video"
    else:
        category = "image"
    pricing = await get_merged_pricing(state.models_cache_repo, model, category)
    return ModelSchemaResponse(
        id=model.id,
        display_name=model.display_name,
        price_hint=pricing.price_hint,
        estimate_credits=pricing.estimate_credits,
        price_updated_at=pricing.price_updated_at,
        parameters=model.parameters,
    )
