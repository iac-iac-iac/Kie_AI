from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from kie_sidecar.kie.errors import KieApiError, KieAuthError
from kie_sidecar.models.settings import AppSettings, AppSettingsPatch

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
async def get_settings(request: Request) -> AppSettings:
    state = request.app.state.app_state
    return state.app_settings


@router.patch("", response_model=AppSettings)
async def patch_settings(request: Request, body: AppSettingsPatch) -> AppSettings:
    state = request.app.state.app_state
    patch = body.model_dump(exclude_none=True)
    state.app_settings = await state.repo.patch_app_settings(patch)
    if "proxy" in patch:
        await state.kie.reload_proxy(state.app_settings.proxy)
        await state.file_uploader.reload_proxy(state.app_settings.proxy)
        await state.task_poller.reload_proxy(state.app_settings.proxy)
    return state.app_settings
