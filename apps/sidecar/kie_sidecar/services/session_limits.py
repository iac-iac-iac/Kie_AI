from __future__ import annotations

from dataclasses import dataclass

from kie_sidecar.db.chat_repository import ChatRepository
from kie_sidecar.models.settings import AppSettings
from kie_sidecar.services.event_bus import EventBus


class SessionLimitExceeded(Exception):
    pass


@dataclass(frozen=True)
class SessionUsage:
    spent: float
    limit: float | None
    remaining: float | None


async def get_usage(repo: ChatRepository, settings: AppSettings) -> SessionUsage:
    spent = await repo.get_session_spent()
    limit = settings.session_limit_credits if settings.session_limit_enabled else None
    remaining = (limit - spent) if limit is not None else None
    return SessionUsage(spent=spent, limit=limit, remaining=remaining)


async def check_can_spend(
    repo: ChatRepository,
    settings: AppSettings,
    estimated: float = 0,
) -> None:
    if not settings.session_limit_enabled or not settings.session_limit_credits:
        return
    spent = await repo.get_session_spent()
    if spent + estimated > settings.session_limit_credits:
        raise SessionLimitExceeded("Session credit limit exceeded")


async def _emit_session_usage(
    repo: ChatRepository,
    settings: AppSettings,
    event_bus: EventBus,
) -> None:
    if not settings.session_limit_enabled:
        return
    usage = await get_usage(repo, settings)
    await event_bus.broadcast(
        "session.usage",
        {"spent": usage.spent, "limit": usage.limit},
    )


async def record_spent(
    repo: ChatRepository,
    credits: float,
    *,
    event_bus: EventBus | None = None,
    settings: AppSettings | None = None,
) -> None:
    if credits > 0:
        await repo.add_session_credits(credits)
    if event_bus is not None and settings is not None:
        await _emit_session_usage(repo, settings, event_bus)


async def reset_session(
    repo: ChatRepository,
    *,
    event_bus: EventBus | None = None,
    settings: AppSettings | None = None,
) -> None:
    await repo.reset_session()
    if event_bus is not None and settings is not None:
        await _emit_session_usage(repo, settings, event_bus)
