def test_generations_video_list_empty(client):
    response = client.get("/api/v1/generations?type=video")
    assert response.status_code == 200
    assert response.json() == []
