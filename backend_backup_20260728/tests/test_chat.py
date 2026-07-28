from fastapi.testclient import TestClient
from app.main import app
from app.db.session import Base, engine
from app.services.auth_service import create_user
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User

client = TestClient(app)
token = None


def test_login():
    global token
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    for username in ["admin", "sales"]:
        if not db.query(User).filter(User.username == username).first():
            create_user(db, username, f"{username}123", role="admin" if username == "admin" else "user")
    db.commit()
    db.close()
    token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"}).json()["access_token"]


def test_chat_multi_page_session():
    session = client.post("/api/v1/chat/sessions", json={"customer_id": None, "title": "客户A攻单"}, headers={"authorization": f"Bearer {token}"}).json()
    assert session["title"] == "客户A攻单"
    history = client.get("/api/v1/chat/sessions", headers={"authorization": f"Bearer {token}"}).json()
    assert any(item["id"] == session["id"] for item in history)

    message = client.post(f"/api/v1/chat/sessions/{session['id']}/messages", json={"role": "user", "content": "准备会前简报"}, headers={"authorization": f"Bearer {token}"}).json()
    assert message["session_id"] == session["id"]
    assert message["message"]["role"] == "assistant"
    assert isinstance(message["source_cards"], list)
    assert isinstance(message["source_refs"], list)

    renamed = client.patch(f"/api/v1/chat/sessions/{session['id']}", json={"title": "客户A会前问题"}, headers={"authorization": f"Bearer {token}"}).json()
    assert renamed["title"] == "客户A会前问题"

    messages = client.get(f"/api/v1/chat/sessions/{session['id']}/messages", headers={"authorization": f"Bearer {token}"}).json()
    assert len(messages) >= 2
