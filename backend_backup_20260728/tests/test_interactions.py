from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
token = None


def test_login():
    global token
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_create_and_list_interaction():
    response = client.post("/api/v1/customers/1/interactions", json={"stage": "会中", "summary": "客户愿意测试", "pending_actions": "发送方案"}, headers={"authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == 1
    list_resp = client.get("/api/v1/customers/1/interactions", headers={"authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
