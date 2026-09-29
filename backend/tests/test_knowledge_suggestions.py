# backend/tests/test_knowledge_suggestions.py
"""知识沉淀建议审核流：跟进包自动生成草稿 → admin 审核/驳回 → 入知识库。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
admin_token = None
sales_token = None


def test_login():
    global admin_token, sales_token
    admin_token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    sales_token = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]


def _followup_with_objection():
    return client.post(
        "/api/v1/customers/1/followup",
        json={"summary": "客户提出价格异议", "transcript": "客户说太贵了，有预算异议"},
        headers={"authorization": f"Bearer {admin_token}"},
    )


def test_followup_creates_pending_suggestion():
    resp = _followup_with_objection()
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "待管理员审核" in data["knowledge_update_suggestion"]
    assert len(data["knowledge_suggestions"]) >= 1
    draft = data["knowledge_suggestions"][0]
    assert draft["status"] == "pending"
    assert draft["scene"] == "异议应答"


def test_suggestions_require_admin():
    resp = client.get("/api/v1/knowledge/suggestions", headers={"authorization": f"Bearer {sales_token}"})
    assert resp.status_code == 403


def test_approve_flow_creates_script():
    resp = _followup_with_objection()
    draft = resp.json()["data"]["knowledge_suggestions"][0]
    sid = draft["id"]

    approve = client.post(f"/api/v1/knowledge/suggestions/{sid}/approve",
                          json={}, headers={"authorization": f"Bearer {admin_token}"})
    assert approve.status_code == 200
    assert approve.json()["data"]["knowledge_id"] is not None
    assert approve.json()["data"]["suggestion"]["status"] == "approved"

    scripts = client.get("/api/v1/knowledge/scripts", headers={"authorization": f"Bearer {admin_token}"}).json()["data"]
    assert any(s["source"] and "会后沉淀" in s["source"] for s in scripts)

    # 已处理的建议不能重复审核
    again = client.post(f"/api/v1/knowledge/suggestions/{sid}/approve",
                        json={}, headers={"authorization": f"Bearer {admin_token}"})
    assert again.status_code == 409


def test_approve_with_edits_overrides_draft():
    resp = _followup_with_objection()
    sid = resp.json()["data"]["knowledge_suggestions"][0]["id"]
    approve = client.post(f"/api/v1/knowledge/suggestions/{sid}/approve", json={
        "content": "编辑后的话术内容",
        "scene": "破冰",
    }, headers={"authorization": f"Bearer {admin_token}"})
    assert approve.status_code == 200
    scripts = client.get("/api/v1/knowledge/scripts", headers={"authorization": f"Bearer {admin_token}"}).json()["data"]
    matched = [s for s in scripts if s["template"] == "编辑后的话术内容"]
    assert matched and matched[0]["scene"] == "破冰"


def test_reject_flow():
    resp = _followup_with_objection()
    sid = resp.json()["data"]["knowledge_suggestions"][0]["id"]
    reject = client.post(f"/api/v1/knowledge/suggestions/{sid}/reject",
                         json={"note": "质量不足"}, headers={"authorization": f"Bearer {admin_token}"})
    assert reject.status_code == 200
    data = reject.json()["data"]
    assert data["status"] == "rejected"
    assert data["note"] == "质量不足"
    # 驳回后不再出现在待审核列表
    pending = client.get("/api/v1/knowledge/suggestions?status=pending",
                         headers={"authorization": f"Bearer {admin_token}"}).json()["data"]
    assert all(item["id"] != sid for item in pending)


def test_followup_without_objection_no_draft():
    resp = client.post(
        "/api/v1/customers/1/followup",
        json={"summary": "常规拜访", "transcript": "气氛融洽，客户认可方案"},
        headers={"authorization": f"Bearer {admin_token}"},
    )
    data = resp.json()["data"]
    assert data["knowledge_suggestions"] == []
