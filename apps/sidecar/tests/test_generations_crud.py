from pathlib import Path

from kie_sidecar.db.generation_repository import GenerationRepository
from kie_sidecar.db.repository import SettingsRepository


async def test_generation_repository_crud(tmp_path):
    db_path = tmp_path / "test.db"
    repo = GenerationRepository(db_path)
    schema = Path(__file__).resolve().parents[1] / "kie_sidecar" / "db" / "schema.sql"

    settings_repo = SettingsRepository(db_path)
    await settings_repo.init(schema)

    gen = await repo.create_generation(
        type="image",
        model_id="flux-2/flex-text-to-image",
        task_id="task-123",
        prompt="A sunset",
        params={"aspect_ratio": "16:9"},
    )
    assert gen.status == "pending"
    assert gen.task_id == "task-123"

    fetched = await repo.get_generation(gen.id)
    assert fetched is not None
    assert fetched.prompt == "A sunset"
    assert fetched.params == {"aspect_ratio": "16:9"}

    items = await repo.list_generations(type="image")
    assert len(items) == 1

    updated = await repo.update_status(
        gen.id,
        status="success",
        credits_used=12.5,
        remote_url="https://example.com/img.png",
        local_path="/media/images/test.png",
    )
    assert updated is not None
    assert updated.status == "success"
    assert updated.credits_used == 12.5
    assert updated.completed_at is not None

    pending = await repo.list_pending()
    assert pending == []

    deleted = await repo.delete_generation(gen.id)
    assert deleted is not None
    assert await repo.list_generations() == []


def test_generations_api_list_empty(client):
    response = client.get("/api/v1/generations?type=image")
    assert response.status_code == 200
    assert response.json() == []


def test_image_models_api(client):
    response = client.get("/api/v1/models?type=image")
    assert response.status_code == 200
    models = response.json()
    assert len(models) == 59
    ids = {m["id"] for m in models}
    assert "flux-2/flex-text-to-image" in ids
    assert "google/nano-banana" in ids
    assert "gpt-image/1.5-text-to-image" in ids
    assert "google/imagen4-fast" in ids
    assert "flux-2/pro-text-to-image" in ids
    assert "seedream/4.5-text-to-image" in ids


def test_model_schema_api(client):
    response = client.get("/api/v1/models/flux-2/flex-text-to-image/schema")
    assert response.status_code == 200
    schema = response.json()
    assert schema["id"] == "flux-2/flex-text-to-image"
    assert any(p["name"] == "prompt" for p in schema["parameters"])
