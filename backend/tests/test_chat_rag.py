"""会中聊天 RAG 注入：提问回复先把命中的研究块前置进提示词，再生成回答；响应携带来源卡"""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.db.init_db import init_db
from app.core.domain.services.research_service import ingest_text, delete_chunk

client = TestClient(app)

RAG_MARK = "会中rag标记_kp55"
Q = "气泡水的旺季打法"
USERNAME = f"u_{RAG_MARK}"
PASSWORD = "pw123456"


def test_chat_reply_carries_sources(monkeypatch):
    init_db()
    db = SessionLocal()
    made = []
    cust = None
    sid = None
    try:
        # 一次性账号 + 归属客户，全部带唯一标记，便于 finally 清理
        from app.core.domain.services.auth_service import create_user
        from app.core.domain.services.customer_service import create_customer
        from app.schemas.customer import CustomerIn

        user = create_user(db, USERNAME, PASSWORD, role="user")
        cust = create_customer(db, CustomerIn(name=f"会中客户_{RAG_MARK}", industry="饮料"), owner_id=user.id)
        # 正文同时包含提问关键词（气泡水）与行业词（饮料），保证名称/行业任一路检索都能命中
        made = ingest_text(db, f"{RAG_MARK} 夏季高温期气泡水等饮料品类动销最佳，建议提前铺冰柜。",
                           source_type="doc", title=f"{RAG_MARK}_资料",
                           customer_id=cust.id, industry="饮料")

        captured = {}

        def fake_generate(prompt, system=None, **kw):
            captured["prompt"] = prompt
            return "建议提前一个月锁定冰柜资源。"

        # chat_service 以 from-import 方式引入 generate_text，patch 其模块属性
        monkeypatch.setattr("app.core.domain.services.chat_service.generate_text", fake_generate)

        tok = client.post("/api/v1/auth/login",
                          json={"username": USERNAME, "password": PASSWORD}).json()["access_token"]
        headers = {"authorization": f"Bearer {tok}"}
        s = client.post("/api/v1/chat/sessions", json={"customer_id": cust.id}, headers=headers).json()
        sid = s["id"]
        r = client.post(f"/api/v1/chat/sessions/{sid}/messages", json={"content": Q}, headers=headers)
        assert r.status_code == 200
        body = r.json()
        msg = body.get("data") or body
        assert RAG_MARK in captured["prompt"], "命中资料块应前置注入 LLM 提示词"
        cards = msg.get("source_cards") or []
        assert len(cards) >= 1 and cards[0].get("source")
        assert any(RAG_MARK in (c.get("detail") or "") for c in cards), "来源卡应包含本研究块的片段"

        # 前端第二条消费路径：历史消息读取 message.meta 里的 source_cards
        msgs = client.get(f"/api/v1/chat/sessions/{sid}/messages", headers=headers).json()
        meta_cards = []
        for m in msgs:
            if m.get("role") == "assistant":
                meta_cards += json.loads(m.get("meta") or "{}").get("source_cards") or []
        assert any(RAG_MARK in str(c) for c in meta_cards), "持久化的消息 meta 也应携带 RAG 来源卡"
    finally:
        # 无论成败删尽全部创建行：研究块(含 FTS)、消息、会话、客户、用户
        for c in made:
            delete_chunk(db, c.id)
        if sid is not None:
            from app.models.chat import ChatMessage, ChatSession

            db.query(ChatMessage).filter(ChatMessage.session_id == sid).delete(synchronize_session=False)
            db.query(ChatSession).filter(ChatSession.id == sid).delete(synchronize_session=False)
        if cust is not None:
            db.delete(cust)
        from app.models.user import User

        db.query(User).filter(User.username == USERNAME).delete(synchronize_session=False)
        db.commit()
        db.close()
