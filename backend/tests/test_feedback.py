# backend/tests/test_feedback.py
"""来源卡反馈 API：创建校验 + 采纳率统计。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
token = None


def test_login():
    global token
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def _post_feedback(**overrides):
    payload = {"scene": "assist", "rating": "up", "source": "测试来源_反馈用例"}
    payload.update(overrides)
    return client.post("/api/v1/feedback", json=payload, headers={"authorization": f"Bearer {token}"})


def test_create_feedback_ok():
    resp = _post_feedback(label="话术卡", customer_id=1)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["rating"] == "up"


def test_create_feedback_requires_login():
    resp = client.post("/api/v1/feedback", json={"scene": "assist", "rating": "up", "source": "x"})
    assert resp.status_code == 401


def test_create_feedback_invalid_rating():
    assert _post_feedback(rating="meh").status_code == 422


def test_create_feedback_invalid_scene():
    assert _post_feedback(scene="unknown").status_code == 422


def test_create_feedback_empty_source():
    assert _post_feedback(source="  ").status_code == 422


def test_feedback_stats_contains_created():
    _post_feedback(rating="up")
    _post_feedback(rating="down")
    resp = client.get("/api/v1/feedback/stats", headers={"authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] >= 2
    assert data["up"] >= 1 and data["down"] >= 1
    assert isinstance(data["adoption_rate"], float)
    scene_names = {item["scene"] for item in data["by_scene"]}
    assert "assist" in scene_names
    assert any(item["scene"] == "assist" and item["total"] >= 2 for item in data["by_scene"])


def test_feedback_visible_in_dashboard():
    _post_feedback(rating="up", scene="briefing")
    resp = client.get("/api/v1/dashboard/stats", headers={"authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["feedback"]["total"] >= 1
    assert "llm" in data
