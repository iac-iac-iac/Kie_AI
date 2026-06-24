from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["system"])


class SystemPathsResponse(BaseModel):
    data_dir: str
    db_path: str
    media_dir: str
    images_dir: str
    videos_dir: str
    logs_dir: str


@router.get("/system/paths", response_model=SystemPathsResponse)
async def get_system_paths(request: Request) -> SystemPathsResponse:
    settings = request.app.state.app_state.settings
    data_dir = settings.data_dir
    media_dir = settings.media_dir
    return SystemPathsResponse(
        data_dir=str(data_dir),
        db_path=str(settings.db_path),
        media_dir=str(media_dir),
        images_dir=str(media_dir / "images"),
        videos_dir=str(media_dir / "videos"),
        logs_dir=str(data_dir / "logs"),
    )
