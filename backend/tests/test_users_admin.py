# backend/tests/test_users_admin.py
"""v1.0 用户管理：创建/禁用/重置/限速/密码策略/禁用即失效。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
admin_token = None
sales_token = None


def test_login():
    global admin_token, sales_token
    admin_token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    sales_token = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]


def _admin_headers():
    return {"authorization": f"Bearer {admin_token}"}


def test_users_list_requires_admin():
    resp = client.get("/api/v1/auth/users", headers={"authorization": f"Bearer {sales_token}"})
    assert resp.status_code == 403
    resp = client.get("/api/v1/auth/users", headers=_admin_headers())
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()["data"]}
    assert {"admin", "sales"} <= usernames


def test_create_user_password_policy():
    resp = client.post("/api/v1/auth/users", json={"username": "weakpw", "password": "123"},
                       headers=_admin_headers())
    assert resp.status_code == 422


def test_create_user_and_duplicate():
    resp = client.post("/api/v1/auth/users", json={"username": "user_mgmt_a", "password": "password888"},
                       headers=_admin_headers())
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is True
    dup = client.post("/api/v1/auth/users", json={"username": "user_mgmt_a", "password": "password888"},
                      headers=_admin_headers())
    assert dup.status_code == 409


def test_created_user_can_login():
    resp = client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "password888"})
    assert resp.status_code == 200


def test_disable_user_blocks_login_and_invalidates_token():
    users = client.get("/api/v1/auth/users", headers=_admin_headers()).json()["data"]
    uid = next(u["id"] for u in users if u["username"] == "user_mgmt_a")
    # 拿一个有效 token
    token = client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "password888"}).json()["access_token"]
    headers = {"authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    # 禁用 → 立即生效
    resp = client.patch(f"/api/v1/auth/users/{uid}/status", json={"is_active": False}, headers=_admin_headers())
    assert resp.status_code == 200
    assert client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "password888"}).status_code == 403
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    # 启用 → 恢复
    client.patch(f"/api/v1/auth/users/{uid}/status", json={"is_active": True}, headers=_admin_headers())
    assert client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "password888"}).status_code == 200


def test_admin_cannot_disable_self():
    users = client.get("/api/v1/auth/users", headers=_admin_headers()).json()["data"]
    admin_id = next(u["id"] for u in users if u["username"] == "admin")
    resp = client.patch(f"/api/v1/auth/users/{admin_id}/status", json={"is_active": False}, headers=_admin_headers())
    assert resp.status_code == 422


def test_reset_password():
    users = client.get("/api/v1/auth/users", headers=_admin_headers()).json()["data"]
    uid = next(u["id"] for u in users if u["username"] == "user_mgmt_a")
    resp = client.post(f"/api/v1/auth/users/{uid}/reset-password", json={"new_password": "newpass666"},
                       headers=_admin_headers())
    assert resp.status_code == 200
    assert client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "password888"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "newpass666"}).status_code == 200


def test_change_own_password():
    # user_mgmt_a 自己改密码
    token = client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "newpass666"}).json()["access_token"]
    headers = {"authorization": f"Bearer {token}"}
    wrong = client.post("/api/v1/auth/change-password",
                        json={"old_password": "bad-old", "new_password": "another777"}, headers=headers)
    assert wrong.status_code == 400
    ok = client.post("/api/v1/auth/change-password",
                     json={"old_password": "newpass666", "new_password": "another777"}, headers=headers)
    assert ok.status_code == 200
    assert client.post("/api/v1/auth/login", json={"username": "user_mgmt_a", "password": "another777"}).status_code == 200


def test_login_rate_limit():
    import uuid
    username = f"rl_{uuid.uuid4().hex[:8]}"
    for _ in range(5):
        resp = client.post("/api/v1/auth/login", json={"username": username, "password": "wrongwrong"})
        assert resp.status_code == 401
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": "wrongwrong"})
    assert resp.status_code == 429
    assert "重试" in resp.json()["detail"]
