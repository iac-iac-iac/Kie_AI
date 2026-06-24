from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kie_sidecar.config import Settings
from kie_sidecar.db.chat_repository import ChatRepository
from kie_sidecar.db.generation_repository import GenerationRepository
from kie_sidecar.db.models_cache_repository import ModelsCacheRepository
from kie_sidecar.db.repository import SettingsRepository
from kie_sidecar.kie.client import KieClient
from kie_sidecar.kie.files import FileUploader
from kie_sidecar.models.settings import AppSettings
from kie_sidecar.services.event_bus import EventBus
from kie_sidecar.services.media_downloader import MediaDownloader
from kie_sidecar.services.media_store import MediaStore
from kie_sidecar.services.task_poller import TaskPoller


@dataclass
class AppState:
    settings: Settings
    repo: SettingsRepository
    chat_repo: ChatRepository
    generation_repo: GenerationRepository
    models_cache_repo: ModelsCacheRepository
    kie: KieClient
    file_uploader: FileUploader
    media_store: MediaStore
    media_downloader: MediaDownloader
    task_poller: TaskPoller
    event_bus: EventBus
    app_settings: AppSettings
    _settings_ref: list[AppSettings] = field(repr=False)

    async def reload_kie_client(self) -> None:
        self.app_settings = await self.repo.get_app_settings()
        self._settings_ref[0] = self.app_settings
        self.kie.update_credentials(self.settings.api_key)
        self.file_uploader.update_credentials(self.settings.api_key)
        await self.kie.reload_proxy(self.app_settings.proxy)
        await self.file_uploader.reload_proxy(self.app_settings.proxy)
        await self.task_poller.reload_proxy(self.app_settings.proxy)


def create_app_state(env_settings: Settings) -> AppState:
    repo = SettingsRepository(env_settings.db_path)
    chat_repo = ChatRepository(env_settings.db_path)
    generation_repo = GenerationRepository(env_settings.db_path)
    models_cache_repo = ModelsCacheRepository(env_settings.db_path)
    kie = KieClient(
        api_key=env_settings.api_key,
        base_url=env_settings.kie_base_url,
    )
    media_store = MediaStore(
        images_dir=env_settings.media_dir / "images",
        videos_dir=env_settings.media_dir / "videos",
        audio_dir=env_settings.media_dir / "audio",
    )
    media_downloader = MediaDownloader()
    event_bus = EventBus()
    settings_ref: list[AppSettings] = [AppSettings()]

    def get_app_settings() -> AppSettings:
        return settings_ref[0]

    task_poller = TaskPoller(
        kie=kie,
        generation_repo=generation_repo,
        chat_repo=chat_repo,
        media_store=media_store,
        media_downloader=media_downloader,
        event_bus=event_bus,
        get_app_settings=get_app_settings,
    )
    return AppState(
        settings=env_settings,
        repo=repo,
        chat_repo=chat_repo,
        generation_repo=generation_repo,
        models_cache_repo=models_cache_repo,
        kie=kie,
        file_uploader=FileUploader(api_key=env_settings.api_key),
        media_store=media_store,
        media_downloader=media_downloader,
        task_poller=task_poller,
        event_bus=event_bus,
        app_settings=settings_ref[0],
        _settings_ref=settings_ref,
    )
