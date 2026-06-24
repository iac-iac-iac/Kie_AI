from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from kie_sidecar.kie.errors import KieApiError, KieAuthError, KieInsufficientCreditsError
from kie_sidecar.kie.jobs import JobsClient
from kie_sidecar.kie.suno import SunoClient, build_suno_payload
from kie_sidecar.models.generation import CreateGenerationRequest, GenerationRecord
from kie_sidecar.models.registry import (
    get_audio_model,
    get_image_model,
    get_video_model,
    validate_model_input,
)
from kie_sidecar.services.generation_dto import generation_to_dto, generation_to_event_data
from kie_sidecar.services.session_limits import SessionLimitExceeded, check_can_spend

router = APIRouter(prefix="/generations", tags=["generations"])


def _to_dto(record) -> GenerationRecord:
    return generation_to_dto(record)


@router.post("", response_model=GenerationRecord)
async def create_generation(
    request: Request,
    body: CreateGenerationRequest,
) -> GenerationRecord:
    state = request.app.state.app_state
    if not state.settings.api_key:
        raise HTTPException(status_code=401, detail="API key is not configured")

    audio_model = get_audio_model(body.model_id)
    image_model = get_image_model(body.model_id)
    video_model = get_video_model(body.model_id)
    model = audio_model or image_model or video_model
    if not model:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model_id}")

    if audio_model:
        gen_type: Literal["image", "video", "audio"] = "audio"
    elif video_model:
        gen_type = "video"
    else:
        gen_type = "image"

    try:
        estimate = model.estimate_credits or 0
        await check_can_spend(state.chat_repo, state.app_settings, estimate)
    except SessionLimitExceeded as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    try:
        validated_input = validate_model_input(model, body.input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prompt = validated_input.get("prompt") or validated_input.get("text") or validated_input.get("content")
    task_id: str | None = None
    try:
        if audio_model:
            if audio_model.api_type == "jobs":
                jobs = JobsClient(state.kie.http_client)
                task_id = await jobs.create_task(audio_model.model_field, validated_input)
            else:
                suno = SunoClient(state.kie.http_client)
                try:
                    payload = build_suno_payload(
                        audio_model.operation,
                        audio_model.model_field,
                        validated_input,
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc)) from exc
                create_result = await suno.create_task(audio_model.operation, payload)
                if audio_model.sync_result:
                    record = await state.generation_repo.create_generation(
                        type=gen_type,
                        model_id=body.model_id,
                        task_id=None,
                        prompt=str(prompt) if prompt else None,
                        params=validated_input,
                    )
                    sync_data = create_result.sync_data or {}
                    result_path = state.media_store.resolve_local_path(
                        record.id,
                        "audio",
                        "json",
                    )
                    result_path.write_text(
                        json.dumps(sync_data, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    updated = await state.generation_repo.update_status(
                        record.id,
                        status="success",
                        local_path=str(result_path),
                    )
                    if updated:
                        await state.event_bus.broadcast(
                            "generation.updated",
                            generation_to_event_data(updated),
                        )
                        return _to_dto(updated)
                    return _to_dto(record)
                task_id = create_result.task_id
        else:
            jobs = JobsClient(state.kie.http_client)
            task_id = await jobs.create_task(model.model_field, validated_input)
    except KieAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except KieInsufficientCreditsError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except KieApiError as exc:
        raise HTTPException(status_code=exc.code if exc.code < 600 else 500, detail=str(exc)) from exc

    record = await state.generation_repo.create_generation(
        type=gen_type,
        model_id=body.model_id,
        task_id=task_id,
        prompt=str(prompt) if prompt else None,
        params=validated_input,
    )
    await state.event_bus.broadcast("generation.updated", generation_to_event_data(record))
    return _to_dto(record)


@router.get("", response_model=list[GenerationRecord])
async def list_generations(
    request: Request,
    type: Literal["image", "video", "audio"] = Query(default="image"),
) -> list[GenerationRecord]:
    state = request.app.state.app_state
    records = await state.generation_repo.list_generations(type=type)
    return [_to_dto(r) for r in records]


@router.get("/{generation_id}", response_model=GenerationRecord)
async def get_generation(request: Request, generation_id: str) -> GenerationRecord:
    state = request.app.state.app_state
    record = await state.generation_repo.get_generation(generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Generation not found")
    return _to_dto(record)


@router.get("/{generation_id}/file")
async def get_generation_file(request: Request, generation_id: str) -> FileResponse:
    state = request.app.state.app_state
    record = await state.generation_repo.get_generation(generation_id)
    if not record or not record.local_path:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(record.local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    media_type = "video/mp4"
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif suffix == ".webp":
        media_type = "image/webp"
    elif suffix == ".png":
        media_type = "image/png"
    elif suffix == ".webm":
        media_type = "video/webm"
    elif suffix == ".mov":
        media_type = "video/quicktime"
    elif suffix == ".mp3":
        media_type = "audio/mpeg"
    elif suffix == ".wav":
        media_type = "audio/wav"
    elif suffix == ".ogg":
        media_type = "audio/ogg"
    elif suffix == ".txt":
        media_type = "text/plain; charset=utf-8"
    elif suffix == ".json":
        media_type = "application/json"
    return FileResponse(path, media_type=media_type)


@router.post("/{generation_id}/retry", response_model=GenerationRecord)
async def retry_generation_download(
    request: Request,
    generation_id: str,
) -> GenerationRecord:
    state = request.app.state.app_state
    record = await state.generation_repo.get_generation(generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Generation not found")
    if record.status != "failed" or not record.task_id:
        raise HTTPException(status_code=400, detail="Generation cannot be retried")
    if record.local_path and Path(record.local_path).exists():
        raise HTTPException(status_code=400, detail="Generation already completed")
    updated = await state.generation_repo.requeue_generation(generation_id)
    if not updated:
        raise HTTPException(status_code=400, detail="Generation cannot be retried")
    await state.event_bus.broadcast("generation.updated", generation_to_event_data(updated))
    return _to_dto(updated)


@router.delete("/{generation_id}", status_code=204)
async def delete_generation(request: Request, generation_id: str) -> None:
    state = request.app.state.app_state
    record = await state.generation_repo.delete_generation(generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Generation not found")
    state.media_store.delete_file(record.local_path)
