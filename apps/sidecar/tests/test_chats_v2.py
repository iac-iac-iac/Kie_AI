from pathlib import Path

import pytest

from kie_sidecar.db.chat_repository import ChatRepository
from kie_sidecar.db.repository import SettingsRepository
from kie_sidecar.models.chat import ContentBlock


@pytest.fixture()
async def chat_repo(tmp_path):
    db_path = tmp_path / "test.db"
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"
    settings_repo = SettingsRepository(db_path)
    await settings_repo.init(schema)
    return ChatRepository(db_path)


@pytest.mark.asyncio
async def test_list_chats_search_by_title(chat_repo):
    await chat_repo.create_chat("claude-sonnet-4-6", title="Проект Kie")
    await chat_repo.create_chat("claude-sonnet-4-6", title="Other topic")

    matches = await chat_repo.list_chats(q="Kie")
    assert len(matches) == 1
    assert matches[0].title == "Проект Kie"


@pytest.mark.asyncio
async def test_list_messages_search(chat_repo):
    chat = await chat_repo.create_chat("claude-sonnet-4-6", title="Search test")
    await chat_repo.add_message(
        chat.id,
        "user",
        [ContentBlock(type="text", text="hello world")],
    )
    await chat_repo.add_message(
        chat.id,
        "assistant",
        [ContentBlock(type="text", text="unique keyword here")],
    )

    matches = await chat_repo.list_messages(chat.id, q="keyword")
    assert len(matches) == 1
    assert matches[0].role == "assistant"


@pytest.mark.asyncio
async def test_export_markdown_utf8(chat_repo):
    chat = await chat_repo.create_chat("claude-sonnet-4-6", title="Чат тест")
    await chat_repo.add_message(
        chat.id,
        "user",
        [ContentBlock(type="text", text="Привет")],
    )
    await chat_repo.add_message(
        chat.id,
        "assistant",
        [ContentBlock(type="text", text="Ответ")],
        credits=1.5,
    )

    md = await chat_repo.export_chat_markdown(chat.id)
    assert md is not None
    # First user message renames chat title
    assert "# Привет" in md
    assert "## User" in md
    assert "Привет" in md
    assert "## Assistant" in md
    assert "Ответ" in md
    assert "*Credits: 1.5*" in md
    assert md.encode("utf-8").decode("utf-8") == md


@pytest.mark.asyncio
async def test_folder_rename_and_delete(chat_repo):
    folder = await chat_repo.create_folder("Old name")
    chat = await chat_repo.create_chat(
        "claude-sonnet-4-6",
        title="In folder",
        folder_id=folder.id,
    )

    updated = await chat_repo.update_folder(folder.id, "New name")
    assert updated is not None
    assert updated.name == "New name"

    deleted = await chat_repo.delete_folder(folder.id)
    assert deleted is True

    refreshed = await chat_repo.get_chat(chat.id)
    assert refreshed is not None
    assert refreshed.folder_id is None

    folders = await chat_repo.list_folders()
    assert all(f.id != folder.id for f in folders)


def test_chats_api_search_and_export(client):
    models = client.get("/api/v1/chats/models").json()
    model_id = models[0]["id"]

    created = client.post(
        "/api/v1/chats",
        json={"model_id": model_id, "title": "API Search Chat"},
    )
    assert created.status_code == 200
    chat_id = created.json()["id"]

    search = client.get("/api/v1/chats", params={"q": "Search"})
    assert search.status_code == 200
    assert any(c["id"] == chat_id for c in search.json())

    export = client.get(f"/api/v1/chats/{chat_id}/export")
    assert export.status_code == 200
    assert "text/markdown" in export.headers["content-type"]
    body = export.content.decode("utf-8")
    assert "# API Search Chat" in body
    assert "content-disposition" in export.headers


def test_folder_api_rename_delete(client):
    folder = client.post("/api/v1/chats/folders", json={"name": "Temp"})
    assert folder.status_code == 200
    folder_id = folder.json()["id"]

    renamed = client.patch(
        f"/api/v1/chats/folders/{folder_id}",
        json={"name": "Renamed"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"

    deleted = client.delete(f"/api/v1/chats/folders/{folder_id}")
    assert deleted.status_code == 204
