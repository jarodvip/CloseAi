from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
token = None


def test_login():
    global token
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_followup():
    response = client.post("/api/v1/customers/1/followup", json={"summary": "客户愿意做测试", "decisions": ["同意1城测试"], "pending_actions": ["发送测试方案"]}, headers={"authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert len(data["data"]["tasks"]) >= 1
