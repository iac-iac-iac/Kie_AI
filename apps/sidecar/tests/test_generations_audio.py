from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from kie_sidecar.db.chat_repository import ChatRepository
from kie_sidecar.db.generation_repository import GenerationRepository
from kie_sidecar.db.repository import SettingsRepository
from kie_sidecar.kie.jobs import JobsClient, TaskRecord
from kie_sidecar.kie.suno import SunoTaskRecord, build_suno_payload
from kie_sidecar.models.settings import AppSettings
from kie_sidecar.services.event_bus import EventBus
from kie_sidecar.services.media_downloader import MediaDownloader
from kie_sidecar.services.media_store import MediaStore
from kie_sidecar.services.task_poller import TaskPoller


def test_media_store_guess_extension_audio():
    store = MediaStore(Path("/tmp/i"), Path("/tmp/v"), Path("/tmp/a"))
    assert store.guess_extension("https://cdn.example.com/track.mp3", media_type="audio") == "mp3"
    assert (
        store.guess_extension("https://cdn.example.com/track.wav", "audio/wav", media_type="audio")
        == "wav"
    )


def test_audio_models_api(client):
    response = client.get("/api/v1/models", params={"type": "audio"})
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 24
    assert all(m["category"] == "audio" for m in models)
    ids = {m["id"] for m in models}
    assert "suno/v5" in ids
    assert "suno/v5-5" in ids
    assert "suno/lyrics" in ids
    assert "elevenlabs/text-to-speech-multilingual-v2" in ids


def test_build_suno_payload_simple():
    payload = build_suno_payload(
        "generate",
        "V4_5",
        {"prompt": "upbeat summer pop", "instrumental": True, "custom_mode": False},
    )
    assert payload["customMode"] is False
    assert payload["instrumental"] is True
    assert payload["model"] == "V4_5"
    assert payload["prompt"] == "upbeat summer pop"
    assert "style" not in payload
    assert "title" not in payload
    assert "negativeTags" not in payload


def test_build_suno_payload_custom():
    payload = build_suno_payload(
        "generate",
        "V3_5",
        {
            "prompt": "Verse lyrics here",
            "instrumental": False,
            "custom_mode": True,
            "style": "indie folk, acoustic guitar",
            "title": "Morning Light",
            "negative_tags": "electronic, drums",
        },
    )
    assert payload["customMode"] is True
    assert payload["style"] == "indie folk, acoustic guitar"
    assert payload["title"] == "Morning Light"
    assert payload["negativeTags"] == "electronic, drums"


def test_build_suno_payload_custom_requires_style():
    with pytest.raises(ValueError, match="style is required"):
        build_suno_payload(
            "generate",
            "V5",
            {
                "prompt": "lyrics",
                "custom_mode": True,
                "title": "Track",
            },
        )


def test_build_suno_payload_lyrics():
    payload = build_suno_payload("lyrics", "", {"prompt": "A song about summer"})
    assert payload["prompt"] == "A song about summer"
    assert "callBackUrl" in payload


def test_build_suno_payload_extend_requires_style_when_default_flag():
    with pytest.raises(ValueError, match="style is required"):
        build_suno_payload(
            "extend",
            "V4_5",
            {
                "audio_id": "abc123",
                "default_param_flag": True,
                "title": "Track",
                "continue_at": 60,
            },
        )


def test_generations_audio_list_empty(client):
    response = client.get("/api/v1/generations", params={"type": "audio"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_task_poller_audio_success_flow(tmp_path):
    db_path = tmp_path / "test.db"
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"
    settings_repo = SettingsRepository(db_path)
    await settings_repo.init(schema)

    generation_repo = GenerationRepository(db_path)
    chat_repo = ChatRepository(db_path)
    media_store = MediaStore(tmp_path / "images", tmp_path / "videos", tmp_path / "audio")
    media_downloader = MediaDownloader()

    gen = await generation_repo.create_generation(
        type="audio",
        model_id="suno/v3-5",
        task_id="task-audio-1",
        prompt="calm piano",
        params={"prompt": "calm piano", "instrumental": True},
    )

    kie = MagicMock()
    kie.http_client = MagicMock()

    suno_record = SunoTaskRecord(
        task_id="task-audio-1",
        state="success",
        result_urls=["https://cdn.example.com/out.mp3"],
        text_content=None,
        credits_consumed=None,
        fail_msg=None,
        raw={"status": "SUCCESS"},
    )

    jobs_mock = MagicMock(spec=JobsClient)
    jobs_mock.get_download_url = AsyncMock(return_value="https://signed.example.com/out.mp3")
    media_downloader.download_to_path = AsyncMock(
        side_effect=lambda url, dest: dest.write_bytes(b"ID3")
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

    async def patched_process(jobs, generation, media_type="audio"):
        import kie_sidecar.services.task_poller as tp

        original_suno = tp.SunoClient

        class FakeSuno:
            def __init__(self, _client):
                pass

            async def get_record(self, _operation, _task_id):
                return suno_record

        tp.SunoClient = FakeSuno
        try:
            await original_process(jobs_mock, generation)
        finally:
            tp.SunoClient = original_suno

    poller._process_generation = patched_process  # type: ignore[method-assign]
    await poller._poll_once()

    updated = await generation_repo.get_generation(gen.id)
    assert updated is not None
    assert updated.status == "success"
    assert updated.local_path is not None
    assert "audio" in updated.local_path.replace("\\", "/")
    assert updated.local_path.endswith(".mp3")

    await media_downloader.close()
