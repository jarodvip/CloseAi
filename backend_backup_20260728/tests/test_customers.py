from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
admin_token = None


def test_login():
    global admin_token
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    admin_token = response.json()["access_token"]


def test_create_customer():
    response = client.post("/api/v1/customers/", json={"name": "测试客户", "industry": "食品"}, headers={"authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "测试客户"
    assert data["id"] >= 1


def test_get_customer():
    response = client.get("/api/v1/customers/1", headers={"authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "示例客户A"
