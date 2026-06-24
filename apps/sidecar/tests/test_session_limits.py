from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kie_sidecar.db.chat_repository import ChatRepository
from kie_sidecar.db.repository import SettingsRepository
from kie_sidecar.models.settings import AppSettings
from kie_sidecar.services.session_limits import (
    SessionLimitExceeded,
    check_can_spend,
    get_usage,
    record_spent,
    reset_session,
)


def _schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"


async def _init_repo(db_path: Path) -> ChatRepository:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    settings_repo = SettingsRepository(db_path)
    await settings_repo.init(_schema_path())
    return ChatRepository(db_path)


@pytest.mark.asyncio
async def test_session_usage_and_reset(tmp_path):
    repo = await _init_repo(tmp_path / "test.db")
    limited_settings = AppSettings(session_limit_enabled=True, session_limit_credits=100)

    usage = await get_usage(repo, limited_settings)
    assert usage.spent == 0
    assert usage.limit == 100
    assert usage.remaining == 100

    await record_spent(repo, 25)
    usage = await get_usage(repo, limited_settings)
    assert usage.spent == 25
    assert usage.remaining == 75

    await reset_session(repo)
    usage = await get_usage(repo, limited_settings)
    assert usage.spent == 0


@pytest.mark.asyncio
async def test_check_can_spend_blocks_over_limit(tmp_path):
    repo = await _init_repo(tmp_path / "test.db")
    limited_settings = AppSettings(session_limit_enabled=True, session_limit_credits=100)

    await record_spent(repo, 95)
    await check_can_spend(repo, limited_settings, estimated=5)
    with pytest.raises(SessionLimitExceeded):
        await check_can_spend(repo, limited_settings, estimated=6)


def test_reset_session_endpoint(client: TestClient):
    response = client.post("/api/v1/account/reset-session")
    assert response.status_code == 204

    usage = client.get("/api/v1/account/session-usage")
    assert usage.status_code == 200
    assert usage.json()["spent"] == 0


def test_generation_blocked_by_session_limit(client: TestClient, monkeypatch):
    monkeypatch.setenv("KIE_API_KEY", "test-key")
    client.post("/internal/reload-api-key", json={"api_key": "test-key"})

    client.patch(
        "/api/v1/settings",
        json={"session_limit_enabled": True, "session_limit_credits": 10},
    )

    import asyncio

    from kie_sidecar.config import get_settings

    async def seed():
        repo = ChatRepository(get_settings().db_path)
        await record_spent(repo, 8)

    asyncio.run(seed())

    response = client.post(
        "/api/v1/generations",
        json={
            "model_id": "flux-2/flex-text-to-image",
            "input": {"prompt": "test"},
        },
    )
    assert response.status_code == 402
