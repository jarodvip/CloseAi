# backend/tests/test_crm.py
"""v1.0 CRM 集成：配置开关、webhook 推送成功/失败、推送日志、权限。"""
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.crm import CrmPushLog
from app.core.config import settings
from app.core.domain.services import crm_service

client = TestClient(app)
admin_token = None
sales_token = None


def test_login():
    global admin_token, sales_token
    admin_token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    sales_token = client.post("/api/v1/auth/login", json={"username": "sales", "password": "sales123"}).json()["access_token"]


def _headers(token):
    return {"authorization": f"Bearer {token}"}


def test_config_reports_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "CRM_WEBHOOK_URL", "")
    resp = client.get("/api/v1/config", headers=_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["data"]["crm_webhook_enabled"] is False


def test_push_without_config_rejected(monkeypatch):
    monkeypatch.setattr(settings, "CRM_WEBHOOK_URL", "")
    resp = client.post("/api/v1/customers/1/crm-push", json={"summary": "s"}, headers=_headers(admin_token))
    assert resp.status_code == 400
    assert "CRM_WEBHOOK_URL" in resp.json()["detail"]


def test_push_success_and_log(monkeypatch):
    monkeypatch.setattr(settings, "CRM_WEBHOOK_URL", "http://crm.mock/hook")
    captured = {}

    class _FakeResp:
        status_code = 200

        def raise_for_status(self):
            pass

    def fake_post(url, json=None, timeout=None, headers=None):
        captured["url"] = url
        captured["payload"] = json
        return _FakeResp()

    monkeypatch.setattr(crm_service.httpx, "post", fake_post)
    resp = client.post("/api/v1/customers/1/crm-push", json={
        "summary": "测试推送", "tasks": [{"title": "发方案", "deadline": "3个工作日内"}],
    }, headers=_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["data"]["success"] is True
    assert captured["payload"]["customer_id"] == 1
    assert captured["payload"]["pushed_by"] == "admin"
    # 日志落库
    db = SessionLocal()
    try:
        log = db.query(CrmPushLog).order_by(CrmPushLog.id.desc()).first()
        assert log is not None and log.success is True and log.customer_id == 1
        db.delete(log)
        db.commit()
    finally:
        db.close()


def test_push_webhook_error_returns_502_and_logs(monkeypatch):
    monkeypatch.setattr(settings, "CRM_WEBHOOK_URL", "http://crm.mock/hook")

    def fake_post(url, json=None, timeout=None, headers=None):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(crm_service.httpx, "post", fake_post)
    resp = client.post("/api/v1/customers/1/crm-push", json={"summary": "失败用例"},
                       headers=_headers(admin_token))
    assert resp.status_code == 502
    db = SessionLocal()
    try:
        log = db.query(CrmPushLog).order_by(CrmPushLog.id.desc()).first()
        assert log is not None and log.success is False and "connection refused" in (log.error or "")
        db.delete(log)
        db.commit()
    finally:
        db.close()


def test_push_requires_own_customer(monkeypatch):
    monkeypatch.setattr(settings, "CRM_WEBHOOK_URL", "http://crm.mock/hook")
    # sales 推送不属于自己的客户 → 404（owner 隔离语义）
    import random
    other_id = random.randint(900000, 999999)
    resp = client.post(f"/api/v1/customers/{other_id}/crm-push", json={"summary": "s"},
                       headers=_headers(sales_token))
    assert resp.status_code == 404
