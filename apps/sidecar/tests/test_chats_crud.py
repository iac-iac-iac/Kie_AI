from pathlib import Path

from kie_sidecar.db.chat_repository import ChatRepository
from kie_sidecar.db.repository import SettingsRepository
from kie_sidecar.models.chat import ContentBlock


async def test_chat_repository_crud(tmp_path):
    db_path = tmp_path / "test.db"
    repo = ChatRepository(db_path)
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"

    settings_repo = SettingsRepository(db_path)
    await settings_repo.init(schema)

    chat = await repo.create_chat("claude-sonnet-4-6", title="Test")
    assert chat.model_id == "claude-sonnet-4-6"

    chats = await repo.list_chats()
    assert len(chats) == 1

    msg = await repo.add_message(
        chat.id,
        "user",
        [ContentBlock(type="text", text="Hello world")],
    )
    assert msg.role == "user"

    updated = await repo.get_chat(chat.id)
    assert updated is not None
    assert updated.title == "Hello world"

    messages = await repo.list_messages(chat.id)
    assert len(messages) == 1

    assistant = await repo.add_message(
        chat.id,
        "assistant",
        [ContentBlock(type="text", text="Hi!")],
        tokens_in=10,
        tokens_out=5,
        credits=0.5,
    )
    assert assistant.credits == 0.5

    await repo.add_session_credits(0.5)
    spent = await repo.get_session_spent()
    assert spent == 0.5

    deleted = await repo.delete_chat(chat.id)
    assert deleted is True
    assert await repo.list_chats() == []


def test_chats_api_flow(client):
    models = client.get("/api/v1/chats/models")
    assert models.status_code == 200
    model_list = models.json()
    assert len(model_list) >= 31
    model_id = model_list[0]["id"]

    create = client.post("/api/v1/chats", json={"model_id": model_id})
    assert create.status_code == 200
    chat_id = create.json()["id"]

    list_resp = client.get("/api/v1/chats")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    messages = client.get(f"/api/v1/chats/{chat_id}/messages")
    assert messages.status_code == 200
    assert messages.json() == []

    send = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        json={"content": [{"type": "text", "text": "Hi"}]},
    )
    assert send.status_code == 401

    delete = client.delete(f"/api/v1/chats/{chat_id}")
    assert delete.status_code == 204


def test_folders_api(client):
    create = client.post("/api/v1/chats/folders", json={"name": "Work"})
    assert create.status_code == 200
    folder_id = create.json()["id"]

    folders = client.get("/api/v1/chats/folders")
    assert folders.status_code == 200
    assert len(folders.json()) == 1

    models = client.get("/api/v1/chats/models").json()
    chat = client.post(
        "/api/v1/chats",
        json={"model_id": models[0]["id"], "folder_id": folder_id},
    )
    assert chat.status_code == 200
    assert chat.json()["folder_id"] == folder_id

    patch = client.patch(
        f"/api/v1/chats/{chat.json()['id']}",
        json={"folder_id": None},
    )
    assert patch.status_code == 200
    assert patch.json()["folder_id"] is None
