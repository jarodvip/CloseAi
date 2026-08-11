from fastapi.testclient import TestClient
from app.main import app
from app.db.init_db import init_db

client = TestClient(app)
token = None


def test_login():
    global token
    init_db()
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_knowledge_cases():
    response = client.get("/api/v1/knowledge/cases", headers={"authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]) >= 1
