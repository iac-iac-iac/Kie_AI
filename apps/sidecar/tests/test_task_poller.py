from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from kie_sidecar.db.chat_repository import ChatRepository
from kie_sidecar.db.generation_repository import GenerationRepository
from kie_sidecar.db.repository import SettingsRepository
from kie_sidecar.kie.jobs import JobsClient, TaskRecord
from kie_sidecar.models.settings import AppSettings
from kie_sidecar.services.event_bus import EventBus
from kie_sidecar.services.media_downloader import MediaDownloader
from kie_sidecar.services.media_store import MediaStore
from kie_sidecar.services.task_poller import TaskPoller


@pytest.mark.asyncio
async def test_task_poller_success_flow(tmp_path):
    db_path = tmp_path / "test.db"
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"
    settings_repo = SettingsRepository(db_path)
    await settings_repo.init(schema)

    generation_repo = GenerationRepository(db_path)
    chat_repo = ChatRepository(db_path)
    media_store = MediaStore(tmp_path / "images", tmp_path / "videos", tmp_path / "audio")
    media_downloader = MediaDownloader()

    gen = await generation_repo.create_generation(
        type="image",
        model_id="flux-2/flex-text-to-image",
        task_id="task-99",
        prompt="sunset",
        params={"prompt": "sunset"},
    )

    kie = MagicMock()
    jobs_mock = MagicMock(spec=JobsClient)
    jobs_mock.get_task_record = AsyncMock(
        return_value=TaskRecord(
            task_id="task-99",
            state="success",
            result_urls=["https://cdn.example.com/out.png"],
            credits_consumed=10.0,
            fail_msg=None,
            raw={},
        )
    )
    jobs_mock.get_download_url = AsyncMock(return_value="https://signed.example.com/out.png")
    media_downloader.download_to_path = AsyncMock(
        side_effect=lambda url, dest: dest.write_bytes(b"\x89PNG\r\n")
    )

    poller = TaskPoller(
        kie,
        generation_repo,
        chat_repo,
        media_store,
        media_downloader,
        EventBus(),
        lambda: AppSettings(),
        poll_interval=0.1,
    )

    original_process = poller._process_generation

    async def patched_process(jobs, generation):
        await original_process(jobs_mock, generation)

    poller._process_generation = patched_process  # type: ignore[method-assign]
    await poller._poll_once()

    updated = await generation_repo.get_generation(gen.id)
    assert updated is not None
    assert updated.status == "success"
    assert updated.credits_used == 10.0
    assert updated.local_path is not None
    assert Path(updated.local_path).exists()
    assert "images" in updated.local_path.replace("\\", "/")

    spent = await chat_repo.get_session_spent()
    assert spent == 10.0

    await media_downloader.close()


@pytest.mark.asyncio
async def test_task_poller_video_success_flow(tmp_path):
    db_path = tmp_path / "test.db"
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"
    settings_repo = SettingsRepository(db_path)
    await settings_repo.init(schema)

    generation_repo = GenerationRepository(db_path)
    chat_repo = ChatRepository(db_path)
    media_store = MediaStore(tmp_path / "images", tmp_path / "videos", tmp_path / "audio")
    media_downloader = MediaDownloader()

    gen = await generation_repo.create_generation(
        type="video",
        model_id="kling-2.6/text-to-video",
        task_id="task-vid-1",
        prompt="ocean waves",
        params={"prompt": "ocean waves"},
    )

    kie = MagicMock()
    jobs_mock = MagicMock(spec=JobsClient)
    jobs_mock.get_task_record = AsyncMock(
        return_value=TaskRecord(
            task_id="task-vid-1",
            state="success",
            result_urls=["https://cdn.example.com/out.mp4"],
            credits_consumed=200.0,
            fail_msg=None,
            raw={},
        )
    )
    jobs_mock.get_download_url = AsyncMock(return_value="https://signed.example.com/out.mp4")
    media_downloader.download_to_path = AsyncMock(
        side_effect=lambda url, dest: dest.write_bytes(b"\x00\x00\x00\x20ftypmp42")
    )

    poller = TaskPoller(
        kie,
        generation_repo,
        chat_repo,
        media_store,
        media_downloader,
        EventBus(),
        lambda: AppSettings(),
        poll_interval=0.1,
    )

    original_process = poller._process_generation

    async def patched_process(jobs, generation):
        await original_process(jobs_mock, generation)

    poller._process_generation = patched_process  # type: ignore[method-assign]
    await poller._poll_once()

    updated = await generation_repo.get_generation(gen.id)
    assert updated is not None
    assert updated.status == "success"
    assert updated.local_path is not None
    assert "videos" in updated.local_path.replace("\\", "/")
    assert updated.local_path.endswith(".mp4")

    await media_downloader.close()
