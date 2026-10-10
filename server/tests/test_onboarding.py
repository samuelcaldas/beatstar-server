import pytest
from fastapi.testclient import TestClient
from server.app_factory import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_starter_songs_catalog(client):
    response = client.get("/api/v1/songs/starters")
    assert response.status_code == 200
    data = response.json()
    assert len(data.get("songs", [])) == 4
    assert data["songs"][0]["id"] == 710

def test_accept_terms(client):
    response = client.post("/api/v1/onboarding/terms", json={"accepted": True, "version": "1.0"})
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] is True

def test_save_preferences(client):
    response = client.post("/api/v1/onboarding/preferences", json={"audio_offset": 0, "sound_fx": True})
    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
