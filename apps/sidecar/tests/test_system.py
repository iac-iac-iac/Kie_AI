from pathlib import Path


def test_health_includes_version(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


def test_system_paths(client, temp_data_dir):
    response = client.get("/api/v1/system/paths")
    assert response.status_code == 200
    data = response.json()
    assert "data_dir" in data
    assert "db_path" in data
    assert "media_dir" in data
    assert str(temp_data_dir) in data["data_dir"]


def test_checkpoint_db_creates_snapshot(client, temp_data_dir):
    response = client.post("/internal/checkpoint-db")
    assert response.status_code == 200
    snapshot = response.json()["snapshot_path"]
    assert Path(snapshot).is_file()
