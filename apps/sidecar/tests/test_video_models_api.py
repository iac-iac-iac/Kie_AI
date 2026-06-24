def test_video_models_api(client):
    response = client.get("/api/v1/models?type=video")
    assert response.status_code == 200
    models = response.json()
    assert len(models) == 97
    ids = {m["id"] for m in models}
    assert "kling-2.6/text-to-video" in ids
    assert "bytedance/seedance-1.5-pro" in ids
    assert "kling-2.6/image-to-video" in ids
    assert "bytedance/seedance-2-fast" in ids


def test_kling_schema_api(client):
    response = client.get("/api/v1/models/kling-2.6/text-to-video/schema")
    assert response.status_code == 200
    schema = response.json()
    assert schema["id"] == "kling-2.6/text-to-video"
    assert any(p["name"] == "prompt" for p in schema["parameters"])
    assert any(p["name"] == "duration" for p in schema["parameters"])


def test_seedance_schema_has_duration(client):
    response = client.get("/api/v1/models/bytedance/seedance-1.5-pro/schema")
    assert response.status_code == 200
    schema = response.json()
    assert any(p["name"] == "duration" for p in schema["parameters"])


def test_kling_i2v_schema_has_image_url(client):
    response = client.get("/api/v1/models/kling-2.6/image-to-video/schema")
    assert response.status_code == 200
    schema = response.json()
    param = next(p for p in schema["parameters"] if p["name"] == "image_url")
    assert param["type"] == "image_url"
    assert param["required"] is True
