"""LLM 增强生成集成测试：模拟 LLM 可用，验证各服务正确注入 llm_text。"""
from unittest.mock import patch

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine
from app.core.domain.services.auth_service import create_user
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.customer import Customer
from app.db.init_db import init_db

client = TestClient(app)
token = None
customer_id = 1
session_id = 1


def setup():
    global token, customer_id, session_id
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            create_user(db, "admin", "admin123", role="admin")
        admin = db.query(User).filter(User.username == "admin").first()
        if not db.query(Customer).filter(Customer.id == 1).first():
            c = Customer(name="LLM测试客户", industry="消费", stage="成长期", region="华东", owner_id=admin.id)
            db.add(c)
            db.flush()
            customer_id = c.id
        db.commit()
    finally:
        db.close()
    init_db()
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]
    s = client.post("/api/v1/chat/sessions", json={"customer_id": customer_id}, headers={"authorization": f"Bearer {token}"}).json()
    session_id = s["id"]


setup()


def test_briefing_llm_text_injected():
    """简报生成时，LLM 可用的情况下 llm_text 应被填充"""
    fake_llm = "【LLM增强】该客户处于成长期，建议重点投入品牌资产建设。"
    with patch("app.core.domain.services.briefing_service.generate_text", return_value=fake_llm):
        resp = client.post(
            f"/api/v1/customers/{customer_id}/briefing",
            headers={"authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["llm_text"] == fake_llm


def test_assist_llm_text_injected():
    """会中辅助时，LLM 可用的情况下 llm_text 应被填充"""
    fake_llm = "【LLM增强】当前阶段为「听」，建议继续挖掘客户增长瓶颈。"
    with patch("app.core.domain.services.assist_service.generate_text", return_value=fake_llm):
        resp = client.post(
            f"/api/v1/customers/{customer_id}/assist",
            json={"current_stage": "听", "transcript": "你们有什么预期数据？"},
            headers={"authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["llm_text"] == fake_llm


def test_followup_llm_text_injected():
    """会后跟进时，LLM 可用的情况下 llm_text 应被填充"""
    fake_llm = "【LLM增强】建议3个工作日内发送测试方案，5个工作日内确认关键决策人。"
    with patch("app.core.domain.services.followup_service.generate_text", return_value=fake_llm):
        resp = client.post(
            f"/api/v1/customers/{customer_id}/followup",
            json={"summary": "客户有意向，需进一步推进", "decisions": ["确定合作"], "pending_actions": ["发方案"]},
            headers={"authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["llm_text"] == fake_llm


def test_chat_llm_reply_injected():
    """聊天回复时，LLM 可用的情况下消息内容应为 LLM 生成"""
    fake_llm = "【LLM增强回复】建议先明确增长瓶颈，再给一句场景化切入话术。"
    with patch("app.core.domain.services.chat_service.generate_text", return_value=fake_llm):
        resp = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"role": "user", "content": "帮我准备会前简报"},
            headers={"authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == fake_llm


def test_briefing_llm_failure_fallback():
    """LLM 调用失败时，应返回结构化字段（来自知识库），llm_text 为 None"""
    with patch("app.core.domain.services.briefing_service.generate_text", side_effect=RuntimeError("LLM down")):
        resp = client.post(
            f"/api/v1/customers/{customer_id}/briefing",
            headers={"authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["llm_text"] is None
    assert data["customer_name"]  # 确保客户名正确返回（不关心具体值）


def test_assist_llm_failure_keeps_structured_output():
    """LLM 失败时，会中辅助仍返回结构化建议（来自规则引擎）"""
    with patch("app.core.domain.services.assist_service.generate_text", side_effect=RuntimeError("LLM down")):
        resp = client.post(
            f"/api/v1/customers/{customer_id}/assist",
            json={"current_stage": "听", "transcript": "你们有什么预期数据？"},
            headers={"authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["current_stage"] == "听"
    assert data["llm_text"] is None


def test_followup_llm_failure_keeps_structured_output():
    """LLM 失败时，会后跟进仍返回结构化结果"""
    with patch("app.core.domain.services.followup_service.generate_text", side_effect=RuntimeError("LLM down")):
        resp = client.post(
            f"/api/v1/customers/{customer_id}/followup",
            json={"summary": "客户有意向", "decisions": ["确定合作"], "pending_actions": ["发方案"]},
            headers={"authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["llm_text"] is None
    assert len(data["tasks"]) >= 1