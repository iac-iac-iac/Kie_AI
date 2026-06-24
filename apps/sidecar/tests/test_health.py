def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "has_api_key" in data
    assert "version" in data


def test_reload_api_key_updates_file_uploader(client):
    state = client.app.state.app_state
    assert state.file_uploader._api_key is None

    response = client.post("/internal/reload-api-key", json={"api_key": "test-key"})
    assert response.status_code == 200
    assert response.json()["has_api_key"] is True
    assert state.settings.api_key == "test-key"
    assert state.file_uploader._api_key == "test-key"


def test_reload_api_key_clears_key(client):
    client.post("/internal/reload-api-key", json={"api_key": "test-key"})
    response = client.post("/internal/reload-api-key", json={"api_key": ""})
    assert response.status_code == 200
    assert response.json()["has_api_key"] is False
    state = client.app.state.app_state
    assert state.settings.api_key is None
    assert state.file_uploader._api_key is None


def test_settings_roundtrip(client):
    get_resp = client.get("/api/v1/settings")
    assert get_resp.status_code == 200
    assert get_resp.json()["theme"] in ("dark", "light", "system")

    patch_resp = client.patch(
        "/api/v1/settings",
        json={"theme": "light", "locale": "en"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["theme"] == "light"
