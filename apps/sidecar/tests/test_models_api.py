def test_image_models_include_estimate_credits(client):
    response = client.get("/api/v1/models?type=image")
    assert response.status_code == 200
    models = response.json()
    assert len(models) > 0
    flux = next(m for m in models if m["id"] == "flux-2/pro-text-to-image")
    assert flux["estimate_credits"] == 15


def test_model_schema_includes_estimate_credits(client):
    response = client.get("/api/v1/models/flux-2/pro-text-to-image/schema")
    assert response.status_code == 200
    data = response.json()
    assert data["estimate_credits"] == 15
    assert "parameters" in data
