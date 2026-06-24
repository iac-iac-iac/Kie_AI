from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Literal

import httpx
import structlog

from kie_sidecar.kie.errors import KieRateLimitError
from kie_sidecar.kie.jobs import JobsClient
from kie_sidecar.kie.suno import SunoClient, SunoTaskRecord, suno_to_task_record
from kie_sidecar.models.registry import get_audio_model
from kie_sidecar.models.settings import AppSettings, ProxySettings
from kie_sidecar.services.generation_dto import generation_to_event_data
from kie_sidecar.services.session_limits import record_spent

if TYPE_CHECKING:
    from kie_sidecar.db.chat_repository import ChatRepository
    from kie_sidecar.db.generation_repository import GenerationRepository
    from kie_sidecar.services.event_bus import EventBus
    from kie_sidecar.services.media_downloader import MediaDownloader
    from kie_sidecar.services.media_store import MediaStore
    from kie_sidecar.kie.client import KieClient

logger = structlog.get_logger()

_TRANSIENT_DOWNLOAD_RETRIES = 20
MediaType = Literal["image", "video", "audio"]


def _format_error(exc: Exception, media_type: MediaType = "image") -> str:
    message = str(exc).strip()
    if message:
        return message
    name = type(exc).__name__
    label = {"video": "video", "audio": "audio"}.get(media_type, "image")
    if isinstance(exc, httpx.TimeoutException):
        return f"{label.capitalize()} download timed out. Check proxy settings or try again."
    if isinstance(exc, httpx.ConnectError):
        return f"Could not connect to download the {label}. Check proxy or network."
    return name or "Unknown error"


class TaskPoller:
    def __init__(
        self,
        kie: KieClient,
        generation_repo: GenerationRepository,
        chat_repo: ChatRepository,
        media_store: MediaStore,
        media_downloader: MediaDownloader,
        event_bus: EventBus,
        get_app_settings: Callable[[], AppSettings],
        poll_interval: float = 4.0,
    ) -> None:
        self._kie = kie
        self._generation_repo = generation_repo
        self._chat_repo = chat_repo
        self._media_store = media_store
        self._media_downloader = media_downloader
        self._event_bus = event_bus
        self._get_app_settings = get_app_settings
        self._poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._retry_counts: dict[str, int] = {}

    async def reload_proxy(self, proxy: ProxySettings) -> None:
        await self._media_downloader.reload_proxy(proxy)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _emit_generation(self, generation_id: str) -> None:
        record = await self._generation_repo.get_generation(generation_id)
        if record:
            await self._event_bus.broadcast(
                "generation.updated",
                generation_to_event_data(record),
            )

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._poll_once()
            except Exception:
                logger.exception("task_poller_cycle_error")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval)
                break
            except asyncio.TimeoutError:
                continue

    async def _poll_once(self) -> None:
        pending = await self._generation_repo.list_pending()
        if not pending:
            return
        jobs = JobsClient(self._kie.http_client)
        for generation in pending:
            if not generation.task_id:
                continue
            media_type: MediaType = generation.type  # type: ignore[assignment]
            try:
                await self._process_generation(
                    jobs,
                    generation,
                )
            except KieRateLimitError:
                logger.warning("task_poller_rate_limited", generation_id=generation.id)
                await asyncio.sleep(5)
            except Exception as exc:
                logger.exception("task_poller_generation_error", generation_id=generation.id)
                retries = self._retry_counts.get(generation.id, 0) + 1
                self._retry_counts[generation.id] = retries
                max_retries = (
                    _TRANSIENT_DOWNLOAD_RETRIES
                    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))
                    else 5
                )
                if retries >= max_retries:
                    await self._generation_repo.update_status(
                        generation.id,
                        status="failed",
                        error_msg=_format_error(exc, media_type),
                    )
                    self._retry_counts.pop(generation.id, None)
                    await self._emit_generation(generation.id)

    async def _process_generation(
        self,
        jobs: JobsClient,
        generation,
    ) -> None:
        generation_id = generation.id
        task_id = generation.task_id
        media_type: MediaType = generation.type  # type: ignore[assignment]
        if not task_id:
            return

        audio_model = get_audio_model(generation.model_id) if media_type == "audio" else None
        suno_record: SunoTaskRecord | None = None

        if media_type == "audio" and audio_model and audio_model.api_type == "suno":
            suno = SunoClient(self._kie.http_client)
            suno_record = await suno.get_record(audio_model.operation, task_id)
            record = suno_to_task_record(suno_record)
        else:
            record = await jobs.get_task_record(task_id)

        if record.state == "pending":
            return
        if record.state == "running":
            await self._generation_repo.update_status(generation_id, status="running")
            await self._emit_generation(generation_id)
            return
        if record.state == "failed":
            await self._generation_repo.update_status(
                generation_id,
                status="failed",
                error_msg=record.fail_msg or "Generation failed",
            )
            self._retry_counts.pop(generation_id, None)
            await self._emit_generation(generation_id)
            return
        if record.state != "success":
            return

        if (
            suno_record
            and audio_model
            and audio_model.output_kind == "text"
            and suno_record.text_content
        ):
            dest = self._media_store.resolve_local_path(generation_id, "audio", "txt")
            dest.write_text(suno_record.text_content, encoding="utf-8")
            await self._generation_repo.update_status(
                generation_id,
                status="success",
                credits_used=record.credits_consumed,
                local_path=str(dest),
            )
            if record.credits_consumed:
                await record_spent(
                    self._chat_repo,
                    record.credits_consumed,
                    event_bus=self._event_bus,
                    settings=self._get_app_settings(),
                )
                await self._event_bus.broadcast(
                    "credits.updated",
                    {"credits_consumed": record.credits_consumed},
                )
            self._retry_counts.pop(generation_id, None)
            await self._emit_generation(generation_id)
            logger.info("generation_completed", generation_id=generation_id, media_type=media_type)
            return

        if not record.result_urls:
            await self._generation_repo.update_status(
                generation_id,
                status="failed",
                error_msg="No result URL in task response",
            )
            self._retry_counts.pop(generation_id, None)
            await self._emit_generation(generation_id)
            return

        remote_url = record.result_urls[0]
        await self._generation_repo.update_status(
            generation_id,
            status="running",
            remote_url=remote_url,
            credits_used=record.credits_consumed,
        )
        await self._emit_generation(generation_id)
        local_path = await self._download_media(
            jobs,
            generation_id,
            remote_url,
            media_type,
        )
        await self._generation_repo.update_status(
            generation_id,
            status="success",
            credits_used=record.credits_consumed,
            remote_url=remote_url,
            local_path=str(local_path),
        )
        if record.credits_consumed:
            await record_spent(
                self._chat_repo,
                record.credits_consumed,
                event_bus=self._event_bus,
                settings=self._get_app_settings(),
            )
            await self._event_bus.broadcast(
                "credits.updated",
                {"credits_consumed": record.credits_consumed},
            )
        self._retry_counts.pop(generation_id, None)
        await self._emit_generation(generation_id)
        logger.info(
            "generation_completed",
            generation_id=generation_id,
            media_type=media_type,
            credits=record.credits_consumed,
        )

    async def _download_media(
        self,
        jobs: JobsClient,
        generation_id: str,
        remote_url: str,
        media_type: MediaType,
    ) -> Path:
        extension = self._media_store.guess_extension(remote_url, media_type=media_type)
        dest = self._media_store.resolve_local_path(generation_id, media_type, extension)
        candidates = [remote_url]
        try:
            signed_url = await jobs.get_download_url(remote_url)
            if signed_url not in candidates:
                candidates.append(signed_url)
        except Exception as exc:
            logger.warning("get_download_url_failed", error=_format_error(exc, media_type))

        last_error: Exception | None = None
        for url in candidates:
            try:
                if dest.exists():
                    dest.unlink()
                await self._media_downloader.download_to_path(url, dest)
                return dest
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "media_download_attempt_failed",
                    media_type=media_type,
                    url=url[:120],
                    error=_format_error(exc, media_type),
                )
        raise last_error or RuntimeError("Media download failed")
