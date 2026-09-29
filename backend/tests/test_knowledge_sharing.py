# backend/tests/test_knowledge_sharing.py
"""v1.0 团队知识共享：个人/共享可见性、共享进入检索池、权限校验。"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.core.domain.services.knowledge_service import list_scripts

client = TestClient(app)
admin_token = None
sales_token = None
sales2_token = None


def test_login():
    global admin_token, sales_token, sales2_token
    admin_token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    sales_token = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]
    # 借 admin API 创建第二个普通用户，验证跨用户可见性
    client.post("/api/v1/auth/users", json={"username": "sales2", "password": "sales2pass"},
                headers={"authorization": f"Bearer {admin_token}"})
    sales2_token = client.post("/api/v1/auth/login", json={"username": "sales2", "password": "sales2pass"}).json()["access_token"]


def _headers(token):
    return {"authorization": f"Bearer {token}"}


def _marker():
    return f"shr_{uuid.uuid4().hex[:8]}"


def test_admin_creates_shared_sales_creates_personal():
    marker = _marker()
    admin_case = client.post("/api/v1/knowledge/cases", json={
        "code": f"CASE_{marker}_a", "title": f"管理案例{marker}",
    }, headers=_headers(admin_token)).json()["data"]
    assert admin_case["is_shared"] is True

    sales_case = client.post("/api/v1/knowledge/cases", json={
        "code": f"CASE_{marker}_b", "title": f"个人案例{marker}",
    }, headers=_headers(sales_token)).json()["data"]
    assert sales_case["is_shared"] is False
    assert sales_case["owner_username"] == "sales"


def test_personal_case_hidden_from_other_user():
    marker = _marker()
    personal_code = f"CASE_{marker}_p"
    client.post("/api/v1/knowledge/cases", json={"code": personal_code, "title": f"个人{marker}"},
                headers=_headers(sales_token))
    # 创建者可见
    mine = client.get("/api/v1/knowledge/cases", headers=_headers(sales_token)).json()["data"]
    assert any(c["code"] == personal_code for c in mine)
    # 管理员可见（聚合视图）
    admin_view = client.get("/api/v1/knowledge/cases", headers=_headers(admin_token)).json()["data"]
    assert any(c["code"] == personal_code for c in admin_view)
    # 其他普通用户不可见
    other_view = client.get("/api/v1/knowledge/cases", headers=_headers(sales2_token)).json()["data"]
    assert not any(c["code"] == personal_code for c in other_view)

    # 共享后其他用户可见
    case_id = next(c["id"] for c in mine if c["code"] == personal_code)
    resp = client.patch(f"/api/v1/knowledge/cases/{case_id}/share?is_shared=true", headers=_headers(sales_token))
    assert resp.status_code == 200
    other_view = client.get("/api/v1/knowledge/cases", headers=_headers(sales2_token)).json()["data"]
    assert any(c["code"] == personal_code for c in other_view)


def test_share_permission_only_owner_or_admin():
    marker = _marker()
    personal = client.post("/api/v1/knowledge/cases", json={"code": f"CASE_{marker}_x", "title": f"案例{marker}"},
                           headers=_headers(sales_token)).json()["data"]
    other_share = client.patch(f"/api/v1/knowledge/cases/{personal['id']}/share?is_shared=true",
                               headers=_headers(sales2_token))
    assert other_share.status_code == 403
    admin_share = client.patch(f"/api/v1/knowledge/cases/{personal['id']}/share?is_shared=true",
                               headers=_headers(admin_token))
    assert admin_share.status_code == 200


def test_personal_script_excluded_from_retrieval_pool():
    marker = _marker()
    personal = client.post("/api/v1/knowledge/scripts", json={
        "scene": "破冰", "type": "品牌野心型", "template": f"个人话术{marker}", "source": "test",
    }, headers=_headers(sales_token)).json()["data"]
    db = SessionLocal()
    try:
        pool = list_scripts(db, shared_only=True)
        assert all(s.id != personal["id"] for s in pool)
        # 共享后进入检索池
        client.patch(f"/api/v1/knowledge/scripts/{personal['id']}/share?is_shared=true",
                     headers=_headers(sales_token))
        pool = list_scripts(db, shared_only=True)
        assert any(s.id == personal["id"] for s in pool)
    finally:
        db.close()
